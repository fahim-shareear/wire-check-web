import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── Test endpoints ─────────────────────────────────────────────

DOWNLOAD_TARGETS = [
    "https://speed.cloudflare.com/__down?bytes=100000000",  # 100MB
    "https://speed.cloudflare.com/__down?bytes=50000000",   # 50MB fallback
    "https://proof.ovh.net/files/100Mb.dat",                # OVH fallback
]

UPLOAD_TARGET = "https://speed.cloudflare.com/__up"
UPLOAD_FALLBACK = "https://httpbin.org/post"


# ── Configuration ──────────────────────────────────────────────

DOWNLOAD_THREADS = 3
DOWNLOAD_TIMEOUT = 60
UPLOAD_TIMEOUT = 60

DOWNLOAD_CHUNK_SIZE = 1024 * 256   # 256KB
UPLOAD_SIZE = 10 * 1024 * 1024     # 10MB


# ── Download Worker ────────────────────────────────────────────

def _download_once(url, timeout=DOWNLOAD_TIMEOUT):
    """
    Download a file and return bytes downloaded.
    """
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    total_bytes = 0

    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
        if chunk:
            total_bytes += len(chunk)

    return total_bytes


# ── Download Test ──────────────────────────────────────────────

def test_download_speed():
    """
    Measures download speed using parallel streams.
    Uses REAL wall-clock timing instead of per-thread timing.
    """

    for url in DOWNLOAD_TARGETS:

        try:
            print(f"[DEBUG] Attempting download from: {url}")

            # Warm-up connection (not measured)
            try:
                requests.get(url, timeout=10, stream=True).close()
            except Exception:
                pass

            results = []

            # REAL wall-clock timing
            overall_start = time.perf_counter()

            with ThreadPoolExecutor(max_workers=DOWNLOAD_THREADS) as executor:

                futures = [
                    executor.submit(_download_once, url)
                    for _ in range(DOWNLOAD_THREADS)
                ]

                for future in as_completed(futures):
                    try:
                        bytes_downloaded = future.result()

                        if bytes_downloaded > 0:
                            results.append(bytes_downloaded)

                    except Exception as e:
                        print(f"[DEBUG] Download thread failed: {e}")

            overall_end = time.perf_counter()

            if not results:
                print("[DEBUG] All download threads failed")
                continue

            total_duration = overall_end - overall_start
            total_bytes = sum(results)

            if total_duration <= 0:
                continue

            speed_bps = (total_bytes * 8) / total_duration
            speed_mbps = speed_bps / 1_000_000

            print(
                f"[DEBUG] Downloaded {total_bytes} bytes "
                f"in {total_duration:.2f}s"
            )

            print(f"[DEBUG] Download speed: {speed_mbps:.2f} Mbps")

            return {
                "success": True,
                "speed_bps": speed_bps,
                "speed_mbps": round(speed_mbps, 2),
                "bytes": total_bytes,
                "duration": round(total_duration, 2),
                "threads": len(results),
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
        "error": "Download test failed on all endpoints."
    }


# ── Upload Test ────────────────────────────────────────────────

def test_upload_speed():
    """
    Measures upload speed using RANDOM DATA
    to prevent compression/cache optimization.
    """

    # RANDOM non-compressible payload
    data = os.urandom(UPLOAD_SIZE)

    targets = [UPLOAD_TARGET, UPLOAD_FALLBACK]

    for url in targets:

        try:
            print(
                f"[DEBUG] Starting upload test to {url} "
                f"({UPLOAD_SIZE} bytes)"
            )

            start = time.perf_counter()

            response = requests.post(
                url,
                data=data,
                timeout=UPLOAD_TIMEOUT,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Cache-Control": "no-cache",
                },
            )

            end = time.perf_counter()

            duration = end - start

            print(
                f"[DEBUG] Upload response: "
                f"status={response.status_code}, "
                f"duration={duration:.2f}s"
            )

            if duration <= 0:
                continue

            if response.status_code == 200:

                speed_bps = (UPLOAD_SIZE * 8) / duration
                speed_mbps = speed_bps / 1_000_000

                print(f"[DEBUG] Upload speed: {speed_mbps:.2f} Mbps")

                return {
                    "success": True,
                    "speed_bps": speed_bps,
                    "speed_mbps": round(speed_mbps, 2),
                    "bytes": UPLOAD_SIZE,
                    "duration": round(duration, 2),
                }

            else:
                print(
                    f"[DEBUG] Upload got status "
                    f"{response.status_code}"
                )

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
        "error": "Upload test failed on all endpoints."
    }


# ── Quality Labels ─────────────────────────────────────────────

def get_quality_label(metric, value):

    thresholds = {
        "download": [
            (100, "Excellent"),
            (25, "Good"),
            (5, "Average"),
            (0, "Poor"),
        ],

        "upload": [
            (50, "Excellent"),
            (10, "Good"),
            (2, "Average"),
            (0, "Poor"),
        ],
    }

    for threshold, label in thresholds[metric]:
        if value >= threshold:
            return label

    return "Poor"


# ── Main Speed Test ────────────────────────────────────────────

def run_speed_test():

    try:

        print("[DEBUG] Starting speed test suite")

        # ── Download ─────────────────────

        print("[DEBUG] Testing download speed...")
        download = test_download_speed()

        if not download["success"]:
            return {
                "success": False,
                "error": download.get(
                    "error",
                    "Download test failed."
                )
            }

        # ── Upload ───────────────────────

        print("[DEBUG] Testing upload speed...")
        upload = test_upload_speed()

        if not upload["success"]:
            return {
                "success": False,
                "error": upload.get(
                    "error",
                    "Upload test failed."
                )
            }

        # ── Final Results ────────────────

        download_mbps = download["speed_mbps"]
        upload_mbps = upload["speed_mbps"]

        result = {

            "success": True,

            "server": {
                "name": "Cloudflare Speed Test",
                "country": "Global CDN",
                "sponsor": "Cloudflare",
                "latency": 0,
            },

            "download_bps": download["speed_bps"],
            "upload_bps": upload["speed_bps"],

            "download_mbps": download_mbps,
            "upload_mbps": upload_mbps,

            "download_quality": get_quality_label(
                "download",
                download_mbps
            ),

            "upload_quality": get_quality_label(
                "upload",
                upload_mbps
            ),

            "download_bytes": download["bytes"],
            "upload_bytes": upload["bytes"],

            "download_duration": download["duration"],
            "upload_duration": upload["duration"],

            "download_threads": download["threads"],
        }

        print(
            f"[DEBUG] Speed test complete: "
            f"{download_mbps} Mbps down, "
            f"{upload_mbps} Mbps up"
        )

        return result

    except Exception as e:

        import traceback

        print(f"[ERROR] Speed test crashed: {e}")
        traceback.print_exc()

        return {
            "success": False,
            "error": f"Speed test failed: {e}"
        }


# ── Entry Point ────────────────────────────────────────────────

if __name__ == "__main__":

    result = run_speed_test()

    print("\n==============================")
    print("        SPEED TEST")
    print("==============================")

    if result["success"]:

        print(f"Download : {result['download_mbps']} Mbps")
        print(f"Upload   : {result['upload_mbps']} Mbps")

        print(f"Download Quality : {result['download_quality']}")
        print(f"Upload Quality   : {result['upload_quality']}")

        print(f"Threads Used     : {result['download_threads']}")

        print(
            f"Download Duration: "
            f"{result['download_duration']}s"
        )

        print(
            f"Upload Duration  : "
            f"{result['upload_duration']}s"
        )

    else:
        print(f"ERROR: {result['error']}")