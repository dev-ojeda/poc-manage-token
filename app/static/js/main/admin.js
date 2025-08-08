import { showAlert } from "../layout.js";
import { ApiAdmin } from "../api/ApiAdmin.js";
import { SessionService } from "../services/SessionService.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { renderButtonRevocar, getStatusBadge } from "../utils/sessionUtils.js";
import { openChat } from "../modules/chatHandler.js";
import { AuditPanel } from "../modules/auditPanel.js";
import { renderAuditLogs } from "../modules/auditTable.js";
import { emitEvent, on } from "../utils/eventBus.js";
const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

const sessionServices = new SessionService();
const auditPanel = new AuditPanel('#audit-panel');
// Guardamos última IP y UA por device_id
const sessionAuditCache = new Map();
const PollingManager = (() => {
    let intervalId = null;

    function iniciar(fn, intervalo = 10000) {
        if (intervalId !== null) detener();
        intervalId = setInterval(fn, intervalo);
    }

    function detener() {
        if (intervalId !== null) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    return { iniciar, detener };
})();
let tokenTimerInterval = null;
let sessionsTimerInterval = null;
let lastUpdate = 0;
// Inicializar al cargar DOM
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

    // Mostrar secciones según rol
    showContentByRole(user_rol);

    // Mostrar dashboard y comenzar temporizador
    dashboardContent.style.display = "block";
    startTokenTimer(expiracion);
    openChat(user_rol);
    await loadActiveSessions();
    // Cargar sesiones si es Admin
    //await auditPanel.loadFromAPI();
    PollingManager.iniciar(loadActiveSessions, 10000);

    document.addEventListener("auditEvent", (e) => {
        e.preventDefault();
        auditPanel.addEvent(e.detail);
    });

    document.addEventListener("tokenRefreshed", async (e) => {
        e.preventDefault();
        await loadActiveSessions();
    });
    // Eventos generales
    document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
        e.preventDefault();
        await api_admin.logout_admin();
        e.stopPropagation();
        PollingManager.detener();
    });
    document.getElementById("statusFilter")?.addEventListener("change", async (event) => {
        event.preventDefault();
        //lastFetchTime = null;
        filtro = event.target.value;
        document.querySelector("#sessionsTable tbody").innerHTML = "";
        await loadActiveSessions(filtro);
        event.stopPropagation();
    })   

});
on('auditLogsLoaded', logs => {
    renderAuditLogs(logs); // función propia para mostrar en tabla
});
function detectarAnomalías(session) {
    const key = session.device_id;
    const prev = sessionAuditCache.get(key);

    if (!prev) {
        sessionAuditCache.set(key, {
            ip_address: session.ip_address,
            user_agent: session.user_agent
        });
        return;
    }

    let anomalía = null;
    if (prev.ip_address !== session.ip_address) {
        anomalía = `Cambio de IP para ${session.device_id}: ${prev.ip_address} → ${session.ip_address}`;
    } else if (prev.user_agent !== session.user_agent) {
        anomalía = `Cambio de User-Agent para ${session.device_id}: "${prev.user_agent}" → "${session.user_agent}"`;
    }

    if (anomalía) {
        emitEvent("auditEvent", {
            type: "suspicious",
            detail: anomalía,
            timestamp: Date.now()
        });
    }

    sessionAuditCache.set(key, {
        ip_address: session.ip_address,
        user_agent: session.user_agent
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
async function tryRefreshToken() {
    const refreshToken = api_admin.refreshToken;
    if (!refreshToken) {
        showAlert("⚠️ No hay refresh token guardado.", "warning", 4000);
        await api_admin.logout_admin();
        return;
    }

    try {
        const response = await fetch("/api/auth/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken, device_id: api_user.deviceId, user_agent: api.userAgent })
        });
        const data = await response.json();
        if (response.ok) {

            api_admin.storage.set("access_token", data.access_token);
            api_admin.storage.set("refresh_token", data.refresh_token);
            api_admin.storage.set("device_id", data.device_id);
            api_admin.storage.set("username", data.username);
            api_admin.storage.set("rol", data.rol);
            api_admin.storage.set("exp", data.exp);
            showAlert("✅ Token refrescado", "success", 4000);
            let expiracion = data.exp
            startTokenTimer(expiracion);
            // 🔔 Disparar evento personalizado
            document.dispatchEvent(new CustomEvent("tokenRefreshed"));
        } else {
            throw new Error(`Error ${data.msg} ${data.code}`);
            await api.logout("intentos");
        }
    } catch (err) {
        api_admin.handleError(err)
        await api_admin.logout("intentos");
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

async function loadActiveSessions(filtro) {
    if (filtro === null || filtro === undefined) {
        filtro = null;
    }
    lastUpdate = Math.floor(Date.now() / 1000);
    console.log("INICIO: " + lastUpdate);
    try {
        const response = await fetch("/api/auth/sessions/active", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${api_admin.accessToken}`,
                "X-Token-Type": "access"
            },
            body: JSON.stringify({ filtro_status: filtro })
        });

        const tbody = document.querySelector("#tablaSesiones tbody");

        const data = await response.json();
        console.log("DATA: " + data);
        tbody.innerHTML = "";
        //lastUpdate = last_update;
        //console.log("INICIO: " + formatDate(lastUpdate));
        console.log("DATOS: " + data.count);
        if (!data.count) {
            showAlert(`SESIONES ACTIVAS: ${data.count}`, "info", 8000);
            tbody.innerHTML = "<tr><td colspan='5' class='text-center'>Sin registros</td></tr>";
            return;
        }

        data.sessions.forEach((session) => {
            //detectarAnomalías(session); // 👈 Agregalo acá
            const isCurrent = session.device_id === api_admin.getDeviceId();
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${session.username}</td>
                <td>${session.device_id}</td>
                <td>${session.browser}</td>
                <td>${formatDate(session.login_at)}</td>
                <td>${formatDate(session.last_refresh_at)}</td>
                <td>${session.reason || "-"}</td>
                <td>${getStatusBadge(session.status)}</td>
                <td data-label="Acciones">${renderButtonRevocar(session, isCurrent)}</td>
            `;
            tbody.appendChild(row);

        });
        tbody.querySelectorAll(".btn-revocar").forEach(btn => {
            btn.addEventListener("click", () => revocarSesion(btn));
        });

    } catch (error) {
        console.error("Error al cargar sesiones activas", error);
    }
}
function formatDate(timestamp) {
    if (!timestamp) return "-";
    const date = new Date(timestamp * 1000); // si viene en segundos
    return date.toLocaleString("es-CL");
}
function applyRoleVisibility(rol) {
    const roles = rol.toLowerCase() || false;

    if (roles) {
        const elements = document.querySelectorAll('[class*="role-"]');

        elements.forEach(el => {
            const requiredRoles = Array.from(el.classList)
                .filter(cls => cls.startsWith("role-"))
                .map(cls => cls.replace("role-", ""));

            const hasAccess = requiredRoles.some(role => roles.includes(role));

            el.style.display = hasAccess ? "" : "none";
        });
    }
    else {
        return roles;
    }


}
async function revocarSesion(btn) {
    const isCurrent = btn.getAttribute("data-username") === api_user.userName;
    const isCurrentDevice = btn.getAttribute("data-device") === api_user.deviceId;
    const isCurrentRol = btn.getAttribute("data-rol") === api_user.userRol;
    const isCurrentRefresh = btn.getAttribute("data-refresh") === api_user.refreshToken;

    if (isCurrent) showAlert(`👋 Cerrando sesión actual`, "info", 8000);
    if (isCurrentDevice) showAlert(`⚠️ Ya existe Device ${isCurrentDevice}`, "warning", 8000);
    if (isCurrentRol) showAlert(`⚠️ Ya existe Rol ${isCurrentRol}`, "warning", 8000);
    if (isCurrentRefresh) showAlert(`⚠️ Ya existe Refresh ${isCurrentRefresh}`, "warning", 8000);

    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;

    try {
        await sessionServices.revocarSesion({
            session_id: btn.getAttribute("data-session"),
            access: api_user.accessToken,
            username: btn.getAttribute("data-username"),
            device: btn.getAttribute("data-device"),
            rol: btn.getAttribute("data-rol"),
            refresh: btn.getAttribute("data-refresh")
        });

        showAlert("✅ Sesión revocada correctamente", "success");
        if (isCurrent) {
            setTimeout(() => {
                this.api.clearSession();
                location.href = "/?revoked=true";
            }, 2000);
        } else {
            document.dispatchEvent(new CustomEvent("tokenRefreshed"));
        }
    } catch (err) {
        showAlert(`❌ ${err.message}`, "danger", 8000);
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}