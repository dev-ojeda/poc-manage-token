// main/user.js
import { showAlert } from "../layout.js";
import { ApiUser } from "../api/ApiUser.js";
import { openChat } from "../modules/chatHandler.js";
import { handleError } from "../utils/errors.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js";
import { MetricsStorage } from '../adapters/MetricsStorage.js';
import { loadItemUser } from '../modules/items.js';
// =======================
// Configuración inicial
// =======================
const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");
const metricsStorage = new MetricsStorage();
const api_user = new ApiUser({ baseURL: API_BASE, storage });

let tokenTimerInterval = null;
let userCache = null;
let currentItemPage = 1;
// =======================
// Inicialización DOM
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    try {
        await storage._init(); // 👈 asegúrate que la DB está lista
        await metricsStorage._init();
        const { user_name, user_rol, expira } = await loadUserCache();
        if (!user_rol) {
            redirectToLogin("No hay token válido, redirigiendo...");
            return;
        }
        initMenuActions();
        renderUserSession(user_name, user_rol);
        startTokenTimer(expira);
        document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
            e.preventDefault();
            await api_user.logout();
            e.stopPropagation();
        });
        setupUnloadLogout();
        initPerformanceAudit();
        attachClickMetricsCategory();
        openChat(user_rol);

    } catch (err) {
        handleError(err);
        redirectToLogin("Error al inicializar sesión. Redirigiendo...");
    }
});

// =======================
// Token Timer Listener
// =======================
document.addEventListener("startTokenTimer", ({ detail }) => {
    const { new_expiracion } = detail;
    resetProgressBar();
    startTokenTimer(new_expiracion);
});

// =======================
// Funciones principales
// =======================

