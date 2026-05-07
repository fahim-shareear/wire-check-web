import time
import statistics
import requests


def http_ping(host="https://8.8.8.8", count=10):
    """
    Simulate ping using HTTP request timing.
    Measures round-trip time of HTTP requests.
    """
    results = []
    errors  = 0

    # Use reliable public endpoints
    targets = [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://www.amazon.com",
    ]
    target = targets[0]

    for i in range(count):
        try:
            start    = time.perf_counter()
            response = requests.get(
                target,
                timeout=3,
                allow_redirects=True
            )
            end      = time.perf_counter()

            if response.status_code < 500:
                latency = round((end - start) * 1000, 2)
                results.append(latency)
            else:
                errors += 1

        except requests.exceptions.Timeout:
            errors += 1
        except requests.exceptions.ConnectionError:
            errors += 1
        except Exception:
            errors += 1

    return {
        "host":    target,
        "count":   count,
        "results": results,
        "errors":  errors,
    }


def analyze_ping(ping_data):
    """Analyze raw ping results"""
    results = ping_data["results"]
    count   = ping_data["count"]
    errors  = ping_data["errors"]

    if not results:
        return {
            "success": False,
            "error":   "All ping attempts failed."
        }

    avg_latency  = round(statistics.mean(results), 2)
    min_latency  = round(min(results), 2)
    max_latency  = round(max(results), 2)
    jitter       = round(statistics.stdev(results), 2) if len(results) > 1 else 0.0
    packet_loss  = round((errors / count) * 100, 1)

    def quality(metric, value):
        thresholds = {
            "ping":         [(20, "Excellent"), (50, "Good"), (100, "Average"), (float("inf"), "Poor")],
            "jitter":       [(5, "Excellent"), (10, "Good"), (20, "Average"), (float("inf"), "Poor")],
            "packet_loss":  [(0, "Excellent"), (1, "Good"), (5, "Average"), (float("inf"), "Poor")],
        }
        for threshold, label in thresholds[metric]:
            if value <= threshold:
                return label
        return "Poor"

    return {
        "success":          True,
        "host":             ping_data["host"],
        "packets_sent":     count,
        "packets_received": len(results),
        "packet_loss":      packet_loss,
        "min_latency":      min_latency,
        "avg_latency":      avg_latency,
        "max_latency":      max_latency,
        "jitter":           jitter,
        "ping_quality":     quality("ping", avg_latency),
        "jitter_quality":   quality("jitter", jitter),
        "loss_quality":     quality("packet_loss", packet_loss),
    }


def run_ping_test(count=10):
    """Main function — runs ping and returns full analysis"""
    raw = http_ping(count=count)
    return analyze_ping(raw)


if __name__ == "__main__":
    result = run_ping_test()
    print(result)