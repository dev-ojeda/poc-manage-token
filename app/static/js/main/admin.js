import {
    showAlert
} from '../layout.js';
import {
    ApiAdmin
} from '../api/ApiAdmin.js';
import {
    IndexedDBStorage
} from '../adapters/IndexedDBStorage.js';
import {
    loadActiveSessions
} from '../modules/sesiones.js';
import {
    loadAuditLogs
} from '../modules/auditoria.js';
import {
    loadUsers
} from '../modules/usuarios.js';

import { MetricsStorage } from '../adapters/MetricsStorage.js';
// =======================
// Configuración inicial
// =======================
const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");
const metricsStorage = new MetricsStorage();
const api_admin = new ApiAdmin({
    baseURL: API_BASE,
    storage
});

let currentAuditPage = 1;
let tokenTimerInterval = null;
let userCache = null;
// --- Estado charts global para evitar "Canvas is already in use" ---
let inputChartInstance = null;
let presentationChartInstance = null;
// =======================
// Init App
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    try {
        await storage._init();
        await metricsStorage._init();
        // activa actualización automática
        const { user_rol, expira } = await loadUserCache();
        if (user_rol !== "Admin") {
            showAlert("🚫 No tienes permisos para acceder a este panel.", "danger", 5000);
            return;
        }
        initDashboard();
        initMenuActions();
        startTokenTimer(expira);
        initLogout();
        initCharts();
        attachClickMetrics();
        observePerformanceMetrics();

    } catch (err) {
        console.error("❌ Error al inicializar el panel admin:", err);
        showAlert("Error inesperado al cargar el panel.", "danger");
    }
});

// recarga cuando haya cambios

// =======================
// Load user cache
// =======================
async function loadUserCache() {
    if (storage.ready) await storage.ready;
    if (userCache) return userCache;

    try {
        const { username, rol, device_id, exp, jti } = await api_admin.get("/api/auth/admin/dashboard");
        userCache = { user_name: username, user_rol: rol, device: device_id, expira: exp, user_jti: jti };
        await Promise.all([
            storage.set("user_name", username),
            storage.set("user_rol", rol),
            storage.set("device_id", device_id),
            storage.set("jti", jti),
            storage.set("expira", exp)
        ]);
        return userCache;
    } catch {
        console.warn("⚠️ Dashboard no disponible, usando cache local...");
        const user_name = await storage.get("user_name") || "Desconocido";
        const user_rol = await storage.get("user_rol") || null;
        const expira = await storage.get("expira") || null;
        return (userCache = { user_name, user_rol, expira });
    }
}

function initDashboard() {
    try {
        const dashboard = document.querySelector("#dashboardContent");
        dashboard.style.display = "block";
        document.getElementById("userName").textContent = `Hola, ${userCache.user_name} (Admin)`;
        showContentByRole();
    } catch (err) {
        console.error("Error inicializando el dashboard:", err);
        showAlert("❌ Ocurrió un error al cargar el panel", "danger", 5000);
    } finally { }
}

function initMenuActions() {
    const sections = {
        "sesiones": "#audit-session",
        "sesiones-auditadas": "#audit-table",
        "listado-usuarios": "#user-table",
        "graficos": "#lighthouseSummary"
    };

    document.body.addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        e.preventDefault();

        const action = btn.dataset.action;
        toggleSections(sections, action);

        try {
            switch (action) {
                case "sesiones":
                    //await loadMockData()
                    await loadActiveSessions(api_admin);
                    await refreshMetricsUI(); // primer render
                    break;
                case "sesiones-auditadas":
                    currentAuditPage = 1;
                    //await loadMockData();
                    await loadAuditLogs(currentAuditPage, api_admin);
                    await refreshMetricsUI(); // primer render
                    break;
                case "listado-usuarios":
                    currentAuditPage = 1;
                    //await loadMockData();
                    await loadUsers(currentAuditPage, api_admin);
                    await refreshMetricsUI(); // primer render
                    break;
                case "graficos":
                    await refreshMetricsUI(); // primer render
                    break;
                default:
                    console.warn("⚠️ Acción desconocida:", action);
            }
        } catch (err) {
            showAlert(`❌ Error cargando sección: ${err.message}`, "danger");
        }
    });
}

