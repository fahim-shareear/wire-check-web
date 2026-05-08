import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import traceback
from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS

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


# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/isp")
def api_isp():
    result = get_isp_info()
    return jsonify(result)


@app.route("/api/ping")
def api_ping():
    result = run_ping_test(count=10)
    return jsonify(result)


@app.route("/api/speed")
def api_speed():
    result = run_speed_test()
    return jsonify(result)


@app.route("/api/run")
def api_run():
    """
    Main SSE endpoint — runs all tests and streams
    live progress events to the browser with error handling.
    """
    def generate():
        def send(event, data):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            # ── Stage 1 — ISP ──────────────────────────────────
            yield send("progress", {
                "percent": 5,
                "message": "Fetching network identity..."
            })

            try:
                isp = get_isp_info()
                yield send("isp", isp)
            except Exception as e:
                print(f"[ERROR] ISP fetch failed: {str(e)}")
                print(traceback.format_exc())
                yield send("isp", {
                    "success": False,
                    "error": f"ISP info failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 15,
                "message": "Network identity retrieved."
            })

            # ── Stage 2 — Ping ─────────────────────────────────
            yield send("progress", {
                "percent": 20,
                "message": "Running ping test (10 packets)..."
            })

            try:
                ping = run_ping_test(count=10)
                yield send("ping", ping)
            except Exception as e:
                print(f"[ERROR] Ping test failed: {str(e)}")
                print(traceback.format_exc())
                yield send("ping", {
                    "success": False,
                    "error": f"Ping test failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 35,
                "message": "Ping test complete."
            })

            # ── Stage 3 — Speed ────────────────────────────────
            yield send("progress", {
                "percent": 40,
                "message": "Testing download speed (this may take 30-60 seconds)..."
            })

            try:
                speed = run_speed_test()
                yield send("speed", speed)
            except Exception as e:
                print(f"[ERROR] Speed test failed: {str(e)}")
                print(traceback.format_exc())
                yield send("speed", {
                    "success": False,
                    "error": f"Speed test failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 70,
                "message": "Speed test complete."
            })

            # ── Stage 4 — Stability ────────────────────────────
            yield send("progress", {
                "percent": 75,
                "message": "Running stability test (30 seconds)..."
            })

            stability_result = None
            try:
                for event in run_stability_test(duration=30, interval=1):
                    if event["type"] == "ping":
                        yield send("stability_ping", {
                            "latency": event["latency"],
                            "elapsed": event["elapsed"],
                            "timeout": event["timeout"],
                        })
                    elif event["type"] == "result":
                        stability_result = event
                        yield send("stability", stability_result)

            except Exception as e:
                print(f"[ERROR] Stability test failed: {str(e)}")
                print(traceback.format_exc())
                yield send("stability", {
                    "success": False,
                    "error": f"Stability test failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 100,
                "message": "All tests complete."
            })
            yield send("done", {"message": "All tests complete."})

        except Exception as e:
            print(f"[CRITICAL ERROR] Stream generation failed: {str(e)}")
            print(traceback.format_exc())
            yield send("error", {
                "message": f"Critical error: {str(e)}"
            })

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
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)