let ws = null;
let wsReconnectTimer = null;

// ── WebSocket ──────────────────────────────────────────────────────────────

function connectWebSocket() {
    if (wsReconnectTimer) {
        clearTimeout(wsReconnectTimer);
        wsReconnectTimer = null;
    }

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws/attendance`);

    ws.onopen = () => setWsStatus(true);

    ws.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            addLiveFeedEntry(data);
        } catch (_) {}
    };

    ws.onclose = () => {
        setWsStatus(false);
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => ws.close();
}

function setWsStatus(connected) {
    const el = document.getElementById("ws-status");
    if (!el) return;
    el.textContent = connected ? "Live" : "Reconnecting…";
    el.className = `badge ${connected ? "bg-success" : "bg-warning text-dark"}`;
}

// ── Live feed ──────────────────────────────────────────────────────────────

function addLiveFeedEntry(data) {
    const feed = document.getElementById("live-feed");
    if (!feed) return;

    // Remove placeholder
    const ph = feed.querySelector(".feed-placeholder");
    if (ph) ph.remove();

    const isOut = data.attendance_type === "OUT";
    const entry = document.createElement("div");
    entry.className = `live-entry${isOut ? " out" : ""}`;
    entry.innerHTML = `
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-1">
            <div>
                <strong>${escHtml(data.student_name)}</strong>
                <span class="text-muted ms-1">${escHtml(data.class_name)} &mdash; Roll: ${escHtml(data.roll_number)}</span>
            </div>
            <div class="d-flex align-items-center gap-2">
                <span class="badge ${isOut ? "bg-danger" : "bg-success"}">${data.attendance_type}</span>
                <small class="text-muted">${data.timestamp}</small>
            </div>
        </div>`;

    feed.insertBefore(entry, feed.firstChild);

    // Cap at 60 visible entries
    while (feed.children.length > 60) {
        feed.removeChild(feed.lastChild);
    }
}

// ── Toast ──────────────────────────────────────────────────────────────────

function showToast(message, type = "success") {
    let container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-white bg-${type} border-0 show mb-2`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${escHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto"
                    onclick="this.closest('.toast').remove()"></button>
        </div>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

// ── Helpers ────────────────────────────────────────────────────────────────

function escHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