async function loadUserCache() {
    // esperar a que storage esté inicializado
    if (storage.ready) await storage.ready;
    if (userCache) return userCache;

    try {


        const { username, rol, device_id, exp, jti } = await api_user.get("/api/auth/dashboard");

        userCache = {
            user_name: username,
            user_rol: rol,
            device: device_id,
            expira: exp,
            user_jti: jti
        };
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

function renderUserSession(user_name, user_rol) {
    document.getElementById("userName").textContent = `👋 ${user_name} (${user_rol})`;
    showContentByRole(user_rol);

    const dashboardContent = document.getElementById("dashboardContent");
    if (dashboardContent) dashboardContent.style.display = "block";
}

function setupUnloadLogout() {
    window.addEventListener("beforeunload", () => api_user.logout("close"));
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
function redirectToLogin(msg) {
    if (msg) showAlert(msg, "danger", 5000);
    window.location.href = "/";
}

// =======================
// UI Helpers
// =======================
function resetProgressBar() {
    const progressBar = document.getElementById("tokenProgress");
    if (progressBar) {
        progressBar.classList.remove("bg-danger", "bg-warning", "bg-success");
        progressBar.classList.add("bg-success");
    }
}

function showContentByRole(rol) {
    if (!rol) return;
    const roleLower = rol.toLowerCase();

    document.querySelectorAll('[class*="role-"]').forEach(el => {
        const requiredRoles = [...el.classList]
            .filter(c => c.startsWith("role-"))
            .map(c => c.replace("role-", "").toLowerCase());

        el.style.display = requiredRoles.includes(roleLower) ? "" : "none";
    });
}

// =======================
// Token Timer
// =======================
function startTokenTimer(expTimestamp) {
    const timerElement = document.getElementById("tokenTimer");
    const progressBar = document.getElementById("tokenProgress");
    const fechaActual = document.getElementById("fechaCountry");

    if (!timerElement || !expTimestamp || !progressBar) return;

    clearInterval(tokenTimerInterval);

    fechaActual.innerText = formatDateSantiago(expTimestamp);
    const totalDuration = expTimestamp * 1000 - Date.now();
    let refreshTriggered = false;

    tokenTimerInterval = setInterval(() => {
        const remaining = expTimestamp * 1000 - Date.now();
        const percentage = Math.max(0, Math.floor((remaining / totalDuration) * 100));

        updateProgressBar(progressBar, percentage);
        timerElement.textContent = `⏱ Expira en ${formatRemaining(remaining)}`;
        timerElement.classList.add("text-success");

        if (!refreshTriggered && remaining <= 30000) {
            refreshTriggered = true;
            showAlert("♻️ Refrescando sesión automáticamente...", "info", 3000);
            timerElement.textContent = "♻️ Renovando token...";
            clearInterval(tokenTimerInterval);
            api_user.tryRefreshToken();
        }

        if (remaining <= 0) {
            timerElement.textContent = "⏱ Token expirado";
            timerElement.classList.replace("text-success", "text-danger");
            progressBar.classList.remove("bg-success", "bg-warning");
            progressBar.classList.add("bg-danger");
            clearInterval(tokenTimerInterval);
        }
    }, 1000);
}

function updateProgressBar(progressBar, percentage) {
    progressBar.style.width = `${percentage}%`;

    progressBar.classList.remove("bg-success", "bg-warning", "bg-danger");
    if (percentage <= 29) progressBar.classList.add("bg-danger");
    else if (percentage <= 49) progressBar.classList.add("bg-warning");
    else progressBar.classList.add("bg-success");
}

// =======================
// Utilidades
// =======================
function formatDateSantiago(expTimestamp) {
    return new Date(expTimestamp * 1000).toLocaleString("es-CL", {
        timeZone: "America/Santiago",
        hour12: false,
    });
}

function formatRemaining(ms) {
    const totalSec = Math.floor(ms / 1000);
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;
    return hours > 0 ? `${hours}h ${minutes}m ${seconds}s` : `${minutes}m ${seconds}s`;
}


async function storeMetrics(metric = {}) {
    if (!userCache) return;

    const enriched = {
        username: userCache.user_name,
        rol: userCache.user_rol,
        type: metric.type,
        value: metric.value,
        action: metric.action,
        category: metric.category || "other",   // 👈 Aquí la clave
        ts: Date.now()
    };

    await metricsStorage.set(enriched);
}

function attachClickMetricsCategory() {
    // Clicks en cualquier control interactivo
    document.body.addEventListener("click", e => {
        const el = e.target.closest("button, a, input, select, textarea");
        if (el) measureInteraction(el, "click");
    });

    // Cambios en inputs/select/textarea
    document.body.addEventListener("change", e => {
        const el = e.target.closest("input, select, textarea");
        if (el) measureInteraction(el, "change");
    });

    // Teclas en inputs/textarea
    document.body.addEventListener("keydown", e => {
        const el = e.target.closest("input, textarea");
        if (el) measureInteraction(el, `keydown:${e.key}`);
    });

    document.body.addEventListener("keyup", e => {
        const el = e.target.closest("input, textarea");
        if (el) measureInteraction(el, `keyup:${e.key}`);
    });
}
function getElementDescriptor(el, interactionType) {
    const tag = el.tagName.toLowerCase();
    const id = el.id ? `#${el.id}` : "";
    const name = el.name ? `[name=${el.name}]` : "";
    const type = el.type ? `[type=${el.type}]` : "";
    const datasetAction = el.dataset.action ? `[data-action=${el.dataset.action}]` : "";

    return `${tag}${id}${name}${type}${datasetAction}-${interactionType}`;
}
function measureInteraction(el, interactionType) {
    const t0 = performance.now();
    setTimeout(() => {
        const t1 = performance.now();
        const inputDelay = Math.round(t1 - t0);

        requestAnimationFrame(() => {
            const t2 = performance.now();
            const presentationDelay = Math.round(t2 - t1);

            const descriptor = getElementDescriptor(el, interactionType);

            // 🔹 Categoría dinámica
            let category = "other";
            if (["button", "a"].includes(el.tagName.toLowerCase())) category = "button";
            else if (["input", "select", "textarea"].includes(el.tagName.toLowerCase())) category = "input";

            storeMetrics({
                type: "inputDelay",
                value: inputDelay,
                action: descriptor,
                category
            });

            storeMetrics({
                type: "presentationDelay",
                value: presentationDelay,
                action: descriptor,
                category
            });
        });
    }, 0);
}
function initPerformanceAudit() {
    class PerformanceAudit {
        constructor(sendAuditLogFn) {
            this.sendAuditLog = sendAuditLogFn;
            this.observers = [];
        }

        init() {
            this.observeLCP();
            this.observeFID();
        }

        observeLCP() {
            const lcpObs = new PerformanceObserver((list) => {
                const last = list.getEntries().slice(-1)[0];
                if (last) this.sendAuditLog({ metric: "LCP", value: last.startTime, element: last.element?.tagName || null, ts: Date.now() });
            });
            lcpObs.observe({ type: "largest-contentful-paint", buffered: true });
            this.observers.push(lcpObs);
        }

        observeFID() {
            const fidObs = new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    this.sendAuditLog({ metric: "FID", inputDelay: entry.processingStart - entry.startTime, processingDuration: entry.duration, target: entry.target?.tagName || null, ts: Date.now() });
                });
            });
            fidObs.observe({ type: "first-input", buffered: true });
            this.observers.push(fidObs);
        }
        observeCLS() {
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
            this.observers.push(clsObs);
        }

        disconnect() { this.observers.forEach(o => o.disconnect()); this.observers = []; }
    }

    const audit = new PerformanceAudit(async (data) => {
        await metricsStorage.set({
            username: userCache.user_name,
            rol: userCache.user_rol,
            type: data.metric,
            value: data.inputDelay || data.value || 0,
            action: data.target || data.element || "unknown",
            category: "performance",
            ts: Date.now()
        });
    });

    audit.init();
}
function initMenuActions() {
    const sections = {
        "item-usuario": "#userItemsSection",
    };
    document.body.addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        e.preventDefault();
        const action = btn.dataset.action;
        toggleSections(sections, action);
        try {
            switch (action) {
                case "item-usuario":
                    currentItemPage = 1;
                    await loadItemUser(currentItemPage,api_user);
                    break;
                default:
                    console.warn("⚠️ Acción desconocida:", action);
            }
        } catch (err) {
            showAlert(`❌ Error acción: ${err.message}`, "danger");
        }
    });

    document.getElementById("addItemBtn")?.addEventListener("click", async () => {
        const name = document.getElementById("itemNameInput").value;
        const description = document.getElementById("itemDescInput").value;
        if (name && description) {
            await api_user.createItem({ name, description });
            await loadItemUser(currentItemPage, api_user);
        } 
    });
}

