// ── State ──────────────────────────────────────────────────────
var eventSource = null;
var testInProgress = false;

// ── Main Functions ─────────────────────────────────────────────

function startTest() {
    if (testInProgress) {
        alert("Test already in progress!");
        return;
    }

    resetUI();
    setStatus("Initializing tests...", "running");
    setButtons(true);
    testInProgress = true;

    eventSource = new EventSource("/api/run");

    eventSource.addEventListener("progress", function(e) {
        try {
            var data = JSON.parse(e.data);
            setProgress(data.percent);
            setStatus(data.message, "running");
        } catch (err) {
            console.error("Error parsing progress:", err);
        }
    });

    eventSource.addEventListener("isp", function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.success) {
                updateISP(data);
                setStage("isp", "done");
            } else {
                console.error("ISP lookup failed:", data.error);
                setStatus("ISP lookup failed: " + data.error, "error");
            }
        } catch (err) {
            console.error("Error parsing ISP data:", err);
        }
    });

    eventSource.addEventListener("ping", function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.success) {
                updatePing(data);
                setStage("ping", "done");
            } else {
                console.error("Ping test failed:", data.error);
                setStatus("Ping test failed: " + data.error, "error");
            }
        } catch (err) {
            console.error("Error parsing ping data:", err);
        }
    });

    eventSource.addEventListener("speed", function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.success) {
                updateSpeed(data);
                setStage("speed", "done");
            } else {
                console.error("Speed test failed:", data.error);
                setStatus("Speed test failed: " + data.error, "error");
            }
        } catch (err) {
            console.error("Error parsing speed data:", err);
        }
    });

    eventSource.addEventListener("stability_ping", function(e) {
        try {
            var data = JSON.parse(e.data);
            appendPingLog(data);
            setStage("stability", "running");
        } catch (err) {
            console.error("Error parsing stability ping:", err);
        }
    });

    eventSource.addEventListener("stability", function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.success) {
                updateStability(data);
                setStage("stability", "done");
            } else {
                console.error("Stability test failed:", data.error);
                setStatus("Stability test failed: " + data.error, "error");
            }
        } catch (err) {
            console.error("Error parsing stability data:", err);
        }
    });

    eventSource.addEventListener("done", function(e) {
        setProgress(100);
        setStatus("All tests complete.", "done");
        setButtons(false);
        testInProgress = false;
        eventSource.close();
        eventSource = null;
    });

    eventSource.addEventListener("error", function(e) {
        try {
            var data = JSON.parse(e.data);
            console.error("Backend error:", data.message);
            setStatus("Error: " + data.message, "error");
        } catch (err) {
            console.error("Stream error:", e);
            setStatus("Connection error. Check browser console for details.", "error");
        }
        setButtons(false);
        testInProgress = false;
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    });

    eventSource.onerror = function(err) {
        console.error("EventSource error:", err);
        setStatus("Connection lost. The test may not have completed.", "error");
        setButtons(false);
        testInProgress = false;
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    };
}

function stopTest() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    testInProgress = false;
    setStatus("Test stopped by user.", "error");
    setButtons(false);
}

// ── UI Update Functions ────────────────────────────────────────

function updateISP(result) {
    if (!result.success) return;
    var d = result.data;
    setText("isp-ip",       d.ip || "N/A");
    setText("isp-org",      d.isp || "N/A");
    setText("isp-city",     d.city || "N/A");
    setText("isp-country",  (d.country || "N/A") + " — " + (d.region || "N/A"));
    setText("isp-timezone", d.timezone || "N/A");
    setText("sum-isp",      d.isp || "N/A");
}

function updatePing(result) {
    if (!result.success) return;
    setText("ping-avg",             String(result.avg_latency) + " ms" || "—");
    setText("ping-min",             (result.min_latency || "—") + " ms");
    setText("ping-max",             (result.max_latency || "—") + " ms");
    setText("ping-jitter",          (result.jitter || "—") + " ms");
    setText("ping-loss",            (result.packet_loss || "—") + "%");
    setQuality("ping-quality",          result.ping_quality || "Unknown");
    setQuality("ping-jitter-quality",   result.jitter_quality || "Unknown");
    setText("sum-ping", result.avg_latency + " ms — " + (result.ping_quality || "Unknown"));
}

