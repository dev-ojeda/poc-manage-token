// js/layout.js
import { clearSession } from "../js/utils/errors.js";
import { IndexedDBStorage } from "../js/adapters/IndexedDBStorage.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { ApiUser } from "../js/api/ApiUser.js";

/* ================= CONFIG ================= */
const API_BASE =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) ||
    globalThis.API_URL ||
    "https://localhost:5000";

const storage = new IndexedDBStorage("AuthDB", "tokens");
export const GLOBAL_DEBUG = localStorage.getItem("debugMode") === "true";
let redirecting = false;

/* ================= SERVICES ================= */
const api_admin = new ApiAdmin({ baseURL: API_BASE, storage, debugEnabled: GLOBAL_DEBUG });
const api_user = new ApiUser({ baseURL: API_BASE, storage, debugEnabled: GLOBAL_DEBUG });
globalThis.AppServices = { api_admin, api_user, storage };

/* ================= ENTRYPOINT ================= */
document.addEventListener("DOMContentLoaded", async () => {
    try {
        initSidebarToggle();
        await handleUrlAlerts();
        initGlobalEvents();
        initDebugPanel();
        initDebugConsole();
        initErrorCapture();
        document.dispatchEvent(new Event("layout:ready"));
    } catch (err) {
        console.error("Layout initialization failed:", err);
        showGlobalAlert("Error inicializando interfaz", "danger");
    }
});

/* ================= ALERTS ================= */
async function handleUrlAlerts() {
    const params = new URLSearchParams(globalThis.location.search);
    const alerts = {
        logout: { msg: "⚠️ Sesión expirada. Iniciá sesión nuevamente.", type: "warning", clear: true },
        unauthorized: { msg: "🚫 Acceso no autorizado. Iniciá sesión.", type: "danger" },
        untoken: { msg: "🚫 Token inválido o ausente.", type: "danger" },
    };

    for (const [key, { msg, type, clear }] of Object.entries(alerts)) {
        if (params.get(key) === "true") {
            showGlobalAlert(msg, type, 6000);
            if (clear) await clearSession();
            if (!globalThis._historyReplaced && globalThis.isSecureContext) {
                globalThis._historyReplaced = true;
                globalThis.history.replaceState({}, document.title, globalThis.location.pathname);
            }
        }
    }
}

/* ================= SIDEBAR ================= */
function initSidebarToggle() {
    const sidebar = document.getElementById("sidebar");
    const main = document.getElementById("mainContent");
    const toggle = document.getElementById("sidebarToggle");
    if (!sidebar || !main || !toggle) return;

    const toggleSidebar = () => {
        sidebar.classList.toggle("collapsed");
        sidebar.classList.toggle("show");
        main.classList.toggle("expanded");
    };

    toggle.addEventListener("click", toggleSidebar);
    toggle.addEventListener("keydown", (e) => {
        if (["Enter", " "].includes(e.key)) {
            e.preventDefault();
            toggleSidebar();
        }
    });

    const resizeHandler = () => {
        const isMobile = globalThis.innerWidth < 992;
        sidebar.classList.toggle("collapsed", isMobile);
        main.classList.toggle("expanded", isMobile);
    };

    globalThis.addEventListener("resize", resizeHandler);
    resizeHandler();
}

/* ================= ALERT UI ================= */
export function showGlobalAlert(message, type = "info", timeout = 4000) {
    const container = document.getElementById("globalAlerts") || document.getElementById("alertContainer");
    if (!container) return console.warn("⚠️ No se encontró contenedor de alertas.");

    const el = document.createElement("div");
    el.className = `alert alert-${type} alert-dismissible fade show shadow mt-2`;
    el.innerHTML = `<div>${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;

    container.appendChild(el);
    if (timeout) setTimeout(() => el.classList.remove("show"), timeout - 300);
    if (timeout) setTimeout(() => el.remove(), timeout);
}

/* ================= GLOBAL EVENTS ================= */
function initGlobalEvents() {
    const logoutBtn = document.getElementById("logoutBtn");

    const logout = async () => {
        if (redirecting) return;
        redirecting = true;
        await clearSession();
        showGlobalAlert("👋 Sesión finalizada.", "info");
        setTimeout(() => (globalThis.location.href = "/"), 1200);
    };

    if (logoutBtn) {
        logoutBtn.addEventListener("click", logout);
        logoutBtn.addEventListener("keydown", (e) => {
            if (["Enter", " "].includes(e.key)) {
                e.preventDefault();
                logout();
            }
        });
    }

    document.addEventListener("debug:log", (e) => {
        const { label, args, level = "info" } = e.detail;
        const colors = { info: "#0dcaf0", success: "#28a745", warn: "#ffc107", error: "#dc3545", debug: "#6f42c1" };
        console.log(`%c[${level.toUpperCase()}] ${label}`, `color:${colors[level] || "#aaa"}`, ...args);
    });

    document.addEventListener("session:change", (e) => {
        const { loggedIn, role } = e.detail;
        const msg = loggedIn ? `✅ Sesión activa (${role.toUpperCase()})` : "🚪 Sesión cerrada.";
        showGlobalAlert(msg, loggedIn ? "success" : "warning");
    });
}

/* ================= DEBUG MODE ================= */
export function initDebugPanel() {
    const toggle = document.getElementById("debugToggle");
    if (!toggle) return;

    const state = localStorage.getItem("debugMode") === "true";
    toggle.checked = state;
    setGlobalDebug(state);

    toggle.addEventListener("change", (e) => {
        const enabled = e.target.checked;
        localStorage.setItem("debugMode", enabled);
        setGlobalDebug(enabled);
    });
}

function setGlobalDebug(enabled) {
    api_user.debugEnabled = enabled;
    api_admin.debugEnabled = enabled;
    if (globalThis.AuthAppInstance) globalThis.AuthAppInstance.debugEnabled = enabled;
    console.info(`%c🪲 Debug ${enabled ? "ON" : "OFF"}`, `color:${enabled ? "#00e676" : "#ff5252"}; font-weight:bold;`);
}

/* ================= DEBUG CONSOLE ================= */
function initDebugConsole() {
    const toggle = document.getElementById("debugToggle");
    const consoleEl = document.getElementById("debugConsole");
    const output = document.getElementById("debugOutput");
    const clearBtn = document.getElementById("clearDebug");
    if (!toggle || !consoleEl) return;

    const updateVisibility = () => consoleEl.classList.toggle("hidden", !toggle.checked);
    toggle.addEventListener("change", updateVisibility);
    clearBtn?.addEventListener("click", () => (output.innerHTML = ""));

    document.addEventListener("debug:log", (e) => {
        const { label, args } = e.detail;
        const time = new Date().toLocaleTimeString();
        const line = document.createElement("div");
        line.className = "debug-log";
        line.innerHTML = `<time>[${time}]</time> ${label}: ${args.map(a => JSON.stringify(a, null, 2)).join(" ")}`;
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    });
}

/* ================= GLOBAL ERROR HANDLER ================= */
function initErrorCapture() {
    globalThis.addEventListener("error", (e) => {
        console.error("Error global:", e.message);
        showGlobalAlert("⚠️ Error inesperado", "danger");
    });

    globalThis.addEventListener("unhandledrejection", (e) => {
        console.error("Rechazo no manejado:", e.reason);
        showGlobalAlert("⚠️ Error en operación asíncrona", "danger");
    });
}
