"""
Speed testing module - Real ISP speed measurement
Measures sustained throughput over 15 seconds for accurate ISP speed
"""
import time
import requests


# Download and upload test targets
DOWNLOAD_TARGETS = [
    "https://httpbin.org/bytes/100000000",           # 100MB file
    "https://speed.cloudflare.com/__down?bytes=100000000",  # Fallback
]

UPLOAD_TARGET = "https://httpbin.org/post"

# Test duration in seconds - long enough for accurate measurement
TEST_DURATION = 15

# Chunk size for realistic streaming
CHUNK_SIZE = 8192


def test_download_speed():
    """
    Measure REAL download speed by downloading a large file 
    and measuring sustained throughput over TEST_DURATION seconds.
    
    This measures your ACTUAL ISP download speed, not peak burst speed.
    
    How it works:
    1. Start downloading a large file (100MB)
    2. Measure bytes received over TEST_DURATION seconds (15 sec)
    3. Calculate: (bytes * 8 bits) / duration in seconds = speed in bits/sec
    4. Stop after TEST_DURATION elapsed
    
    Returns:
        dict: {success, speed_bps, speed_mbps, bytes, duration} or error
    """
    
    for url in DOWNLOAD_TARGETS:
        try:
            print(f"[SPEED TEST] Starting download test")
            print(f"[SPEED TEST] Target: {url}")
            print(f"[SPEED TEST] Duration: {TEST_DURATION} seconds")
            
            start_time = time.perf_counter()
            total_bytes = 0
            
            # Start downloading the file in stream mode
            response = requests.get(url, timeout=45, stream=True)
            response.raise_for_status()
            
            # Download chunks and measure throughput over time
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    total_bytes += len(chunk)
                
                # Check elapsed time
                elapsed = time.perf_counter() - start_time
                
                # Stop after TEST_DURATION seconds
                if elapsed >= TEST_DURATION:
                    print(f"[SPEED TEST] Reached {TEST_DURATION}s limit, stopping download")
                    break
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # Validate we got meaningful data
            if duration > 2 and total_bytes > 0:
                # Calculate speed in bits per second
                speed_bps = (total_bytes * 8) / duration
                speed_mbps = round(speed_bps / 1_000_000, 2)
                
                print(f"[SPEED TEST] ✓ Download complete")
                print(f"[SPEED TEST] Data: {total_bytes:,} bytes in {duration:.2f} seconds")
                print(f"[SPEED TEST] Speed: {speed_mbps} Mbps")
                
                return {
                    "success": True,
                    "speed_bps": speed_bps,
                    "speed_mbps": speed_mbps,
                    "bytes": total_bytes,
                    "duration": round(duration, 2),
                }
            else:
                print(f"[SPEED TEST] ✗ Download failed: duration={duration}, bytes={total_bytes}")
                continue
        
        except requests.exceptions.Timeout:
            print(f"[SPEED TEST] ✗ Download timeout from {url}")
            continue
        
        except requests.exceptions.ConnectionError as e:
            print(f"[SPEED TEST] ✗ Connection error: {str(e)}")
            continue
        
        except Exception as e:
            print(f"[SPEED TEST] ✗ Download error: {str(e)}")
            continue
    
    # All targets failed
    print(f"[SPEED TEST] ✗ All download targets failed")
    return {
        "success": False,
        "error": "Download test failed. Check your internet connection."
    }


