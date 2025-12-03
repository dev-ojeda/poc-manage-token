import { showGlobalAlert } from "../layout.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js"

const storage = new IndexedDBStorage("AuthDB", "tokens");
let _handlingSession = false;
export async function handleError(err) {
    if (_handlingSession) return;
    _handlingSession = true;

    const msg = err?.message || "";
    const code = err?.code || "";

    try {
        switch (code) {
            case "ACCESS_DENIED":
            case "VALUE_ERROR":
                showGlobalAlert(`⚠️ ${msg}`, "warning", 8000);
                break;
            case "USER_BLOCKED":
                showGlobalAlert(msg, "warning", 8000);
                break;
            case "TOKEN_NOT_FOUND":
            case "SERVER_ERROR":
                showGlobalAlert(`❌ ${msg}`, "danger", 8000);
                break;
            case "TIMEOUT":
            case "NETWORK_ERROR":
            case "RATE_LIMIT_EXCEEDED":
                showGlobalAlert(`${msg}`, "danger", 8000);
                break;
            case "INVALID_USER":
                endSession(`❌ ${msg}`, "danger", 5000);
                break;

            case "INVALID_CREDENTIALS":
                endSession(`❌ ${msg}`, "danger", 5000);
                break;

            case "USER_ALREADY_HAS_TOKEN":
                showGlobalAlert("⚠️ Ya tenés sesión activa en otro dispositivo.", "warning", 6000);
                break;

            case "UPSERT_TOKEN_FAILED":
            case "REGISTER_SESSION_FAILED":
                showGlobalAlert("⚠️ Error interno. Contactá a soporte.", "danger", 8000);
                break;

            case "INVALID_JSON":
            case "MISSING_FIELDS":
                showGlobalAlert(`⚠️ ${msg}`, "warning", 6000);
                break;

            case "UNAUTHORIZED":
            case "TOKEN_EXPIRED":
                await endSession("⏳ Tu sesión ha expirado o no es válida. Iniciá sesión nuevamente.", "info");
                break;

            case "CONFLICT":
                showGlobalAlert("❌ Ya existe una sesión activa en otro dispositivo.", "danger", 5000);
                break;
            case "INVALID_REVOKED_TOKEN":
            case "INVALID_REVOKED_TOKEN_BLACKLIST":
                await endSession(`⚠️ ${msg}`, "warning", 8000);
                break;

            default: {
                const msgStr = String(msg);
                const codeStr = String(code);

                if (codeStr.includes("ExpiredSignatureError")) {
                    await endSession("⏳ Tu sesión ha expirado. Iniciá sesión nuevamente.", "info");
                } else if (msgStr.includes("Token no existe")) {
                    await endSession("❌ Token no existe. Volvé a iniciar sesión.", "danger", 8000);
                } else if (codeStr.includes("InvalidAudienceError")) {
                    showGlobalAlert("⚠️ El token no corresponde a este cliente (audiencia inválida).", "danger", 8000);
                } else if (codeStr.includes("ImmatureSignatureError")) {
                    await endSession("⚠️ Token aún no es válido (nbf).", "danger", 8000);
                } else if (codeStr.includes("MaxAttemptsExceeded")) {
                    await endSession(`🚫 ${msgStr}`, "danger", 8000);
                } else if (codeStr.includes("InvalidIssuerError")) {
                    showGlobalAlert("⚠️ Emisor del token inválido. Contactá a soporte.", "danger", 8000);
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
    } finally {
        // Limpiar URL solo una vez
        globalThis.history.replaceState({}, globalThis.document.title, globalThis.location.pathname);
        _handlingSession = false;
    }
    if (import.meta.env?.DEV) console.error("🔴 handleError:", err);
}

let _clearingSession = false;
export async function clearSession() {
    if (_clearingSession) return;
    _clearingSession = true;
    await storage.clearAll();
    _clearingSession = false;
}

// -----------------------------
// Función global para finalizar sesión
// -----------------------------
export async function endSession(message, type = "danger", timeout = 6000) {
    await clearSession();
    showGlobalAlert(message, type, timeout);
}