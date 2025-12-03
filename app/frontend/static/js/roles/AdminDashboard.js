// js/roles/AdminDashboard.js
import { showGlobalAlert } from "../layout.js";
import { fetchMetrics } from "../utils/api.js";
import { state } from "../utils/states.js";
import { ApiAdmin } from "../api/ApiAdmin.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js";
import {
    initRealtime,
    renderCategoryChart,
    renderMetricsApi,
    renderChartByCategory
} from "../utils/render_chat.js";
import { renderKPIs, renderEndpointsTable, renderErrors } from "../utils/ui.js";
import { initPerformanceAudit } from "../utils/audit.js";
import { transformData } from "../utils/helper.js";

export class AdminDashboard {
    constructor() {
        this.API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
        this.storage = new IndexedDBStorage("AuthDB", "tokens");
        this.api_admin = new ApiAdmin({ baseURL: this.API_BASE, storage: this.storage });
        this.userCache = null;
        this.tokenTimerInterval = null;
        this.currentAuditPage = 1;

        // Auditoría
        //this.auditar = initPerformanceAudit({
        //    enableHooks: false,
        //    sendToBackendAPI: async (metrics) => {
        //        try {
        //            await this.api_admin.post("/api/metrics/collect-api", { metrics });
        //            console.log("✅ API Metrics enviados:", metrics.length);
        //        } catch (err) {
        //            console.error("❌ Error enviando API metrics:", err);
        //        }
        //    },
        //    debug: true,
        //    onUpdate: ({ type, count, total }) => {
        //        if (type === "api") {
        //            document.getElementById("apiCount").textContent = count;
        //            document.getElementById("apiTotal").textContent = total;
        //        }
        //    }
        //});
    }

    async init() {
        try {
            state.apiAdmin = this.api_admin;
            Chart.register(window["chartjs-plugin-annotation"]);

            await this.storage._init();

            const { user_name, user_rol, expira } = await this.loadUserCache();
            if (user_rol !== "Admin") {
                showGlobalAlert("🚫 No tienes permisos para acceder a este panel.", "danger", 5000);
                return;
            }
            this.renderUserSession(user_name, user_rol);
            await this.loadDashboard(); // carga contenido SPA
            this.startTokenTimer(expira);
            initRealtime();
            await this.refreshAll();
            this.initMenuActions();
            this.initByRole();
            this.showContentByRole(user_rol);
            this.initLogout();
            this.initAuditButtons();
        } catch (err) {
            console.error("❌ Error al inicializar el panel admin:", err);
            showGlobalAlert("Error inesperado al cargar el panel.", "danger");
        }
    }

    async loadUserCache() {
        const { username, rol, exp } = await this.api_admin.loadInfoAdmin();
        this.userCache = { user_name: username, user_rol: rol, expira: exp };
        return this.userCache;
    }

    async loadDashboard() {
        const container = document.getElementById("mainContent");
        if (!container) return;

        // Placeholder visual
        container.innerHTML = `
            <div class="skeleton-loader">
            <div class="skeleton-card"></div>
            <div class="skeleton-card"></div>
            <div class="skeleton-chart"></div>
            </div>
        `;

        try {
            const html = await this.api_admin.fetchDashboardHtml();
            container.innerHTML = html;
        } catch (err) {
            console.error("Error al cargar dashboard SPA:", err);
            showGlobalAlert("❌ Error al cargar el contenido del dashboard", "danger");
        }
    }

    async refreshAll() {
        const data = await fetchMetrics(state.role);
        state.lastUpdate = new Date().toLocaleString();
        document.getElementById("lastUpdate").textContent = state.lastUpdate;
        renderKPIs(data.metrics);
        renderCategoryChart(data.metrics);
        renderEndpointsTable(data.endpoints);
        renderErrors(data.errors);
    }

    renderUserSession(user_name, user_rol) {
        const userEl = document.getElementById("userName");
        if (userEl) userEl.textContent = `👋 ${user_name} (${user_rol})`;
        const dashEl = document.getElementById("dashboardContent");
        if (dashEl) dashEl.style.display = "block";
    }

    initByRole() {
        const el = document.getElementById("navPrincipal");
        if (!el) return;
        const elements = el.querySelectorAll("*");
        const allElementsArray = [el, ...elements];
        allElementsArray[0].className = "nav-item role-admin";
        allElementsArray[1]?.setAttribute("data-action", "iniciar-auditoria");
        if (allElementsArray[2]) allElementsArray[2].innerText = " Dashboard Admin";
    }

