import os
import time
import statistics
import requests


# ──────────────────────────────────────────────────────────────
# ORIGINAL UI-COMPATIBLE ENDPOINTS
# ──────────────────────────────────────────────────────────────

DOWNLOAD_TARGETS = [
    "https://speed.cloudflare.com/__down?bytes=250000000",
    "https://speed.cloudflare.com/__down?bytes=100000000",
    "https://proof.ovh.net/files/100Mb.dat",
]

UPLOAD_TARGET = "https://speed.cloudflare.com/__up"
UPLOAD_FALLBACK = "https://httpbin.org/post"


# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────

# IMPORTANT:
# Single-thread testing prevents inflated speed
DOWNLOAD_THREADS = 1

DOWNLOAD_CHUNK_SIZE = 1024 * 256
UPLOAD_CHUNK_SIZE = 1024 * 256

DOWNLOAD_TIMEOUT = 120
UPLOAD_TIMEOUT = 120

# Sustained measurement duration
TEST_DURATION = 20

# Random upload payload
UPLOAD_SIZE = 25 * 1024 * 1024


# ──────────────────────────────────────────────────────────────
# DOWNLOAD TEST
# ──────────────────────────────────────────────────────────────

def test_download_speed():

    """
    Realistic sustained download test.
    Keeps original endpoints for UI compatibility.
    """

    for url in DOWNLOAD_TARGETS:

        try:

            print(f"[DEBUG] Download test using: {url}")

            response = requests.get(
                url,
                stream=True,
                timeout=DOWNLOAD_TIMEOUT,
                headers={
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
            )

            response.raise_for_status()

            total_bytes = 0
            speed_samples = []

            start_time = time.perf_counter()

            last_sample_time = start_time
            last_sample_bytes = 0

            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_SIZE
            ):

                if not chunk:
                    continue

                total_bytes += len(chunk)

                now = time.perf_counter()

                elapsed_since_sample = (
                    now - last_sample_time
                )

                # Sample every second
                if elapsed_since_sample >= 1:

                    bytes_since_sample = (
                        total_bytes - last_sample_bytes
                    )

                    sample_bps = (
                        bytes_since_sample * 8
                    ) / elapsed_since_sample

                    speed_samples.append(sample_bps)

                    print(
                        f"[DEBUG] Current Download: "
                        f"{sample_bps / 1_000_000:.2f} Mbps"
                    )

                    last_sample_time = now
                    last_sample_bytes = total_bytes

                # Sustained testing
                total_elapsed = now - start_time

                if total_elapsed >= TEST_DURATION:
                    break

            if not speed_samples:
                continue

            # Remove startup burst spikes
            if len(speed_samples) > 4:
                speed_samples = speed_samples[2:]

            avg_bps = statistics.mean(speed_samples)

            avg_mbps = avg_bps / 1_000_000

            duration = round(
                time.perf_counter() - start_time,
                2
            )

            print(
                f"[DEBUG] Sustained Download Speed: "
                f"{avg_mbps:.2f} Mbps"
            )

            return {
                "success": True,
                "speed_bps": avg_bps,
                "speed_mbps": round(avg_mbps, 2),
                "bytes": total_bytes,
                "duration": duration,
                "threads": DOWNLOAD_THREADS,
                "samples": len(speed_samples),
            }

        except requests.exceptions.Timeout:
            print(f"[DEBUG] Download timeout from {url}")

        except Exception as e:
            print(f"[DEBUG] Download error from {url}: {e}")

    return {
        "success": False,
        "error": "Download test failed."
    }


# ──────────────────────────────────────────────────────────────
# UPLOAD TEST
# ──────────────────────────────────────────────────────────────

def test_upload_speed():

    """
    Realistic upload speed test.
    Uses random payload to avoid compression inflation.
    """

    # RANDOM payload prevents fake upload acceleration
    data = os.urandom(UPLOAD_SIZE)

    targets = [UPLOAD_TARGET, UPLOAD_FALLBACK]

    for url in targets:

        try:

            print(f"[DEBUG] Upload test using: {url}")

            start_time = time.perf_counter()

            response = requests.post(
                url,
                data=data,
                timeout=UPLOAD_TIMEOUT,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
            )

            end_time = time.perf_counter()

            response.raise_for_status()

            duration = end_time - start_time

            if duration <= 0:
                continue

            speed_bps = (
                UPLOAD_SIZE * 8
            ) / duration

            speed_mbps = speed_bps / 1_000_000

            print(
                f"[DEBUG] Sustained Upload Speed: "
                f"{speed_mbps:.2f} Mbps"
            )

            return {
                "success": True,
                "speed_bps": speed_bps,
                "speed_mbps": round(speed_mbps, 2),
                "bytes": UPLOAD_SIZE,
                "duration": round(duration, 2),
            }

        except requests.exceptions.Timeout:
            print(f"[DEBUG] Upload timeout to {url}")

        except Exception as e:
            print(f"[DEBUG] Upload error to {url}: {e}")

    return {
        "success": False,
        "error": "Upload test failed."
    }


