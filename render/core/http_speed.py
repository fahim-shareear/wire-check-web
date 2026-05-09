"""Speed testing module - Real ISP speed measurement"""
import time
import requests
import io


# Use services optimized for accurate speed testing
DOWNLOAD_TARGETS = [
    "https://httpbin.org/bytes/100000000",      # 100MB (will download for ~10-15 seconds on typical connection)
    "https://speed.cloudflare.com/__down?bytes=100000000",
]

UPLOAD_TARGET = "https://httpbin.org/post"
TEST_DURATION = 15  # seconds - measure sustained speed for 15 seconds


def test_download_speed():
    """
    Measure real download speed by downloading data and measuring
    sustained throughput over TEST_DURATION seconds.
    This measures your ACTUAL ISP download speed, not peak burst.
    """
    for url in DOWNLOAD_TARGETS:
        try:
            print(f"[SPEED TEST] Starting download test from {url}")
            start_time = time.perf_counter()
            total_bytes = 0
            
            response = requests.get(url, timeout=45, stream=True)
            
            # Measure bytes downloaded over time window
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_bytes += len(chunk)
                
                # Stop after TEST_DURATION seconds
                elapsed = time.perf_counter() - start_time
                if elapsed >= TEST_DURATION:
                    break
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # Ensure we have meaningful data
            if duration > 2 and total_bytes > 0:
                # Calculate sustained speed (bits per second)
                speed_bps = (total_bytes * 8) / duration
                speed_mbps = round(speed_bps / 1_000_000, 2)
                
                print(f"[SPEED TEST] Download: {total_bytes} bytes in {duration:.2f}s = {speed_mbps} Mbps")
                
                return {
                    "success": True,
                    "speed_bps": speed_bps,
                    "speed_mbps": speed_mbps,
                    "bytes": total_bytes,
                    "duration": round(duration, 2),
                }
        
        except requests.exceptions.Timeout:
            print(f"[SPEED TEST] Download timeout from {url}")
            continue
        except Exception as e:
            print(f"[SPEED TEST] Download error from {url}: {str(e)}")
            continue
    
    return {
        "success": False,
        "error": "Download test failed. Check your connection."
    }


def test_upload_speed():
    """
    Measure real upload speed by uploading data in chunks and measuring
    sustained throughput over TEST_DURATION seconds.
    This measures your ACTUAL ISP upload speed, not peak burst.
    
    Note: With thread=1 (single thread), this gives accurate single-threaded speed.
    """
    chunk_size = 256 * 1024  # 256KB chunks (more realistic for ISP testing)
    total_uploaded = 0
    
    try:
        print(f"[SPEED TEST] Starting upload test to {UPLOAD_TARGET}")
        start_time = time.perf_counter()
        
        # Create a generator that yields chunks
        def data_generator():
            """Generate data chunks for upload"""
            nonlocal total_uploaded
            elapsed = time.perf_counter() - start_time
            
            while elapsed < TEST_DURATION:
                chunk = b"x" * chunk_size
                total_uploaded += len(chunk)
                yield chunk
                elapsed = time.perf_counter() - start_time
        
        # Upload with streaming
        response = requests.post(
            UPLOAD_TARGET,
            data=data_generator(),
            timeout=45,
            headers={"Content-Type": "application/octet-stream"},
            stream=True
        )
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Ensure we have meaningful data
        if duration > 2 and response.status_code == 200 and total_uploaded > 0:
            # Calculate sustained speed (bits per second)
            speed_bps = (total_uploaded * 8) / duration
            speed_mbps = round(speed_bps / 1_000_000, 2)
            
            print(f"[SPEED TEST] Upload: {total_uploaded} bytes in {duration:.2f}s = {speed_mbps} Mbps")
            
            return {
                "success": True,
                "speed_bps": speed_bps,
                "speed_mbps": speed_mbps,
                "bytes": total_uploaded,
                "duration": round(duration, 2),
            }
        else:
            print(f"[SPEED TEST] Upload failed: status={response.status_code}, duration={duration}, bytes={total_uploaded}")
            return {
                "success": False,
                "error": "Upload test failed with bad response."
            }
    
    except requests.exceptions.Timeout:
        print(f"[SPEED TEST] Upload timeout")
        return {
            "success": False,
            "error": "Upload test timed out."
        }
    except Exception as e:
        print(f"[SPEED TEST] Upload error: {str(e)}")
        return {
            "success": False,
            "error": f"Upload test failed: {str(e)}"
        }


def get_quality_label(metric, value):
    """
    Get quality label for speed metrics based on real ISP standards.
    
    ISP Speed Classifications:
      Download:
        < 5 Mbps = Poor (unusable)
        5-25 Mbps = Average (basic web browsing)
        25-100 Mbps = Good (HD streaming, video calls)
        > 100 Mbps = Excellent (4K, gaming, multiple users)
      
      Upload:
        < 1 Mbps = Poor (can't upload)
        1-10 Mbps = Average (basic uploads)
        10-50 Mbps = Good (video calls, live streaming)
        > 50 Mbps = Excellent (professional streaming)
    """
    thresholds = {
        "download": [
            (100, "Excellent"),    # > 100 Mbps
            (25, "Good"),          # 25-100 Mbps  (Your 30 Mbps ISP = Good)
            (5, "Average"),        # 5-25 Mbps
            (0, "Poor")            # < 5 Mbps
        ],
        "upload": [
            (50, "Excellent"),     # > 50 Mbps
            (10, "Good"),          # 10-50 Mbps
            (1, "Average"),        # 1-10 Mbps
            (0, "Poor")            # < 1 Mbps
        ],
    }
    
    for threshold, label in thresholds[metric]:
        if value >= threshold:
            return label
    return "Poor"


def run_speed_test():
    """Main function - runs full speed test"""
    download = test_download_speed()
    upload = test_upload_speed()
    
    if not download["success"]:
        return {
            "success": False,
            "error": download.get("error", "Download test failed.")
        }
    
    if not upload["success"]:
        return {
            "success": False,
            "error": upload.get("error", "Upload test failed.")
        }
    
    download_mbps = download["speed_mbps"]
    upload_mbps = upload["speed_mbps"]
    
    return {
        "success": True,
        "server": {
            "name": "Cloudflare / httpbin",
            "country": "Global CDN",
            "sponsor": "Cloudflare",
            "latency": 0,
        },
        "download_bps": download["speed_bps"],
        "upload_bps": upload["speed_bps"],
        "download_mbps": download_mbps,
        "upload_mbps": upload_mbps,
        "download_quality": get_quality_label("download", download_mbps),
        "upload_quality": get_quality_label("upload", upload_mbps),
        "download_bytes": download["bytes"],
        "upload_bytes": upload["bytes"],
        "download_duration": download["duration"],
        "upload_duration": upload["duration"],
    }


if __name__ == "__main__":
    result = run_speed_test()
    print(result)