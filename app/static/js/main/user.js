// main/user.js
import { showAlert } from "../layout.js";
import { ApiUser } from "../api/ApiUser.js";
import { openChat } from "../modules/chatHandler.js";
import { handleError } from "../utils/errors.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js";
import { initUserPerformanceAudit } from "../utils/auditMetrics.js";
// =======================
// Configuración inicial
// =======================
const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");
const api_user = new ApiUser({ baseURL: API_BASE, storage });

let tokenTimerInterval = null;
let userCache = null;

// =======================
// Inicialización DOM
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    try {
        await storage._init(); // 👈 asegúrate que la DB está lista
        const { user_name, user_rol, expira } = await allKeys();
        initUserPerformanceAudit(user_name);
        if (!user_rol) {
            redirectToLogin("No hay token válido, redirigiendo...");
            return;
        }

        renderUserSession(user_name, user_rol);
        startTokenTimer(expira);
        document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
            e.preventDefault();
            await api_user.logout();
            e.stopPropagation();
        });
        setupUnloadLogout();
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

async function allKeys() {
    // esperar a que storage esté inicializado
    if (storage.ready) await storage.ready;
    if (userCache) return userCache;

    try {


        const response = await api_user.get("/api/auth/dashboard");

        // Intentar obtener desde backend
        const { username, rol, device_id, exp, jti } = response;
        userCache = {
            user_name: username,
            user_rol: rol,
            device: device_id,
            expira: exp,
            user_jti: jti
        };

        await storage.set("username", username);
        await storage.set("rol", rol);
        await storage.set("device_id", device_id);
        await storage.set("jti", jti);

        return userCache;
    } catch (err) {
        console.warn("⚠️ Dashboard no disponible, usando cache local...", err);

        const user_name = await storage.get("user_name") || "Desconocido";
        const user_rol = await storage.get("user_rol") || null;

        return (userCache = { user_name, user_rol });
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