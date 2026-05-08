import time
import requests
import statistics


# ── Test file URLs ─────────────────────────────────────────────
# Multiple fallback URLs for reliability
DOWNLOAD_TARGETS = [
    "https://httpbin.org/bytes/10000000",                  # 10MB httpbin (more reliable)
    "https://speed.cloudflare.com/__down?bytes=10000000",  # 10MB Cloudflare
]

UPLOAD_TARGET = "https://httpbin.org/post"


def test_download_speed():
    """
    Measure download speed by downloading a 10MB file
    and timing how long it takes.
    Returns speed in bits per second.
    """
    for url in DOWNLOAD_TARGETS:
        try:
            print(f"[DEBUG] Attempting download from: {url}")
            start      = time.perf_counter()
            response   = requests.get(url, timeout=60, stream=True)  # Increased timeout
            total_bytes = 0

            # Track progress for debugging
            chunk_count = 0
            for chunk in response.iter_content(chunk_size=8192):
                total_bytes += len(chunk)
                chunk_count += 1

            end      = time.perf_counter()
            duration = end - start

            print(f"[DEBUG] Downloaded {total_bytes} bytes in {duration:.2f}s from {url}")

            if duration > 0 and total_bytes > 0:
                speed_bps = (total_bytes * 8) / duration
                return {
                    "success":    True,
                    "speed_bps":  speed_bps,
                    "speed_mbps": round(speed_bps / 1_000_000, 2),
                    "bytes":      total_bytes,
                    "duration":   round(duration, 2),
                }

        except requests.exceptions.Timeout:
            print(f"[DEBUG] Download timeout from {url}")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Download connection error from {url}: {str(e)}")
            continue
        except Exception as e:
            print(f"[DEBUG] Download error from {url}: {str(e)}")
            continue

    return {
        "success": False,
        "error":   "Download test failed. Check your connection."
    }


def test_upload_speed():
    """
    Measure upload speed by uploading random data
    and timing how long it takes.
    Returns speed in bits per second.
    """
    # Generate 5MB of random data
    upload_size = 5 * 1024 * 1024
    data        = b"x" * upload_size

    try:
        print(f"[DEBUG] Starting upload test, {upload_size} bytes to {UPLOAD_TARGET}")
        start    = time.perf_counter()
        response = requests.post(
            UPLOAD_TARGET,
            data=data,
            timeout=60,  # Increased timeout
            headers={"Content-Type": "application/octet-stream"}
        )
        end      = time.perf_counter()
        duration = end - start

        print(f"[DEBUG] Upload completed: status={response.status_code}, duration={duration:.2f}s")

        if duration > 0 and response.status_code == 200:
            speed_bps = (upload_size * 8) / duration
            return {
                "success":    True,
                "speed_bps":  speed_bps,
                "speed_mbps": round(speed_bps / 1_000_000, 2),
                "bytes":      upload_size,
                "duration":   round(duration, 2),
            }
        else:
            return {
                "success": False,
                "error":   f"Upload test failed with status code: {response.status_code}"
            }

    except requests.exceptions.Timeout:
        print("[DEBUG] Upload test timed out")
        return {
            "success": False,
            "error":   "Upload test timed out. Server took too long to respond."
        }
    except requests.exceptions.ConnectionError as e:
        print(f"[DEBUG] Upload connection error: {str(e)}")
        return {
            "success": False,
            "error":   f"Upload connection failed: {str(e)}"
        }
    except Exception as e:
        print(f"[DEBUG] Upload test error: {str(e)}")
        return {
            "success": False,
            "error":   f"Upload test failed: {str(e)}"
        }


def get_quality_label(metric, value):
    """Get quality label for speed metrics"""
    thresholds = {
        "download": [(100, "Excellent"), (25, "Good"), (5, "Average"), (0, "Poor")],
        "upload":   [(50, "Excellent"), (10, "Good"), (2, "Average"), (0, "Poor")],
    }
    for threshold, label in thresholds[metric]:
        if value >= threshold:
            return label
    return "Poor"


def run_speed_test():
    """
    Main function — runs full speed test.
    Returns complete result dict.
    """
    try:
        print("[DEBUG] Starting speed test suite")
        print("Testing download speed...")
        download = test_download_speed()

        print("Testing upload speed...")
        upload = test_upload_speed()

        if not download["success"]:
            print(f"[DEBUG] Download failed: {download.get('error')}")
            return {
                "success": False,
                "error":   download.get("error", "Download test failed.")
            }

        if not upload["success"]:
            print(f"[DEBUG] Upload failed: {upload.get('error')}")
            return {
                "success": False,
                "error":   upload.get("error", "Upload test failed.")
            }

        download_mbps = download["speed_mbps"]
        upload_mbps   = upload["speed_mbps"]

        result = {
            "success":          True,
            "server": {
                "name":     "httpbin.org",
                "country":  "Global",
                "sponsor":  "httpbin",
                "latency":  0,
            },
            "download_bps":     download["speed_bps"],
            "upload_bps":       upload["speed_bps"],
            "download_mbps":    download_mbps,
            "upload_mbps":      upload_mbps,
            "download_quality": get_quality_label("download", download_mbps),
            "upload_quality":   get_quality_label("upload", upload_mbps),
            "download_bytes":   download["bytes"],
            "upload_bytes":     upload["bytes"],
            "download_duration": download["duration"],
            "upload_duration":  upload["duration"],
        }
        print(f"[DEBUG] Speed test complete: {download_mbps} Mbps down, {upload_mbps} Mbps up")
        return result

    except Exception as e:
        print(f"[ERROR] Speed test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error":   f"Speed test failed: {str(e)}"
        }


if __name__ == "__main__":
    result = run_speed_test()
    print(result)