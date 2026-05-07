// ── State ──────────────────────────────────────────────────────
var eventSource = null;

// ── Main Functions ─────────────────────────────────────────────

function startTest() {
    resetUI();
    setStatus("Initializing tests...", "running");
    setButtons(true);

    eventSource = new EventSource("/api/run");

    eventSource.addEventListener("progress", function(e) {
        var data = JSON.parse(e.data);
        setProgress(data.percent);
        setStatus(data.message, "running");
    });

    eventSource.addEventListener("isp", function(e) {
        var data = JSON.parse(e.data);
        updateISP(data);
        setStage("isp", "done");
    });

    eventSource.addEventListener("ping", function(e) {
        var data = JSON.parse(e.data);
        updatePing(data);
        setStage("ping", "done");
    });

    eventSource.addEventListener("speed", function(e) {
        var data = JSON.parse(e.data);
        updateSpeed(data);
        setStage("speed", "done");
    });

    eventSource.addEventListener("stability_ping", function(e) {
        var data = JSON.parse(e.data);
        appendPingLog(data);
        setStage("stability", "running");
    });

    eventSource.addEventListener("stability", function(e) {
        var data = JSON.parse(e.data);
        updateStability(data);
        setStage("stability", "done");
    });

    eventSource.addEventListener("done", function(e) {
        setProgress(100);
        setStatus("All tests complete.", "done");
        setButtons(false);
        eventSource.close();
        eventSource = null;
    });

    eventSource.onerror = function() {
        setStatus("Connection error. Try again.", "error");
        setButtons(false);
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
    setStatus("Test stopped by user.", "error");
    setButtons(false);
}

// ── UI Update Functions ────────────────────────────────────────

function updateISP(result) {
    if (!result.success) return;
    var d = result.data;
    setText("isp-ip",       d.ip);
    setText("isp-org",      d.isp);
    setText("isp-city",     d.city);
    setText("isp-country",  d.country + " — " + d.region);
    setText("isp-timezone", d.timezone);
    setText("sum-isp",      d.isp);
}

function updatePing(result) {
    if (!result.success) return;
    setText("ping-avg",             String(result.avg_latency));
    setText("ping-min",             result.min_latency + " ms");
    setText("ping-max",             result.max_latency + " ms");
    setText("ping-jitter",          result.jitter + " ms");
    setText("ping-loss",            result.packet_loss + "%");
    setQuality("ping-quality",          result.ping_quality);
    setQuality("ping-jitter-quality",   result.jitter_quality);
    setText("sum-ping", result.avg_latency + " ms — " + result.ping_quality);
}

function updateSpeed(result) {
    if (!result.success) return;
    setText("dl-value",      String(result.download_mbps));
    setText("ul-value",      String(result.upload_mbps));
    setQuality("dl-quality", result.download_quality);
    setQuality("ul-quality", result.upload_quality);
    setBar("dl-bar", Math.min(result.download_mbps, 100));
    setBar("ul-bar", Math.min(result.upload_mbps, 100));
    setText("speed-server",  result.server.name + ", " + result.server.country);
    setText("speed-sponsor", result.server.sponsor);
    setText("speed-latency", result.server.latency + " ms");
    setText("sum-download",  result.download_mbps + " Mbps — " + result.download_quality);
    setText("sum-upload",    result.upload_mbps + " Mbps — " + result.upload_quality);
}

function updateStability(result) {
    if (!result.success) return;
    setText("stab-score",  String(result.stability_score));
    setBar("stab-bar",     result.stability_score);
    setText("stab-avg",    result.avg_latency + " ms");
    setText("stab-jitter", result.jitter + " ms");
    setText("stab-loss",   result.packet_loss + "%");
    setText("stab-range",  result.latency_range + " ms");
    setText("stab-type",   result.connection_type);
    setQuality("stab-label", result.stability_label);
    setText("sum-stability", result.stability_score + "/100 — " + result.stability_label);
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
        el.style.width = percent + "%";
    }
}

function setQuality(id, quality) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = quality;
    el.className = "metric-value quality-" + quality.toLowerCase();
}

function setProgress(percent) {
    var el = document.getElementById("progress-fill");
    if (el) {
        el.style.width = percent + "%";
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