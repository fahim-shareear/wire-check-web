"""Wire-Test: Network Speed & Stability Analyzer"""
import json
import os
import traceback
from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS

# Import test modules - CORRECT render.core imports
from render.core.http_ping import run_ping_test
from render.core.http_speed import run_speed_test
from render.core.http_stability import run_stability_test
from render.core.isp_info import get_isp_info


# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# Enable CORS for all routes
CORS(app)


# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main dashboard"""
    return render_template("index.html")


@app.route("/api/isp")
def api_isp():
    """Get ISP information endpoint"""
    try:
        result = get_isp_info()
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] ISP info failed: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"ISP detection failed: {str(e)}"
        }), 500


@app.route("/api/ping")
def api_ping():
    """Get ping test results endpoint"""
    try:
        result = run_ping_test(count=10)
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] Ping test failed: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Ping test failed: {str(e)}"
        }), 500


@app.route("/api/speed")
def api_speed():
    """Get speed test results endpoint"""
    try:
        result = run_speed_test()
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] Speed test failed: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Speed test failed: {str(e)}"
        }), 500


@app.route("/api/run")
def api_run():
    """
    Main SSE endpoint - runs all tests and streams
    live progress events to the browser using Server-Sent Events.
    """
    print("[TEST] Starting full test suite...")
    
    def generate():
        def send(event, data):
            """Format data as SSE event"""
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
                print(f"[TEST] ISP info: {isp.get('data', {}).get('ip', 'unknown')}")
            except Exception as e:
                print(f"[ERROR] ISP fetch failed: {str(e)}")
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
                "message": "Running ping test (10 packets to Google)..."
            })

            try:
                ping = run_ping_test(count=10)
                yield send("ping", ping)
                if ping.get('success'):
                    print(f"[TEST] Ping: {ping.get('avg_latency')} ms, {ping.get('packet_loss')}% loss")
            except Exception as e:
                print(f"[ERROR] Ping test failed: {str(e)}")
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
                "message": "Testing real ISP speed (measuring sustained throughput for 15 seconds)..."
            })

            try:
                speed = run_speed_test()
                yield send("speed", speed)
                if speed.get('success'):
                    print(f"[TEST] Speed: DL={speed.get('download_mbps')} Mbps, UL={speed.get('upload_mbps')} Mbps")
            except Exception as e:
                print(f"[ERROR] Speed test failed: {str(e)}")
                yield send("speed", {
                    "success": False,
                    "error": f"Speed test failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 70,
                "message": "Speed test complete. Results show your REAL ISP speed."
            })

            # ── Stage 4 — Stability ────────────────────────────
            yield send("progress", {
                "percent": 75,
                "message": "Running stability test (30 seconds)..."
            })

            try:
                stability_result = None
                for event in run_stability_test(duration=30, interval=1):
                    if event["type"] == "ping":
                        yield send("stability_ping", {
                            "latency": event["latency"],
                            "elapsed": event["elapsed"],
                            "timeout": event["timeout"],
                        })
                    elif event["type"] == "result":
                        stability_result = event

                if stability_result and stability_result.get('success'):
                    yield send("stability", stability_result)
                    print(f"[TEST] Stability: Score={stability_result.get('stability_score')}, Loss={stability_result.get('packet_loss')}%")
                elif stability_result:
                    yield send("stability", stability_result)
                    
            except Exception as e:
                print(f"[ERROR] Stability test failed: {str(e)}")
                yield send("stability", {
                    "success": False,
                    "error": f"Stability test failed: {str(e)}"
                })

            yield send("progress", {
                "percent": 100,
                "message": "All tests complete."
            })
            yield send("done", {"message": "All tests complete."})
            print("[TEST] Test suite completed successfully")

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
    return jsonify({"status": "ok", "message": "wire-test is running"})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    print(f"[STARTUP] Starting wire-test on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)