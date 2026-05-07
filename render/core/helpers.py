import time
from datetime import datetime

def format_speed(speed_bps):
    """Convert speed from bits per second to human readable format"""
    if speed_bps is None:
        return "N/A"

    mbps = speed_bps / 1_000_000
    gbps = speed_bps / 1_000_000_000

    if gbps >= 1:
        return f"{gbps:.2f} Gbps"
    else:
        return f"{mbps:.2f} Mbps"


def format_latency(ms):
    """Format latency in milliseconds"""
    if ms is None:
        return "N/A"
    return f"{ms:.2f} ms"

def format_packet_loss(loss_percent):
    """format packet loss percentage"""
    if loss_percent is None:
        return "N/A"
    return f"{loss_percent:.1f}%"

def get_quality_label(metric, value):
    """Return a quality label based on metric type and value. Metrics: 'ping', 'download', 'upload', 'jitter', 'packet_loss' """
    if value is None:
        return "Unknown"

    thresholds = {
        "ping":         [(20, "Excellent"), (50, "Good"), (100, "Average"), (float("inf"), "Poor")],
        "download":     [(100, "Excellent"), (25, "Good"), (5, "Average"), (0, "Poor")],
        "upload":       [(50, "Excellent"), (10, "Good"), (2, "Average"), (0, "Poor")],
        "jitter":       [(5, "Excellent"), (10, "Good"), (20, "Average"), (float("inf"), "Poor")],
        "packet_loss":  [(0, "Excellent"), (1, "Good"), (5, "Average"), (float("inf"), "Poor")],
    }

    if metric in ["ping", "jitter", "packet_loss"]:
        # Lower is better
        for threshold, label in thresholds[metric]:
            if value <= threshold:
                return label
    else:
        # Higher is better (download, upload)
        for threshold, label in thresholds[metric]:
            if value >= threshold:
                return label

    return "Poor"

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def timer(func):
    """Decorator to measure how long a function takes to run"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        elapsed = (end - start) * 1000 #converting to ms
        return result, elapsed
    return wrapper