function initLogout() {
    const btn = document.getElementById("logoutBtn");
    btn?.addEventListener("click", async e => {
        e.preventDefault();
        await api_admin.logout_admin();
    });
}
// =========================
// 1) Inicializar Charts
// =========================
// =======================
// Charts
// =======================
function initCharts() {
    const inputCanvas = document.getElementById("inputDelayChart");
    const presentationCanvas = document.getElementById("presentationDelayChart");

    if (inputCanvas) {
        if (inputChartInstance) inputChartInstance.destroy();
        inputChartInstance = new Chart(inputCanvas.getContext("2d"), {
            type: "bar",
            data: { labels: [], datasets: [{ label: "Input Delay (ms)", data: [], borderColor: "#007bff", borderWidth: 2, fill: false }] },
            options: { responsive: true, animation: false }
        });
    }

    if (presentationCanvas) {
        if (presentationChartInstance) presentationChartInstance.destroy();
        presentationChartInstance = new Chart(presentationCanvas.getContext("2d"), {
            type: "bar",
            data: { labels: [], datasets: [{ label: "Presentation Delay (ms)", data: [], borderColor: "#28a745", borderWidth: 2, fill: false }] },
            options: { responsive: true, animation: false }
        });
    }
}
// =======================
// Click + Input Metrics
// =======================
function attachClickMetrics() {
    document.querySelectorAll("button[data-action], a[data-action]").forEach(el => {
        el.addEventListener("click", () => {
            const t0 = performance.now();
            setTimeout(() => {
                const t1 = performance.now();
                const inputDelay = Math.round(t1 - t0);
                requestAnimationFrame(() => {
                    const t2 = performance.now();
                    const presentationDelay = Math.round(t2 - t1);

                    storeMetrics({ type: "inputDelay", value: inputDelay, action: el.dataset.action || el.id || el.tagName });
                    storeMetrics({ type: "presentationDelay", value: presentationDelay, action: el.dataset.action || el.id || el.tagName });
                });
            }, 0);
        });
    });
}
// =======================
// PerformanceObserver Metrics
// =======================
function observePerformanceMetrics() {
    if (!("PerformanceObserver" in window)) return;

    try {
        const lcpObs = new PerformanceObserver((list) => {
            const last = list.getEntries().slice(-1)[0];
            if (last) storeMetrics({ type: "LCP", value: Math.round(last.renderTime || last.loadTime) });
        });
        lcpObs.observe({ type: "largest-contentful-paint", buffered: true });

        let clsValue = 0;
        const clsObs = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                    storeMetrics({ type: "CLS", value: Number(clsValue.toFixed(3)) });
                }
            }
        });
        clsObs.observe({ type: "layout-shift", buffered: true });
    } catch (e) {
        console.warn("PerformanceObserver no disponible o restringido:", e);
    }
}
// =======================
// Store metrics
// =======================
async function storeMetrics(metric = {}) {
    if (!userCache) return;

    const enriched = {
        username: userCache.user_name,
        rol: userCache.user_rol,
        type: metric.type,
        value: metric.value,
        action: metric.action,
        ts: Date.now()
    };

    console.log(enriched);
    await metricsStorage.set(enriched);
}

