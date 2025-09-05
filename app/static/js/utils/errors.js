import { showAlert } from "../layout.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js"
import { MetricsStorage } from "../adapters/MetricsStorage.js"

const storage = new IndexedDBStorage("AuthDB", "tokens");
const metricsStorage = new MetricsStorage();

export async function handleError(err) {
    const msg = err?.message || "";
    const code = err?.code || "";

    // Helpers
    async function endSession(message, type = "danger", timeout = 6000) {
        await clearSession();
        showAlert(message, type, timeout);
    }

    switch (code) {
        case "VALUE_ERROR":
            showAlert(`⚠️ ${msg}`, "warning", 8000);
            break;
        case "USER_BLOCKED":
            showAlert(msg, "warning", 8000);
            break;
        case "SERVER_ERROR":
            showAlert(`❌ ${msg}`, "danger", 8000);
            break;
        case "INVALID_USER":
            endSession(`❌ ${msg}`, "danger", 5000);
            break;
        case "INVALID_CREDENTIALS":
            endSession(`❌ ${msg}`, "danger", 5000);
            break;

        case "USER_ALREADY_HAS_TOKEN":
            showAlert("⚠️ Ya tenés sesión activa en otro dispositivo.", "warning", 6000);
            break;

        case "UPSERT_TOKEN_FAILED":
        case "REGISTER_SESSION_FAILED":
            showAlert("⚠️ Error interno. Contactá a soporte.", "danger", 8000);
            break;

        case "INVALID_JSON":
        case "MISSING_FIELDS":
            showAlert(`⚠️ ${msg}`, "warning", 6000);
            break;

        case "UNAUTHORIZED":
        case "TOKEN_EXPIRED":
            await endSession("⏳ Tu sesión ha expirado o no es válida. Iniciá sesión nuevamente.", "info");
            break;

        case "CONFLICT":
            showAlert("❌ Ya existe una sesión activa en otro dispositivo.", "danger", 5000);
            break;
        case "INVALID_REVOKED_TOKEN_BLACKLIST":
            await endSession(`⚠️ ${msg}`, "warning", 8000);
            break;

        default: {
            const msgStr = String(msg);
            const codeStr = String(code);

            if (codeStr.includes("ExpiredSignatureError")) {
                await endSession("⏳ Tu sesión ha expirado. Iniciá sesión nuevamente.", "info");
            } else if (codeStr.includes("InvalidAudienceError")) {
                showAlert("⚠️ El token no corresponde a este cliente (audiencia inválida).", "danger", 8000);
            } else if (codeStr.includes("ImmatureSignatureError")) {
                await endSession("⚠️ Token aún no es válido (nbf).", "danger", 8000);
            } else if (codeStr.includes("MaxAttemptsExceeded")) {
                await endSession(`🚫 ${msgStr}`, "danger", 8000);
            } else if (codeStr.includes("InvalidIssuerError")) {
                showAlert("⚠️ Emisor del token inválido. Contactá a soporte.", "danger", 8000);
            } else if (codeStr.includes("InvalidTokenError") || msgStr.includes("Token inválido")) {
                await endSession("❌ Token inválido o corrupto. Volvé a iniciar sesión.", "danger", 8000);
            } else if (codeStr.includes("AbortError")) {
                // Mejor como info o ignorar: no es un error real
                console.info("⚠️ Petición abortada:", msgStr);
                return;
            } else {
                await endSession(`❌ Error inesperado: ${msgStr}`, "danger", 8000);
            }
        }
    }

    // 🧹 Limpieza de URL
    window.history.replaceState({}, document.title, window.location.pathname);

    // 🔎 Logging solo en dev
    if (import.meta.env?.DEV) {
        console.error("🔴 handleError:", err);
    }
}

export async function clearSession() {
    await storage.clearAll();
    await metricsStorage.clearAll();
}
