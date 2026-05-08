import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── Test endpoints ─────────────────────────────────────────────
# Cloudflare speed test CDN — no throttling, globally distributed
DOWNLOAD_TARGETS = [
    "https://speed.cloudflare.com/__down?bytes=25000000",   # 25MB Cloudflare (primary)
    "https://speed.cloudflare.com/__down?bytes=10000000",   # 10MB Cloudflare (fallback)
    "https://proof.ovh.net/files/10Mb.dat",                 # 10MB OVH (fallback)
]

UPLOAD_TARGET    = "https://speed.cloudflare.com/__up"      # Cloudflare upload endpoint
UPLOAD_FALLBACK  = "https://httpbin.org/post"


# ── Download ───────────────────────────────────────────────────

def _download_once(url, timeout=30):
    """
    Download a file and return (bytes_downloaded, duration_seconds).
    Raises on failure.
    """
    start    = time.perf_counter()
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    total_bytes = 0
    for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
        total_bytes += len(chunk)

    end = time.perf_counter()
    return total_bytes, end - start


def test_download_speed():
    """
    Measure download speed using multiple parallel connections.
    Single-threaded HTTP severely underestimates real bandwidth —
    parallelism compensates for latency overhead from Dhaka to remote servers.
    """
    for url in DOWNLOAD_TARGETS:
        try:
            print(f"[DEBUG] Attempting download from: {url}")

            # Warm-up request (establishes TCP, ignored in measurement)
            try:
                requests.get(url, timeout=10, stream=True).close()
            except Exception:
                pass

            # Run 3 parallel download streams and sum their throughput
            num_threads  = 3
            results      = []

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(_download_once, url, 30) for _ in range(num_threads)]
                for future in as_completed(futures):
                    try:
                        bytes_dl, duration = future.result()
                        if duration > 0 and bytes_dl > 0:
                            results.append((bytes_dl, duration))
                    except Exception as e:
                        print(f"[DEBUG] A parallel download thread failed: {e}")

            if not results:
                print(f"[DEBUG] All parallel threads failed for {url}")
                continue

            # Total bytes across all threads / max duration = real throughput
            total_bytes   = sum(r[0] for r in results)
            max_duration  = max(r[1] for r in results)
            speed_bps     = (total_bytes * 8) / max_duration

            print(f"[DEBUG] Parallel download: {total_bytes} bytes in {max_duration:.2f}s from {url}")
            print(f"[DEBUG] Download speed: {round(speed_bps / 1_000_000, 2)} Mbps")

            return {
                "success":    True,
                "speed_bps":  speed_bps,
                "speed_mbps": round(speed_bps / 1_000_000, 2),
                "bytes":      total_bytes,
                "duration":   round(max_duration, 2),
                "threads":    len(results),
            }

        except requests.exceptions.Timeout:
            print(f"[DEBUG] Download timeout from {url}")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Download connection error from {url}: {e}")
            continue
        except Exception as e:
            print(f"[DEBUG] Download error from {url}: {e}")
            continue

    return {
        "success": False,
        "error":   "Download test failed on all endpoints."
    }


# ── Upload ─────────────────────────────────────────────────────

def test_upload_speed():
    """
    Measure upload speed by POSTing random data.
    Uses Cloudflare's upload endpoint (designed for this),
    falls back to httpbin.
    """
    upload_size = 5 * 1024 * 1024   # 5 MB
    data        = b"x" * upload_size

    targets = [UPLOAD_TARGET, UPLOAD_FALLBACK]

    for url in targets:
        try:
            print(f"[DEBUG] Starting upload test to {url} ({upload_size} bytes)")

            start    = time.perf_counter()
            response = requests.post(
                url,
                data=data,
                timeout=60,
                headers={"Content-Type": "application/octet-stream"}
            )
            end      = time.perf_counter()
            duration = end - start

            print(f"[DEBUG] Upload: status={response.status_code}, duration={duration:.2f}s")

            # Cloudflare returns 200; httpbin returns 200 with JSON body
            if duration > 0 and response.status_code == 200:
                speed_bps = (upload_size * 8) / duration
                print(f"[DEBUG] Upload speed: {round(speed_bps / 1_000_000, 2)} Mbps")
                return {
                    "success":    True,
                    "speed_bps":  speed_bps,
                    "speed_mbps": round(speed_bps / 1_000_000, 2),
                    "bytes":      upload_size,
                    "duration":   round(duration, 2),
                }
            else:
                print(f"[DEBUG] Upload got status {response.status_code} from {url}, trying next")
                continue

        except requests.exceptions.Timeout:
            print(f"[DEBUG] Upload timeout to {url}")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Upload connection error to {url}: {e}")
            continue
        except Exception as e:
            print(f"[DEBUG] Upload error to {url}: {e}")
            continue

    return {
        "success": False,
        "error":   "Upload test failed on all endpoints."
    }


# ── Quality labels ─────────────────────────────────────────────

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


# ── Main ───────────────────────────────────────────────────────

def run_speed_test():
    """
    Main function — runs full speed test.
    Returns complete result dict.
    """
    try:
        print("[DEBUG] Starting speed test suite")

        print("[DEBUG] Testing download speed...")
        download = test_download_speed()

        print("[DEBUG] Testing upload speed...")
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
            "success": True,
            "server": {
                "name":    "Cloudflare Speed Test",
                "country": "Global CDN",
                "sponsor": "Cloudflare",
                "latency": 0,
            },
            "download_bps":      download["speed_bps"],
            "upload_bps":        upload["speed_bps"],
            "download_mbps":     download_mbps,
            "upload_mbps":       upload_mbps,
            "download_quality":  get_quality_label("download", download_mbps),
            "upload_quality":    get_quality_label("upload", upload_mbps),
            "download_bytes":    download["bytes"],
            "upload_bytes":      upload["bytes"],
            "download_duration": download["duration"],
            "upload_duration":   upload["duration"],
            "download_threads":  download.get("threads", 1),
        }

        print(f"[DEBUG] Speed test complete: {download_mbps} Mbps down, {upload_mbps} Mbps up")
        return result

    except Exception as e:
        import traceback
        print(f"[ERROR] Speed test crashed: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "error":   f"Speed test failed: {str(e)}"
        }


if __name__ == "__main__":
    result = run_speed_test()
    print(result)