function updateSpeed(result) {
    if (!result.success) return;
    setText("dl-value",      String(result.download_mbps) || "—");
    setText("ul-value",      String(result.upload_mbps) || "—");
    setQuality("dl-quality", result.download_quality || "Unknown");
    setQuality("ul-quality", result.upload_quality || "Unknown");
    setBar("dl-bar", Math.min(result.download_mbps || 0, 100));
    setBar("ul-bar", Math.min(result.upload_mbps || 0, 100));
    setText("speed-server",  (result.server.name || "Unknown") + ", " + (result.server.country || "Unknown"));
    setText("speed-sponsor", result.server.sponsor || "Unknown");
    setText("speed-latency", (result.server.latency || 0) + " ms");
    setText("sum-download",  result.download_mbps + " Mbps — " + (result.download_quality || "Unknown"));
    setText("sum-upload",    result.upload_mbps + " Mbps — " + (result.upload_quality || "Unknown"));
}

function updateStability(result) {
    if (!result.success) return;
    setText("stab-score",  String(result.stability_score) || "—");
    setBar("stab-bar",     result.stability_score || 0);
    setText("stab-avg",    (result.avg_latency || "—") + " ms");
    setText("stab-jitter", (result.jitter || "—") + " ms");
    setText("stab-loss",   (result.packet_loss || "—") + "%");
    setText("stab-range",  (result.latency_range || "—") + " ms");
    setText("stab-type",   result.connection_type || "Unknown");
    setQuality("stab-label", result.stability_label || "Unknown");
    setText("sum-stability", result.stability_score + "/100 — " + (result.stability_label || "Unknown"));
}

function appendPingLog(data) {
    var log = document.getElementById("ping-log");
    if (!log) return;

    var placeholder = log.querySelector(".log-placeholder");
    if (placeholder) {
        placeholder.remove();
    }

    var line = document.createElement("span");
    line.classList.add("log-line");

    if (data.timeout) {
        line.classList.add("timeout");
        line.textContent = "[" + data.elapsed + "s] Timeout";
    } else {
        var ms = data.latency;
        if (ms < 40) {
            line.classList.add("fast");
        } else if (ms < 80) {
            line.classList.add("medium");
        } else {
            line.classList.add("slow");
        }
        line.textContent = "[" + data.elapsed + "s] " + ms.toFixed(2) + " ms";
    }

    log.appendChild(line);

    var lines = log.querySelectorAll(".log-line");
    if (lines.length > 10) {
        lines[0].remove();
    }

    log.scrollTop = log.scrollHeight;
}

// ── Helper Functions ───────────────────────────────────────────

function setText(id, value) {
    var el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

function setBar(id, percent) {
    var el = document.getElementById(id);
    if (el) {
        el.style.width = Math.max(0, Math.min(100, percent)) + "%";
    }
}

function setQuality(id, quality) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = quality;
    el.className = "metric-value quality-" + (quality || "unknown").toLowerCase();
}

function setProgress(percent) {
    var el = document.getElementById("progress-fill");
    if (el) {
        el.style.width = Math.max(0, Math.min(100, percent)) + "%";
    }
}

function setStatus(message, state) {
    var el = document.getElementById("status-text");
    if (!el) return;
    el.textContent = message;
    el.className = "status-text " + (state || "idle");
}

function setStage(name, state) {
    var stage = document.getElementById("stage-" + name);
    if (!stage) return;
    var dot = stage.querySelector(".dot");
    if (dot) {
        dot.className = "dot " + state;
    }
}

function setButtons(isRunning) {
    var runBtn  = document.getElementById("run-btn");
    var stopBtn = document.getElementById("stop-btn");
    if (runBtn)  runBtn.disabled  = isRunning;
    if (stopBtn) stopBtn.disabled = !isRunning;
}

function resetUI() {
    var ids = [
        "isp-ip", "isp-org", "isp-city", "isp-country", "isp-timezone",
        "dl-value", "ul-value", "dl-quality", "ul-quality",
        "speed-server", "speed-sponsor", "speed-latency",
        "ping-avg", "ping-min", "ping-max", "ping-jitter",
        "ping-loss", "ping-quality", "ping-jitter-quality",
        "stab-score", "stab-avg", "stab-jitter", "stab-loss",
        "stab-range", "stab-type", "stab-label",
        "sum-isp", "sum-ping", "sum-download",
        "sum-upload", "sum-stability"
    ];

    for (var i = 0; i < ids.length; i++) {
        setText(ids[i], "—");
    }

    setBar("dl-bar", 0);
    setBar("ul-bar", 0);
    setBar("stab-bar", 0);
    setProgress(0);

    var log = document.getElementById("ping-log");
    if (log) {
        log.innerHTML = '<span class="log-placeholder">Waiting for stability test...</span>';
    }

    var stages = ["isp", "ping", "speed", "stability"];
    for (var j = 0; j < stages.length; j++) {
        setStage(stages[j], "idle");
    }
}