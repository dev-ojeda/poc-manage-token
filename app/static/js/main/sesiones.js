// sessions.js
import { showAlert } from "../layout.js";
import { handleError } from "../utils/errors.js";
import { renderButtonRevocar, getStatusBadge } from "../utils/sessionUtils.js";

/**
 * Carga las sesiones activas y renderiza la tabla.
 * @param {object} api_admin Instancia de ApiAdmin
 * @param {Function} [reloadFn] Función opcional para recargar datos
 */
export async function loadActiveSessions(api_admin, reloadFn) {
    const filtro = document.getElementById("statusFilter")?.value || null;
    const payload = { filtro_status: filtro };

    try {
        const response = await fetch("/api/auth/sessions/active", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${api_admin.accessToken}`,
                "X-Token-Type": "access"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Error cargando sesiones activas");

        const data = await safeJson(response);
        const tbody = document.querySelector("#tablaSesiones tbody");
        tbody.innerHTML = "";

        if (!data.count) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center">Sin registros</td></tr>`;
            return;
        }

        data.sessions.forEach(session => {
            const isCurrent = session.device_id === api_admin.getDeviceId();
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${session.username}</td>
                <td>${session.device_id}</td>
                <td>${session.browser || "-"}</td>
                <td>${formatDateIso(session.login_at)}</td>
                <td>${formatDateIso(session.last_refresh_at)}</td>
                <td>${session.reason || "-"}</td>
                <td>${getStatusBadge(session.status)}</td>
                <td data-label="Acciones">${renderButtonRevocar(session, isCurrent)}</td>
            `;
            tbody.appendChild(row);
        });

        // Delegación de eventos, solo una vez
        attachSessionListeners(api_admin, reloadFn);

    } catch (err) {
        console.error("Error al cargar sesiones activas", err);
        handleError(err);
    }
}

/**
 * Agrega listeners a los botones de revocar sesión.
 */
export function attachSessionListeners(api_admin, reloadFn) {
    const tbody = document.querySelector("#tablaSesiones tbody");
    if (!tbody || tbody.hasListener) return;

    tbody.addEventListener("click", async (e) => {
        const btn = e.target.closest(".btn-revocar");
        if (!btn) return;
        e.preventDefault();
        try {
            await revocarSesion(btn, api_admin, reloadFn);
        } catch (err) {
            showAlert(`❌ ${err.message}`, "danger");
        }
    });

    tbody.hasListener = true;
}

/**
 * Revoca una sesión específica.
 */
async function revocarSesion(btn, api_admin, reloadFn) {
    const payload = {
        user_id: btn.getAttribute("data-session"),
        username: btn.getAttribute("data-username"),
        device_id: btn.getAttribute("data-device"),
        user_rol: btn.getAttribute("data-rol"),
        refresh_token: btn.getAttribute("data-refresh"),
        user_agent: btn.getAttribute("data-browser"),
    };

    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;

    try {
        const response = await fetch("/api/auth/sessions/revoke", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${api_admin.accessToken}`,
                "X-Token-Type": "access"
            },
            body: JSON.stringify(payload)
        });

        const data = await safeJson(response);

        if (response.ok) {
            showAlert("✅ Sesión revocada correctamente", "success");
            if (typeof reloadFn === "function") await reloadFn();
        } else {
            throw new Error(`Error ${data.msg || ""} ${data.code || ""}`);
        }
    } catch (err) {
        console.error(err);
        showAlert(`❌ ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

/**
 * Formatea timestamp Unix (segundos) a string legible.
 */
function formatDate(timestamp) {
    if (!timestamp) return "-";
    return new Date(timestamp * 1000).toLocaleString("es-CL");
}

/**
 * Formatea string ISO a string legible.
 */
function formatDateIso(isoString) {
    if (!isoString) return "-";
    return new Date(isoString).toLocaleString("es-CL");
}

/**
 * Convierte la respuesta JSON de forma segura.
 */
async function safeJson(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}
