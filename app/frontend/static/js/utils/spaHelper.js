// ========================================
// spaHelper.js (v2.2) – Smart Partial Loader
// ========================================

export class SPAHelper {
    constructor({ spinnerId, dashboardId, apiUser, cacheTTL = 180000 }) {
        this.spinner = document.getElementById(spinnerId);
        this.dashboard = document.getElementById(dashboardId);
        this.apiUser = apiUser;
        this.cacheTTL = cacheTTL; // Tiempo de vida del caché en ms
        this.cache = new Map();   // key: URL → { html, timestamp }
    }

    // =============================
    // 🔹 Cargar vista dinámica
    // =============================
    async loadDynamicView(url, forceRefresh = false) {
        try {
            if (this.spinner) this.spinner.style.display = "flex";

            // Verifica caché antes del fetch
            const cached = this.cache.get(url);
            if (cached && !forceRefresh && !this._isExpired(cached.timestamp)) {
                this._log("CACHE", `Vista cargada desde memoria: ${url}`);
                this.dashboard.innerHTML = cached.html;
                return cached.html;
            }

            const resp = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-SPA-Client": "UserDashboard",
                    "Authorization": `Bearer ${await this.apiUser.getToken() || ""}`
                }
            });

            if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`);
            const html = await resp.text();

            // Guarda en caché con timestamp
            this.cache.set(url, { html, timestamp: Date.now() });
            this.dashboard.innerHTML = html;
            this._log("FETCH", `Vista actualizada desde servidor: ${url}`);
            return html;

        } catch (err) {
            console.error("❌ Error cargando vista dinámica:", err);
            this.dashboard.innerHTML = "<p>Error al cargar vista parcial.</p>";
        } finally {
            if (this.spinner) this.spinner.style.display = "none";
        }
    }

    // =============================
    // 🔹 Utilidades visuales
    // =============================
    showDashboard() {
        if (this.dashboard) {
            this.dashboard.hidden = false;
            this.dashboard.classList.add("fade-in");
        }
    }

    showSpinner() {
        if (this.spinner) this.spinner.style.display = "flex";
        if (this.dashboard) this.dashboard.style.display = "none";
    }

    switchSection(selector) {
        const sections = this.dashboard?.querySelectorAll("section") || [];
        sections.forEach(s => (s.style.display = "none"));
        const sec = this.dashboard?.querySelector(selector);
        if (sec) sec.style.display = "block";
    }

    // =============================
    // 🔹 Token Timer
    // =============================
    startTokenTimer(expTimestamp) {
        const timerEl = document.getElementById("tokenTimer");
        const progressBar = document.getElementById("tokenProgress");
        if (!timerEl || !progressBar || !expTimestamp) return;

        const totalDuration = expTimestamp * 1000 - Date.now();
        let lastUpdate = performance.now();
        let refreshTriggered = false;

        const update = (now) => {
            const delta = now - lastUpdate;
            if (delta >= 1000) {
                lastUpdate = now;
                const remaining = expTimestamp * 1000 - Date.now();
                const pct = Math.max(0, Math.floor((remaining / totalDuration) * 100));
                this.updateProgressBar(progressBar, pct);
                timerEl.textContent = `⏱ ${this.formatRemaining(remaining)}`;
                if (!refreshTriggered && remaining <= 30000) {
                    refreshTriggered = true;
                    this.apiUser.tryRefreshToken();
                }
            }
            if (expTimestamp * 1000 > Date.now()) {
                requestAnimationFrame(update);
            } else {
                progressBar.classList.add("bg-danger");
                timerEl.textContent = "⛔ Token expirado";
            }
        };
        requestAnimationFrame(update);
    }

    updateProgressBar(progressBar, percentage) {
        progressBar.style.width = `${percentage}%`;
        progressBar.classList.remove("bg-success", "bg-warning", "bg-danger");

        if (percentage <= 29) progressBar.classList.add("bg-danger");
        else if (percentage <= 49) progressBar.classList.add("bg-warning");
        else progressBar.classList.add("bg-success");
    }

    // =============================
    // 🔹 Helpers
    // =============================
    _isExpired(timestamp) {
        return Date.now() - timestamp > this.cacheTTL;
    }

    _log(tag, msg) {
        if (this.apiUser?.debugEnabled) {
            console.log(`📦 [${tag}]`, msg);
        }
    }

    formatRemaining(ms) {
        const totalSec = Math.floor(ms / 1000);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        return `${m}m ${s}s`;
    }

    clearCache() {
        this.cache.clear();
        this._log("CACHE", "Caché SPA limpiado manualmente.");
    }

    async refreshView(url) {
        await this.loadDynamicView(url, true);
    }
}