# ──────────────────────────────────────────────────────────────
# LATENCY TEST
# ──────────────────────────────────────────────────────────────

def test_latency():

    host = "https://1.1.1.1"

    latencies = []

    for i in range(5):

        try:

            start = time.perf_counter()

            response = requests.get(
                host,
                timeout=10
            )

            end = time.perf_counter()

            response.raise_for_status()

            latency_ms = (
                end - start
            ) * 1000

            latencies.append(latency_ms)

            print(
                f"[DEBUG] Ping {i+1}: "
                f"{latency_ms:.2f} ms"
            )

        except Exception as e:
            print(f"[DEBUG] Ping failed: {e}")

    if not latencies:

        return {
            "success": False,
            "error": "Latency test failed."
        }

    return {
        "success": True,
        "avg_latency": round(
            statistics.mean(latencies),
            2
        ),
        "min_latency": round(
            min(latencies),
            2
        ),
        "max_latency": round(
            max(latencies),
            2
        ),
        "jitter": round(
            statistics.stdev(latencies),
            2
        ) if len(latencies) > 1 else 0,
    }


# ──────────────────────────────────────────────────────────────
# QUALITY LABELS
# ──────────────────────────────────────────────────────────────

def get_quality_label(metric, value):

    thresholds = {

        "download": [
            (100, "Excellent"),
            (50, "Good"),
            (10, "Average"),
            (0, "Poor"),
        ],

        "upload": [
            (50, "Excellent"),
            (20, "Good"),
            (5, "Average"),
            (0, "Poor"),
        ],
    }

    for threshold, label in thresholds[metric]:

        if value >= threshold:
            return label

    return "Poor"


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def run_speed_test():

    try:

        print("\n[DEBUG] Starting realistic speed test...\n")

        # DOWNLOAD
        print("[DEBUG] Testing sustained download...")
        download = test_download_speed()

        if not download["success"]:
            return download

        # UPLOAD
        print("\n[DEBUG] Testing sustained upload...")
        upload = test_upload_speed()

        if not upload["success"]:
            return upload

        # LATENCY
        print("\n[DEBUG] Testing latency...")
        latency = test_latency()

        if not latency["success"]:

            latency = {
                "avg_latency": 0,
                "min_latency": 0,
                "max_latency": 0,
                "jitter": 0,
            }

        # FINAL UI-COMPATIBLE RESULT
        result = {

            "success": True,

            # UI REQUIRED STRUCTURE
            "server": {
                "name": "Cloudflare Speed Test",
                "country": "Global CDN",
                "sponsor": "Cloudflare",
                "latency": latency["avg_latency"],
            },

            # UI REQUIRED FIELDS
            "download_bps": download["speed_bps"],
            "upload_bps": upload["speed_bps"],

            "download_mbps": download["speed_mbps"],
            "upload_mbps": upload["speed_mbps"],

            "download_quality": get_quality_label(
                "download",
                download["speed_mbps"]
            ),

            "upload_quality": get_quality_label(
                "upload",
                upload["speed_mbps"]
            ),

            "download_bytes": download["bytes"],
            "upload_bytes": upload["bytes"],

            "download_duration": download["duration"],
            "upload_duration": upload["duration"],

            "download_threads": DOWNLOAD_THREADS,

            # EXTRA PING DATA
            "ping": {
                "avg": latency["avg_latency"],
                "min": latency["min_latency"],
                "max": latency["max_latency"],
                "jitter": latency["jitter"],
                "quality": (
                    "Excellent"
                    if latency["avg_latency"] <= 20
                    else "Good"
                    if latency["avg_latency"] <= 50
                    else "Average"
                    if latency["avg_latency"] <= 100
                    else "Poor"
                )
            }
        }

        print(
            f"\n[DEBUG] Final Speed Results:"
        )

        print(
            f"[DEBUG] Download: "
            f"{result['download_mbps']} Mbps"
        )

        print(
            f"[DEBUG] Upload: "
            f"{result['upload_mbps']} Mbps"
        )

        print(
            f"[DEBUG] Latency: "
            f"{latency['avg_latency']} ms"
        )

        return result

    except Exception as e:

        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "error": str(e)
        }


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    result = run_speed_test()

    print("\n====================================")
    print("     REALISTIC SPEED TEST")
    print("====================================")

    if result["success"]:

        print(
            f"Download Speed : "
            f"{result['download_mbps']} Mbps"
        )

        print(
            f"Upload Speed   : "
            f"{result['upload_mbps']} Mbps"
        )

        print(
            f"Latency        : "
            f"{result['ping']['avg']} ms"
        )

        print(
            f"Jitter         : "
            f"{result['ping']['jitter']} ms"
        )

    else:

        print(f"ERROR: {result['error']}")