import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { loadActiveSessions } from "../modules/sessiones.js";

const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});
let tokenTimerInterval = null;
document.addEventListener("DOMContentLoaded", async () => {
    const user_rol = api_admin.userRol;
    const user_name = api_admin.userName;
    const dashboardContent = document.getElementById("dashboardContent");
    const expiracion = api_admin.tokenExp;
    if (!user_rol) {
        console.warn("No hay token válido, redirigiendo...");
        window.location.href = "/";
        return;
    }
    // Mostrar nombre y rol
    document.getElementById("userName").textContent = `👋 ${user_name} (${user_rol})`;
    showContentByRole(user_rol)
    // Mostrar dashboard y comenzar temporizador
    dashboardContent.style.display = "block";
    startTokenTimer(expiracion);
    document.querySelectorAll(".nav-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const action = e.currentTarget.dataset.action;

            switch (action) {
                case "sesiones":
                    console.log("Abrir módulo de sesiones activas");
                    // Aquí puedes llamar tu función para cargar datos
                    document.querySelector(".admin-only-sessiones").style.display = "block";
                    await loadActiveSessions();
                    break;

                case "sesiones-auditadas":
                    console.log("Abrir módulo de sesiones auditadas");
                    break;

                case "tokens":
                    console.log("Abrir módulo de tokens");
                    break;

                default:
                    console.warn("Acción no reconocida:", action);
            }
        });
    });
    document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
        e.preventDefault();
        await api_admin.logout_admin();
        e.stopPropagation();
    });
});

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
            //tryRefreshToken(); // ⚙️ Refresh automático
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

function showContentByRole(rol) {
    // Aquí podrías expandir esto para ocultar/mostrar cards, secciones, etc.
    if (rol !== "Admin") {
        const adminSection = document.querySelector(".admin-only");
        if (adminSection) adminSection.style.display = "none";
    }
    applyRoleVisibility(rol);
    // Agrega más roles si es necesario
}