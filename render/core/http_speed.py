import sys
import os
import json
import traceback

from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.core.http_ping import run_ping_test
from render.core.http_speed import run_speed_test
from render.core.http_stability import run_stability_test
from render.core.isp_info import get_isp_info


app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

CORS(app)


# ─────────────────────────────────────────────
# Client IP helper
# ─────────────────────────────────────────────

def get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip

    js_ip = request.args.get("client_ip", "").strip()
    if js_ip:
        return js_ip

    return request.remote_addr


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/isp")
def api_isp():
    return jsonify(get_isp_info(client_ip=get_client_ip()))


@app.route("/api/ping")
def api_ping():
    return jsonify(run_ping_test(count=10))


@app.route("/api/speed")
def api_speed():
    """
    Standalone speed test (non-SSE)
    """
    try:
        raw = run_speed_test()

        result = {
            "success": True,
            "download_mbps": raw.get("download_mbps") or raw.get("download") or 0,
            "upload_mbps": raw.get("upload_mbps") or raw.get("upload") or 0,
            "download_quality": raw.get("download_quality", "Unknown"),
            "upload_quality": raw.get("upload_quality", "Unknown"),
            "server": raw.get("server", {
                "name": "Unknown",
                "country": "Unknown",
                "sponsor": "Unknown",
                "latency": 0
            })
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


# ─────────────────────────────────────────────
# MAIN SSE STREAM
# ─────────────────────────────────────────────

@app.route("/api/run")
def api_run():

    client_ip = get_client_ip()

    def generate():

        def send(event, data):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            # ── ISP ─────────────────────────────
            yield send("progress", {"percent": 5, "message": "Fetching ISP..."})

            try:
                isp = get_isp_info(client_ip=client_ip)
                yield send("isp", isp)
            except Exception as e:
                yield send("isp", {"success": False, "error": str(e)})

            yield send("progress", {"percent": 15, "message": "ISP done"})

            # ── PING ────────────────────────────
            yield send("progress", {"percent": 20, "message": "Running ping..."})

            try:
                ping = run_ping_test(count=10)
                yield send("ping", ping)
            except Exception as e:
                yield send("ping", {"success": False, "error": str(e)})

            yield send("progress", {"percent": 35, "message": "Ping done"})

            # ── SPEED (FIXED) ───────────────────
            yield send("progress", {
                "percent": 40,
                "message": "Running speed test..."
            })

            try:
                raw = run_speed_test()

                speed = {
                    "success": True,
                    "download_mbps": float(raw.get("download_mbps") or raw.get("download") or 0),
                    "upload_mbps": float(raw.get("upload_mbps") or raw.get("upload") or 0),

                    "download_quality": raw.get("download_quality", "Unknown"),
                    "upload_quality": raw.get("upload_quality", "Unknown"),

                    "server": raw.get("server", {
                        "name": "Unknown",
                        "country": "Unknown",
                        "sponsor": "Unknown",
                        "latency": 0
                    })
                }

                print("[DEBUG SPEED]", speed)
                yield send("speed", speed)

            except Exception as e:
                print("[ERROR SPEED]", str(e))
                yield send("speed", {
                    "success": False,
                    "error": str(e)
                })

            yield send("progress", {"percent": 70, "message": "Speed done"})

            # ── STABILITY ───────────────────────
            yield send("progress", {"percent": 75, "message": "Running stability..."})

            try:
                for event in run_stability_test(duration=30, interval=1):
                    if event["type"] == "ping":
                        yield send("stability_ping", {
                            "latency": event["latency"],
                            "elapsed": event["elapsed"],
                            "timeout": event["timeout"],
                        })
                    elif event["type"] == "result":
                        yield send("stability", event)

            except Exception as e:
                yield send("stability", {"success": False, "error": str(e)})

            yield send("progress", {"percent": 100, "message": "Done"})
            yield send("done", {"message": "All tests complete"})

        except Exception as e:
            yield send("error", {"message": str(e)})
            print(traceback.format_exc())

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)