    initMenuActions() {
        const sections = {
            "sesiones": "#audit-session",
            "sesiones-auditadas": "#audit-table",
            "listado-usuarios": "#user-table",
            "overview": "#overview",
            "metrics-api": "#metricsApi",
            "metrics-endpoints": "#endpoints",
            "iniciar-auditoria": "#auditPanel",
        };

        document.body.addEventListener("click", async (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;
            e.preventDefault();

            const action = btn.dataset.action;
            this.toggleSections(sections, action);

            switch (action) {
                case "sesiones":
                    const { loadActiveSessions } = await import("../modules/sesiones.js");
                    await loadActiveSessions(this.api_admin);
                    break;
                case "sesiones-auditadas":
                    this.currentAuditPage = 1;
                    this.stopAutoRefreshApi(state.intervalAPI);
                    state.intervalAPI = null;
                    const { loadAuditLogs } = await import("../modules/auditoria.js");
                    await loadAuditLogs(this.currentAuditPage, this.api_admin);
                    break;
                //case "listado-usuarios":
                //    this.currentAuditPage = 1;
                //    this.stopAutoRefreshApi(state.intervalAPI);
                //    state.intervalAPI = null;
                //    const { loadItemUser } = await import("../modules/items.js");
                //    await loadItemUser(this.currentAuditPage, this.api_admin);
                //    break;
                case "overview":
                    this.stopAutoRefreshApi(state.intervalAPI);
                    state.intervalAPI = null;
                    await this.refreshAll();
                    break;
                case "metrics-api":
                    const chartElDuration = document.getElementById("durationChart");
                    if (!chartElDuration) break;
                    renderMetricsApi(chartElDuration);
                    state.intervalAPI = this.startAutoRefreshApi(chartElDuration);
                    break;
                case "metrics-endpoints":
                    state.intervalAPI = null;
                    const timeline = await this.api_admin.fetchTimeline("hour", 24);
                    if (timeline) {
                        const grouped = transformData(timeline);
                        renderChartByCategory(grouped);
                    }
                    break;
                case "iniciar-auditoria":
                    // aquí se activa panel auditoría
                    break;
                default:
                    console.warn("⚠️ Acción desconocida:", action);
            }
        });

        // =======================
        // Token Timer Listener
        // =======================
        document.addEventListener("startTokenTimer", ({ detail }) => {
            const { new_expiracion } = detail;
            this.resetProgressBar();
            this.startTokenTimer(new_expiracion);
        });
    }

    initLogout() {
        const btn = document.getElementById("logoutBtn");
        btn?.addEventListener("click", async e => {
            e.preventDefault();
            await this.api_admin.logout();
        });
    }

    startAutoRefreshApi(ctxElement, interval = 10000) {
        return setInterval(() => renderMetricsApi(ctxElement), interval);
    }

    stopAutoRefreshApi(id) {
        if (id) {
            clearInterval(id);
            console.log("⏹ Auto-refresh-Api detenido:", id);
        }
    }

    toggleSections(sections, activeKey) {
        Object.values(sections).forEach(sel => {
            if (!sel) return;
            const sec = document.querySelector(sel);
            if (sec) sec.style.display = "none";
        });

        const activeSel = sections[activeKey];
        if (activeSel) document.querySelector(activeSel).style.display = "block";
    }

    showContentByRole(rol) {
        if (!rol) return;
        const roleLower = rol.toLowerCase();

        document.querySelectorAll('[class*="role-"]').forEach(el => {
            const requiredRoles = [...el.classList]
                .filter(c => c.startsWith("role-"))
                .map(c => c.replace("role-", "").toLowerCase());

            el.style.display = requiredRoles.includes(roleLower) ? "" : "none";
        });
    }

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
                    this.tryRefreshToken();
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
    resetProgressBar() {
        const progressBar = document.getElementById("tokenProgress");
        if (progressBar) {
            progressBar.classList.remove("bg-danger", "bg-warning", "bg-success");
            progressBar.classList.add("bg-success");
        }
    }
    async tryRefreshToken() {
        try {
            const newToken = await this.api_admin.refreshToken();
            if (!newToken?.exp) throw new Error("Token inválido o incompleto");

            this.userCache.expira = newToken.exp;
            await this.storage.set("expira", newToken.exp);
            this.startTokenTimer(newToken.exp);
            showGlobalAlert("✅ Token renovado automáticamente", "success", 2000);
            await this.refreshVisibleSections();
        } catch (err) {
            console.error("❌ Error al refrescar token:", err);
            showGlobalAlert("⚠️ Sesión expirada. Redirigiendo al login...", "warning", 3000);
            setTimeout(() => location.replace("/?logout=true"), 3000);
        }
    }
    async refreshVisibleSections() {
        if (document.querySelector("#audit-table")?.offsetParent !== null)
            await loadAuditLogs(this.currentAuditPage, this.api_admin);
        else if (document.querySelector("#audit-session")?.offsetParent !== null)
            await loadActiveSessions(this.api_admin);
    }
    formatDateSantiago(expTimestamp) {
        return new Date(expTimestamp * 1000).toLocaleString("es-CL", {
            timeZone: "America/Santiago",
            hour12: false,
        });
    }
    formatRemaining(ms) {
        const totalSec = Math.floor(ms / 1000);
        const hours = Math.floor(totalSec / 3600);
        const minutes = Math.floor((totalSec % 3600) / 60);
        const seconds = totalSec % 60;
        return hours > 0 ? `${hours}h ${minutes}m ${seconds}s` : `${minutes}m ${seconds}s`;
    }
    initAuditButtons() {
        document.getElementById("startAuditBtn")?.addEventListener("click", () => {
            this.auditar.start();
            state.auditActive = true;
        });
        document.getElementById("stopAuditBtn")?.addEventListener("click", () => {
            this.auditar.stop();
            state.auditActive = false;
        });
    }
}


// =======================
// Inicialización automática
// =======================
document.addEventListener("DOMContentLoaded", () => {
    const spinner = document.getElementById("loadingSpinner");
    const dash = document.getElementById("dashboardContent");
    if (dash) dash.hidden = true;

    const fadeIn = () => {
        if (spinner) spinner.style.opacity = 0;
        setTimeout(() => {
            spinner?.remove();
            dash.hidden = false;
            dash.classList.add("fade-in");
        }, 300);
    };

    setTimeout(fadeIn, 500);
    new AdminDashboard().init();
});
