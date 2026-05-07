import time
import statistics
import requests


def http_ping_once(target="https://www.google.com"):
    """
    Single HTTP ping — returns latency in ms or None on failure.
    """
    try:
        start    = time.perf_counter()
        response = requests.get(target, timeout=3, allow_redirects=True)
        end      = time.perf_counter()

        if response.status_code < 500:
            return round((end - start) * 1000, 2)
        return None

    except Exception:
        return None


def calculate_stability_score(avg_latency, jitter, packet_loss):
    """Calculate stability score out of 100"""

    # Latency score (40 points)
    if avg_latency <= 50:
        latency_score = 40
    elif avg_latency <= 100:
        latency_score = 30
    elif avg_latency <= 200:
        latency_score = 20
    else:
        latency_score = 10

    # Jitter score (40 points)
    if jitter <= 10:
        jitter_score = 40
    elif jitter <= 30:
        jitter_score = 30
    elif jitter <= 60:
        jitter_score = 20
    else:
        jitter_score = 10

    # Packet loss score (20 points)
    if packet_loss == 0:
        loss_score = 20
    elif packet_loss <= 1:
        loss_score = 15
    elif packet_loss <= 5:
        loss_score = 10
    else:
        loss_score = 0

    return latency_score + jitter_score + loss_score


def get_stability_label(score):
    """Convert score to label"""
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Fair"
    else:
        return "Poor"


def classify_connection(avg_latency, jitter, packet_loss):
    """Classify connection type based on behavior"""
    if avg_latency <= 50 and jitter <= 10 and packet_loss == 0:
        return "Fiber / High-Speed Broadband"
    elif avg_latency <= 100 and jitter <= 30 and packet_loss <= 1:
        return "Cable / Standard Broadband"
    elif avg_latency <= 200 and jitter <= 60:
        return "DSL / Wireless Broadband"
    elif avg_latency > 200 and packet_loss > 2:
        return "Mobile Data / Weak Signal"
    else:
        return "Unknown / Mixed Connection"


def run_stability_test(duration=30, interval=1):
    """
    Run HTTP-based stability test over time.
    Yields live ping data and returns final result.
    This is a generator — yields each ping as it happens.
    """
    target     = "https://www.google.com"
    latencies  = []
    errors     = 0
    total      = 0
    start_time = time.time()

    while time.time() - start_time < duration:
        total   += 1
        elapsed  = int(time.time() - start_time)
        latency  = http_ping_once(target)

        if latency is None:
            errors += 1
            yield {
                "type":    "ping",
                "latency": 0,
                "elapsed": elapsed,
                "timeout": True,
            }
        else:
            latencies.append(latency)
            yield {
                "type":    "ping",
                "latency": latency,
                "elapsed": elapsed,
                "timeout": False,
            }

        time.sleep(interval)

    # Build final result
    if not latencies:
        yield {
            "type":    "result",
            "success": False,
            "error":   "No successful pings during stability test."
        }
        return

    avg_latency     = round(statistics.mean(latencies), 2)
    min_latency     = round(min(latencies), 2)
    max_latency     = round(max(latencies), 2)
    jitter          = round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0
    packet_loss     = round((errors / total) * 100, 1)
    latency_range   = round(max_latency - min_latency, 2)
    stability_score = calculate_stability_score(avg_latency, jitter, packet_loss)
    stability_label = get_stability_label(stability_score)
    connection_type = classify_connection(avg_latency, jitter, packet_loss)

    yield {
        "type":             "result",
        "success":          True,
        "host":             target,
        "duration":         duration,
        "total_pings":      total,
        "successful_pings": len(latencies),
        "failed_pings":     errors,
        "packet_loss":      packet_loss,
        "min_latency":      min_latency,
        "max_latency":      max_latency,
        "avg_latency":      avg_latency,
        "jitter":           jitter,
        "latency_range":    latency_range,
        "stability_score":  stability_score,
        "stability_label":  stability_label,
        "connection_type":  connection_type,
        "jitter_quality":   "Excellent" if jitter <= 10 else "Good" if jitter <= 30 else "Average" if jitter <= 60 else "Poor",
        "loss_quality":     "Excellent" if packet_loss == 0 else "Good" if packet_loss <= 1 else "Average" if packet_loss <= 5 else "Poor",
    }


if __name__ == "__main__":
    print("Running 10 second stability test...")
    for event in run_stability_test(duration=10):
        print(event)