def test_upload_speed():
    """
    Measure REAL upload speed by uploading data in chunks
    and measuring sustained throughput over TEST_DURATION seconds.
    
    This measures your ACTUAL ISP upload speed, not peak burst speed.
    
    How it works:
    1. Generate data chunks (256KB each - realistic streaming size)
    2. Upload continuously for TEST_DURATION seconds (15 sec)
    3. Calculate: (bytes_uploaded * 8 bits) / duration in seconds = speed in bits/sec
    4. Stop after TEST_DURATION elapsed
    
    Note: Single-threaded upload (thread=1) for accurate ISP measurement
    
    Returns:
        dict: {success, speed_bps, speed_mbps, bytes, duration} or error
    """
    
    chunk_size = 256 * 1024  # 256KB chunks - realistic for ISP testing
    total_uploaded = 0
    
    try:
        print(f"[SPEED TEST] Starting upload test")
        print(f"[SPEED TEST] Target: {UPLOAD_TARGET}")
        print(f"[SPEED TEST] Chunk size: {chunk_size / 1024:.0f}KB")
        print(f"[SPEED TEST] Duration: {TEST_DURATION} seconds")
        print(f"[SPEED TEST] Mode: Single-threaded (thread=1)")
        
        start_time = time.perf_counter()
        
        # Generator function that yields data chunks
        def data_generator():
            """
            Generate data chunks continuously until TEST_DURATION elapsed.
            Simulates realistic streaming upload.
            """
            nonlocal total_uploaded
            
            while True:
                # Check elapsed time
                elapsed = time.perf_counter() - start_time
                
                # Stop if we've reached the time limit
                if elapsed >= TEST_DURATION:
                    print(f"[SPEED TEST] Reached {TEST_DURATION}s limit, stopping upload")
                    break
                
                # Generate a 256KB chunk of data
                chunk = b"x" * chunk_size
                total_uploaded += len(chunk)
                
                yield chunk
        
        # Upload with streaming (chunked)
        response = requests.post(
            UPLOAD_TARGET,
            data=data_generator(),
            timeout=45,
            headers={"Content-Type": "application/octet-stream"},
            stream=True
        )
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Validate response and data
        if duration > 2 and response.status_code == 200 and total_uploaded > 0:
            # Calculate speed in bits per second
            speed_bps = (total_uploaded * 8) / duration
            speed_mbps = round(speed_bps / 1_000_000, 2)
            
            print(f"[SPEED TEST] ✓ Upload complete")
            print(f"[SPEED TEST] Data: {total_uploaded:,} bytes in {duration:.2f} seconds")
            print(f"[SPEED TEST] Speed: {speed_mbps} Mbps")
            
            return {
                "success": True,
                "speed_bps": speed_bps,
                "speed_mbps": speed_mbps,
                "bytes": total_uploaded,
                "duration": round(duration, 2),
            }
        else:
            print(f"[SPEED TEST] ✗ Upload failed: status={response.status_code}, duration={duration}, bytes={total_uploaded}")
            return {
                "success": False,
                "error": "Upload test failed with bad response."
            }
    
    except requests.exceptions.Timeout:
        print(f"[SPEED TEST] ✗ Upload timeout")
        return {
            "success": False,
            "error": "Upload test timed out."
        }
    
    except Exception as e:
        print(f"[SPEED TEST] ✗ Upload error: {str(e)}")
        return {
            "success": False,
            "error": f"Upload test failed: {str(e)}"
        }


def get_quality_label(metric, value):
    """
    Get quality label for speed metrics based on REAL ISP standards.
    
    NOT based on server-to-server speed, but on actual ISP package speeds.
    
    Download Speed Standards:
      < 5 Mbps = Poor (unusable for modern internet)
      5-25 Mbps = Average (basic web browsing only)
      25-100 Mbps = Good (HD streaming, video calls, normal use)
      > 100 Mbps = Excellent (4K streaming, gaming, multiple users)
    
    Upload Speed Standards:
      < 1 Mbps = Poor (can't upload)
      1-10 Mbps = Average (basic uploads, Zoom)
      10-50 Mbps = Good (video calls, live streaming, large uploads)
      > 50 Mbps = Excellent (professional streaming, content creation)
    
    Args:
        metric (str): "download" or "upload"
        value (float): speed in Mbps
    
    Returns:
        str: Quality label (Excellent, Good, Average, Poor)
    """
    
    thresholds = {
        "download": [
            (100, "Excellent"),    # > 100 Mbps
            (25, "Good"),          # 25-100 Mbps (Your 30 Mbps = Good)
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
    
    # Find matching threshold
    for threshold, label in thresholds[metric]:
        if value >= threshold:
            return label
    
    return "Poor"


def run_speed_test():
    """
    Main speed test function - runs download and upload tests sequentially.
    
    Process:
    1. Run download test (15 seconds)
    2. Run upload test (15 seconds)
    3. Calculate quality labels
    4. Return complete results
    
    Total time: ~30-40 seconds (includes overhead)
    
    Returns:
        dict: Complete speed test results with download, upload, quality ratings
    """
    
    print("[SPEED TEST] ========================================")
    print("[SPEED TEST] Starting Real ISP Speed Measurement")
    print("[SPEED TEST] ========================================")
    
    # Run download test
    print("[SPEED TEST] Phase 1/2: Download Test")
    print("[SPEED TEST] ----------------------------------------")
    download = test_download_speed()
    print()
    
    # Check download result
    if not download["success"]:
        print(f"[SPEED TEST] ✗ Download failed: {download.get('error')}")
        return {
            "success": False,
            "error": download.get("error", "Download test failed.")
        }
    
    # Run upload test
    print("[SPEED TEST] Phase 2/2: Upload Test")
    print("[SPEED TEST] ----------------------------------------")
    upload = test_upload_speed()
    print()
    
    # Check upload result
    if not upload["success"]:
        print(f"[SPEED TEST] ✗ Upload failed: {upload.get('error')}")
        return {
            "success": False,
            "error": upload.get("error", "Upload test failed.")
        }
    
    # Extract speeds
    download_mbps = download["speed_mbps"]
    upload_mbps = upload["speed_mbps"]
    
    # Build result
    result = {
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
    
    # Print summary
    print("[SPEED TEST] ========================================")
    print("[SPEED TEST] Speed Test Complete")
    print("[SPEED TEST] ========================================")
    print(f"[SPEED TEST] Download: {download_mbps} Mbps ({result['download_quality']})")
    print(f"[SPEED TEST] Upload: {upload_mbps} Mbps ({result['upload_quality']})")
    print("[SPEED TEST] ========================================")
    print()
    
    return result


# Allow testing directly
if __name__ == "__main__":
    result = run_speed_test()
    print("Final Result:")
    print(result)