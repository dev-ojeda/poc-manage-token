// main/user.js
import { showAlert } from "../layout.js";
import { ApiUser } from "../api/ApiUser.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { openChat } from "../modules/chatHandler.js";
import { handleError } from "../utils/errors.js";

const api_user = new ApiUser({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost:5000",
    storage: new LocalStorageAdapter()
});
// Guardamos última IP y UA por device_id
let tokenTimerInterval = null;
// Inicializar al cargar DOM
document.addEventListener("DOMContentLoaded", async () => {
    const user_rol = api_user.userRol;
    const user_name = api_user.userName;
    const dashboardContent = document.getElementById("dashboardContent");
    const expiracion = api_user.tokenExp;
    if (!user_rol) {
        console.warn("No hay token válido, redirigiendo...");
        window.location.href = "/";
        return;
    }
    // Mostrar nombre y rol
    document.getElementById("userName").textContent = `👋 ${user_name} (${user_rol})`;

    // Mostrar secciones según rol
    showContentByRole(user_rol);

    // Mostrar dashboard y comenzar temporizador
    dashboardContent.style.display = "block";
    startTokenTimer(expiracion);
    openChat(user_rol);

    // Eventos generales
    document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
        e.preventDefault();
        await api_user.logout("logout"); 
        e.stopPropagation();
    });

});

function showContentByRole(rol) {
    // Aquí podrías expandir esto para ocultar/mostrar cards, secciones, etc.
    if (rol !== "Admin") {
        const adminSection = document.querySelector(".admin-only");
        if (adminSection) adminSection.style.display = "none";
    }
    applyRoleVisibility(rol);
    // Agrega más roles si es necesario
}
async function tryRefreshToken() {
    const refreshToken = await api_user.getRefreshToken();
    if (!refreshToken) {
        showAlert("⚠️ No hay refresh token guardado.", "warning", 4000);
        await api_user.logout("expiration");
        return;
    }

    try {
        const response = await fetch("/api/auth/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                refresh_token: refreshToken,
                device_id: api_user.getDeviceId(),  // <-- paréntesis acá
                user_agent: api_user.getBrowserInfo()
            })
        });
        const data = await response.json();
        if (response.ok) {
            api_user.storage.set("access_token", data.access_token);
            api_user.storage.set("refresh_token", data.refresh_token);
            api_user.storage.set("device_id", data.device_id);
            api_user.storage.set("username", data.username);
            api_user.storage.set("rol", data.rol);
            api_user.storage.set("exp", data.exp);
            showAlert("✅ Token refrescado", "success", 4000);
            startTokenTimer(data.exp);
        } else {
            throw new Error(`Error ${data.msg} ${data.code}`);
            await api_user.logout("intentos");
        }
    } catch (err) {
        handleError(err)
        await api_user.logout("intentos");
    }
}

function startTokenTimer(expTimestamp) {
    const timerElement = document.getElementById("tokenTimer");
    if (!timerElement || !expTimestamp) return;
    clearInterval(tokenTimerInterval);  // ⚠️ Evita múltiples intervalos

    tokenTimerInterval = setInterval(() => {
        const remaining = expTimestamp * 1000 - Date.now();
        if (remaining <= 0) {
            timerElement.textContent = "⏱ Token expirado";
            timerElement.classList.replace("text-success", "text-danger");
            clearInterval(tokenTimerInterval);
            tryRefreshToken(); // ⚙️ Refresh automático
            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        timerElement.textContent = `⏱ Expira en ${minutes}:${seconds.toString().padStart(2, "0")}`;
    }, 1000);
}
function applyRoleVisibility(rol) {
    if (!rol) return false;
    const userRole = rol.toLowerCase();
    const elements = document.querySelectorAll('[class*="role-"]');

    elements.forEach(el => {
        const requiredRoles = Array.from(el.classList)
            .filter(cls => cls.startsWith("role-"))
            .map(cls => cls.replace("role-", "").toLowerCase());

        const hasAccess = requiredRoles.includes(userRole);
        el.style.display = hasAccess ? "" : "none";
    });
}