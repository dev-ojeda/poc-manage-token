// roles/admin
import {
    showGlobalAlert
} from "../layout.js";
import { fetchMetrics } from '../utils/api.js';
import { state } from '../utils/states.js';
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
import {
    initRealtime,
    renderCategoryChart,
    renderMetricsApi,
    renderChartByCategory
} from '../utils/render_chat.js';
import {
    renderKPIs,
    renderEndpointsTable,
    renderErrors
} from '../utils/ui.js';
//import { MetricsStorage } from '../adapters/MetricsStorage.js';
import { initPerformanceAudit } from '../utils/audit.js';
import { transformData } from '../utils/helper.js';

const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");
//const metricsStorage = new MetricsStorage();
const api_admin = new ApiAdmin({
    baseURL: API_BASE,
    storage
});
// ==============================
// Instanciar auditoría
// ==============================
const auditar = initPerformanceAudit({
    enableHooks: false,       // NO inicia automáticamente
    //sendToBackendWebVitals: async (metrics) => {
    //    try {
    //        await api_admin.post('/api/metrics/collect-web-vitals', { metrics });
    //        console.log("✅ Web Vitals enviados:", metrics.length);
    //    } catch (err) {
    //        console.error("❌ Error enviando Web Vitals:", err);
    //    }
    //},
    sendToBackendAPI: async (metrics) => {
        try {
            await api_admin.post('/api/metrics/collect-api', { metrics });
            console.log("✅ API Metrics enviados:", metrics.length);
        } catch (err) {
            console.error("❌ Error enviando API metrics:", err);
        }
    },
    debug: true,
    onUpdate: ({ type, count, total }) => {
        //if (type === "webVitals") {
        //    document.getElementById("webVitalsCount").textContent = count;
        //    document.getElementById("webVitalsTotal").textContent = total;
        //}
        if (type === "api") {
            document.getElementById("apiCount").textContent = count;
            document.getElementById("apiTotal").textContent = total;
        }
    }

});

// Endpoint summary

let currentAuditPage = 1;
let tokenTimerInterval = null;
let userCache = null;
// =======================
// Init App
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    try {
        state.apiAdmin = api_admin;
        Chart.register(window['chartjs-plugin-annotation']);
        await storage._init();
        //await metricsStorage._init();
        // activa actualización automática
        const { user_rol, expira } = await loadUserCache();
        if (user_rol !== "Admin") {
            showGlobalAlert("🚫 No tienes permisos para acceder a este panel.", "danger", 5000);
            return;
        }
        initRealtime();
        await refreshAll();
        initDashboard();
        initMenuActions();
        startTokenTimer(expira);
        initLogout();
    } catch (err) {
        console.error("❌ Error al inicializar el panel admin:", err);
        showGlobalAlert("Error inesperado al cargar el panel.", "danger");
    }
});

/**
* Carga los datos necesarios del usuario
* @returns
*/
async function loadUserCache() {
    if (storage.ready) await storage.ready;
    if (userCache) return userCache;
    try {
        const { username, rol, device_id, exp, jti } = await api_admin.loadInfoAdmin();
        userCache = { user_name: username, user_rol: rol, device: device_id, expira: exp, user_jti: jti };
        await Promise.all([
            storage.set("username", username),
            storage.set("rol", rol),
            storage.set("device_id", device_id),
            storage.set("jti", jti),
            storage.set("exp", exp)
        ]);
        return userCache;
    } catch {
        console.warn("⚠️ Dashboard no disponible, usando cache local...");
        const user_name = await storage.get("username") || "Desconocido";
        const user_rol = await storage.get("rol") || null;
        const expira = await storage.get("exp") || null;
        return (userCache = { user_name, user_rol, expira });
    }
}
async function refreshAll() {
    const data = await fetchMetrics(state.role);
    state.lastUpdate = new Date().toLocaleString();
    document.getElementById('lastUpdate').textContent = state.lastUpdate;
    renderKPIs(data.metrics);
    renderCategoryChart(data.metrics);
    renderEndpointsTable(data.endpoints);
    renderErrors(data.errors);
}
/** Inicia el loyaout para el usuario*/
function initDashboard() {
    try {
        const dashboard = document.querySelector("#dashboardContent");
        if (!dashboard) return;
        dashboard.style.display = "block";
        document.getElementById("userName").textContent = `Hola, ${userCache.user_name} (${userCache.user_rol})`;
        showContentByRole();
        initByRole();
    } catch (err) {
        console.error("Error inicializando el dashboard:", err);
        showGlobalAlert("❌ Ocurrió un error al cargar el panel", "danger", 5000);
    }
}

