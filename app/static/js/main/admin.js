import { showAlert } from "../layout.js";
import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { attachSessionListeners, loadActiveSessions } from "./sesiones.js";
import { loadAuditLogs, attachAuditListeners } from "./auditoria.js";
// import { loadTokens } from "./tokens.js"; // cuando lo implementes

const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost:5000",
    storage: new LocalStorageAdapter()
});

let currentAuditPage = 1;
let tokenTimerInterval = null;
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const user_rol = api_admin.userRol;
        const user_name = api_admin.userName;
        const expiracion = api_admin.tokenExp;
        if (user_rol !== "Admin") {
            showAlert("🚫 No tienes permisos para acceder a este panel.", "danger", 5000);
            return;
        }
        document.getElementById("userName").textContent = `Hola, ${user_name} (Admin)`;
        showContentByRole(user_rol);
        document.querySelector("#dashboardContent").style.display = "block";
        startTokenTimer(expiracion);
        // Carga inicial de auditoría y sesiones
        await loadAuditLogs(currentAuditPage, api_admin);
        await loadActiveSessions(api_admin);

        // Adjuntar listeners
        attachAuditListeners(api_admin, () => loadAuditLogs(currentAuditPage, api_admin));
        attachSessionListeners(api_admin, () => loadActiveSessions(api_admin));

        // Menú lateral
        document.body.addEventListener("click", async (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;
            e.preventDefault();

            const action = btn.dataset.action;
            // Define qué divs corresponderán a cada acción
            const sections = {
                "sesiones": document.querySelector("#audit-session"),
                "sesiones-auditadas": document.querySelector("#audit-table"),
                "tokens": null // Aquí puedes asignar otro div si lo tienes
            };
            // Ocultar todas las secciones
            Object.values(sections).forEach(sec => sec && (sec.style.display = "none"));
            // Mostrar solo la sección relacionada a la acción
            const activeSection = sections[action];
            if (activeSection) activeSection.style.display = "block";
            switch (action) {
                case "sesiones":
                    await loadActiveSessions(api_admin);
                    break;
                case "sesiones-auditadas":
                    currentAuditPage = 1;
                    await loadAuditLogs(currentAuditPage, api_admin);
                    break;
                case "tokens":
                    showAlert("Funcionalidad tokens no implementada aún.", "info");
                    break;
                default:
                    console.warn("Acción desconocida:", action);
            }
        });
        document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
            e.preventDefault();
            await api_admin.logout_admin();
        });
    } catch (err) {
        console.error(err);
    }
});
function toggleSections(action) {
    document.querySelectorAll(".section").forEach(sec => sec.style.display = "none");
    const target = document.getElementById(`section-${action}`);
    if (target) target.style.display = "block";
}
function showContentByRole(rol) {
    if (rol !== "Admin") {
        const adminSection = document.querySelector(".admin-only");
        if (adminSection) adminSection.style.display = "none";
    }
    applyRoleVisibility(rol);
}
function startTokenTimer(expTimestamp) {
    const timerElement = document.getElementById("tokenTimer");
    if (!timerElement || !expTimestamp) return;
    clearInterval(tokenTimerInterval);

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
    if (!rol) return;
    const roles = rol.toLowerCase();
    document.querySelectorAll('[class*="role-"]').forEach(el => {
        const requiredRoles = [...el.classList].filter(c => c.startsWith("role-")).map(c => c.replace("role-", ""));
        el.style.display = requiredRoles.some(r => roles.includes(r)) ? "" : "none";
    });
}