// =======================
// Refresh Charts & Summary
// =======================
async function refreshMetricsUI(role = "User") {
    try {
        const metrics = await metricsStorage.getByRole(role);

        const labels = metrics.map(m => formatDateIso(m.ts));
        const fidVals = metrics.filter(m => m.type === "inputDelay").map(m => m.value);
        const presVals = metrics.filter(m => m.type === "presentationDelay").map(m => m.value);
        const lcpVals = metrics.filter(m => m.type === "LCP").map(m => m.value);
        const clsVals = metrics.filter(m => m.type === "CLS").map(m => m.value);

        if (inputChartInstance) {
            inputChartInstance.data.labels = labels;
            inputChartInstance.data.datasets[0].data = fidVals;
            inputChartInstance.update();
        }

        if (presentationChartInstance) {
            presentationChartInstance.data.labels = labels;
            presentationChartInstance.data.datasets[0].data = presVals;
            presentationChartInstance.update();
        }

        const avg = arr => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : null;
        const avgFid = avg(fidVals);
        const avgLcp = avg(lcpVals);
        const avgCls = clsVals.length ? Number((clsVals.reduce((a, b) => a + b, 0) / clsVals.length).toFixed(3)) : null;

        if (avgFid !== null) document.getElementById("fidAvg").textContent = avgFid;
        if (avgLcp !== null) document.getElementById("lcpAvg").textContent = avgLcp;
        if (avgCls !== null) document.getElementById("clsAvg").textContent = avgCls;

        const statusEl = document.getElementById("perfStatus");
        if (statusEl) {
            const okFid = avgFid !== null ? avgFid < 100 : true;
            const okLcp = avgLcp !== null ? avgLcp < 2500 : true;
            const okCls = avgCls !== null ? avgCls < 0.1 : true;

            let status = "Óptimo", cls = "text-success";
            if (!(okFid && okLcp && okCls)) {
                status = (okFid || okLcp || okCls) ? "Medio" : "Crítico";
                cls = status === "Medio" ? "text-warning" : "text-danger";
            }
            statusEl.textContent = status;
            statusEl.className = cls;
        }
    } catch (err) {
        console.error("Error refrescando métricas:", err);
    }
}
// =======================
// Export CSV, Dashboard, Logout, Roles, Token Timer
// =======================
// =======================
// Helpers UI
// =======================
function toggleSections(sections, activeKey) {
    Object.values(sections).forEach(sel => {
        if (!sel) return;
        const sec = document.querySelector(sel);
        if (sec) sec.style.display = "none";
    });

    const activeSel = sections[activeKey];
    if (activeSel) document.querySelector(activeSel).style.display = "block";
}

function showContentByRole() {

    const roles = String(userCache.user_rol).toLowerCase();
    document.querySelectorAll('[class*="role-"]').forEach(el => {
        const requiredRoles = [...el.classList]
            .filter(c => c.startsWith("role-"))
            .map(c => c.replace("role-", ""));
        el.style.display = requiredRoles.some(r => roles.includes(r)) ? "" : "none";
    });
}

function startTokenTimer(expTimestamp) {
    const timerElement = document.getElementById("tokenTimer");
    if (!timerElement || !expTimestamp) return;

    clearInterval(tokenTimerInterval);

    tokenTimerInterval = setInterval(async () => {
        const remaining = expTimestamp * 1000 - Date.now();

        if (remaining <= 0) {
            timerElement.textContent = "⏱ Token expirado";
            timerElement.classList.replace("text-success", "text-danger");
            clearInterval(tokenTimerInterval);
            await tryRefreshToken();
            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        timerElement.textContent = `⏱ Expira en ${minutes}:${seconds.toString().padStart(2, "0")}`;
    }, 1000);
}

async function tryRefreshToken() {
    try {
        const newToken = await api_admin.refreshToken();
        const exp = newToken.exp;
        userCache.expira = exp;
        await storage.set("expira", exp);
        startTokenTimer(exp);
        showAlert("✅ Token renovado automáticamente", "success", 3000);

        // refrescar datos si estás en dashboard activo
        if (document.querySelector("#audit-table").style.display !== "none") {
            await loadAuditLogs(currentAuditPage, api_admin);
        }
        if (document.querySelector("#audit-session").style.display !== "none") {
            await loadActiveSessions(api_admin);
        }
    } catch (err) {
        console.error("❌ Error al refrescar token:", err);
        showAlert("❌ No se pudo renovar token, por favor relogin", "danger");
    }
}

// =======================
// Helpers
// =======================
function formatDateIso(ts) {
    const date = new Date(ts);
    const pad = n => String(n).padStart(2, "0");
    return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

document.getElementById("roleSelector")?.addEventListener("change", e => refreshMetricsUI(e.target.value));
metricsStorage.subscribe(() => {
    const role = document.getElementById("roleSelector")?.value || "User";
    refreshMetricsUI(role);
});
