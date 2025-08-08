import { showAlert } from "../layout.js";
import { ApiClient } from "../ApiClient.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";

const api = new ApiClient({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

let tokenTimerInterval = null;

export function startTokenCountdown() {
    const el = document.getElementById("tokenTimer");
    if (!el) return;

    clearInterval(tokenTimerInterval);

    tokenTimerInterval = setInterval(() => {
        const seconds = getTokenRemainingSeconds();

        if (seconds <= 0) {
            el.textContent = "❌ Token expirado";
            clearInterval(tokenTimerInterval);
            tryRefreshToken(); // 🚨 Intentar refresh apenas expira
            return;
        }

        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        el.textContent = `⏱️ Token expira en ${m}m ${s}s`;
        el.style.color = seconds < 10 ? "red" : seconds < 30 ? "orange" : "inherit";
    }, 1000);
}

function getTokenRemainingSeconds() {
    const exp = api.tokenExp;
    if (!exp) return 0;
    const now = Math.floor(Date.now() / 1000);
    return Math.max(exp - now, 0);
}

export async function tryRefreshToken() {
    const refreshToken = api.refreshToken;
    const deviceId = api.deviceId;
    const userAgent = api.userAgent;

    if (!refreshToken || !deviceId) {
        showAlert("⚠️ No hay refresh token o device ID", "warning", 4000);
        return await api.logout("no-refresh-token");
    }

    try {
        const res = await fetch("/api/auth/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                refresh_token: refreshToken,
                device_id: deviceId,
                user_agent: userAgent,
            })
        });

        const data = await res.json();

        if (res.ok) {
            console.log("🔄 Nuevo token recibido:", data);

            // ✅ Validar que el JWT ID sea string antes de guardar
            if (typeof data.jti !== "string") {
                throw new Error("JWT ID must be a string");
            }

            // ⬇️ Guardar nuevos tokens y sesión
            api.storage.set("access_token", data.access_token);
            api.storage.set("refresh_token", data.refresh_token);
            api.storage.set("exp", data.exp);
            api.storage.set("jti", data.jti);
            api.storage.set("username", data.username);
            api.storage.set("rol", data.rol);

            showAlert("✅ Token refrescado", "success", 3000);
            startTokenCountdown();
            document.dispatchEvent(new CustomEvent("tokenRefreshed"));
        } else {
            console.warn("❌ Refresh fallido:", data);
            if (res.status === 403) {
                showAlert("🔒 Token reusado o inválido. Sesión revocada.", "danger", 5000);
            } else {
                showAlert(`❌ Error: ${data.msg || "Refresh fallido"}`, "danger", 4000);
            }

            await api.logout("refresh_failed");
        }
    } catch (err) {
        console.error("❌ Error al intentar refrescar:", err);
        showAlert("⚠️ Error de red o token inválido", "danger", 4000);
        await api.logout("refresh_error");
    }
}
