import { showAlert } from "../layout.js";
import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

export async function loadActiveSessions() {

    const filtro = document.getElementById("statusFilter").value;
    if (filtro === null || filtro === undefined) {
        filtro = null;
    }
    lastUpdate = Math.floor(Date.now() / 1000);
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
        tbody.innerHTML = "";
        if (!data.count) {
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
            tbody.querySelectorAll(".btn-revocar").forEach(btn => {
                btn.addEventListener("click", () => revocarSesion(btn));
            });

        });

    } catch (error) {
        console.error("Error al cargar sesiones activas", error);
        handleError(error);
    }
}
function formatDate(timestamp) {
    if (!timestamp) return "-";
    const date = new Date(timestamp * 1000); // si viene en segundos
    return date.toLocaleString("es-CL");
}
function renderButtonRevocar(sesion, isCurrent) {
    return isCurrent
        ? '<span class="badge bg-primary">Actual</span>'
        : `<button class="btn btn-danger btn-sm btn-revocar" 
                data-session="${sesion.user_id}" 
                data-device="${sesion.device_id}" 
                data-username="${sesion.username}"
                data-rol="${sesion.rol}"
                data-refresh="${sesion.refresh_token}"
                <i class="bi bi-lock-fill"></i> Revocar
            </button>`;
}
function getStatusBadge(status) {
    switch (status) {
        case "active":
            return `<span class="badge bg-success">Activa</span>`;
        case "revoked":
            return `<span class="badge bg-warning text-dark">Revocada</span>`;
        case "expired":
            return `<span class="badge bg-danger">Expirada</span>`;
        default:
            return `<span class="badge bg-secondary">Desconocido</span>`;
    }
}

async function revocarSesion(btn) {
    const isCurrent = btn.getAttribute("data-username");
    const isCurrentDevice = btn.getAttribute("data-device");
    const isCurrentRol = btn.getAttribute("data-rol");
    const isCurrentRefresh = btn.getAttribute("data-refresh");

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
                clearSession();
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