function initByRole() {
    const el = document.getElementById('navPrincipal');
    const elements = el.querySelectorAll('*'); // NodeList de elementos descendientes (no incluye el <li> itself)
    const allElementsArray = [el, ...elements]; // incluye el <li> como primer elemento
    allElementsArray[0].className = "nav-item role-admin";
    allElementsArray[1].setAttribute("data-action", "iniciar-auditoria");
    allElementsArray[2].innerText = "";
    allElementsArray[2].innerText = "Dashboard Admin";
}

/**
* Menu del sidebar con las acciones
*/
function initMenuActions() {
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
        toggleSections(sections, action);
        switch (action) {
            case "sesiones":
                await loadActiveSessions(api_admin);
                break;
            case "sesiones-auditadas":
                currentAuditPage = 1;
                stopAutoRefreshApi(state.intervalAPI);
                state.intervalAPI = null;
                await loadAuditLogs(currentAuditPage, api_admin);
                break;
            case "listado-usuarios":
                currentAuditPage = 1;
                stopAutoRefreshApi(state.intervalAPI);
                state.intervalAPI = null;
                await loadUsers(currentAuditPage, api_admin);
                break;
            case "overview":
                stopAutoRefreshApi(state.intervalAPI);
                state.intervalAPI = null;
                await refreshAll();
                break;
            case "metrics-api":
                const chartElDuration = document.getElementById("durationChart");
                if (!chartElDuration) break;
                renderMetricsApi(chartElDuration);
                state.intervalAPI = startAutoRefreshApi(chartElDuration);
                break;
            case "iniciar-auditoria":
                break;
            case "metrics-endpoints":
                state.intervalAPI = null;
                const timeline = await api_admin.fetchTimeline("hour", 24);
                if (timeline) {
                    const grouped = transformData(timeline);
                    renderChartByCategory(grouped);
                }
                break;
            default:
                console.warn("⚠️ Acción desconocida:", action);
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
function startAutoRefreshApi(ctxElement, interval = 10000) {
    return setInterval(() => renderMetricsApi(ctxElement), interval);
}

function stopAutoRefreshApi(id) {
    if (id) {
        clearInterval(id);
        console.log("⏹ Auto-refresh-Api detenido:", id);
    }
}



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
        const requiredRoles = [...el.classList].filter(c => c.startsWith("role-")).map(c => c.replace("role-", ""));
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
        showGlobalAlert("✅ Token renovado automáticamente", "success", 3000);

        // refrescar datos si estás en dashboard activo
        if (document.querySelector("#audit-table").style.display !== "none") {
            await loadAuditLogs(currentAuditPage, api_admin);
        }
        if (document.querySelector("#audit-session").style.display !== "none") {
            await loadActiveSessions(api_admin);
        }
    } catch (err) {
        console.error("❌ Error al refrescar token:", err);
        showGlobalAlert("❌ No se pudo renovar token, por favor relogin", "danger");
    }
}

function formatDateIso(ts) {
    const date = new Date(ts);
    const pad = n => String(n).padStart(2, "0");
    return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

// Botones
document.getElementById("startAuditBtn").addEventListener("click", () => {
    auditar.start();
    state.auditActive = true;
});
document.getElementById("stopAuditBtn").addEventListener("click", () => {
    auditar.stop();
    state.auditActive = false;
});