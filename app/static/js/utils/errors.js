import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";

const almacenamiento = new LocalStorageAdapter();
export function handleError(err) {
    const msg = err?.message || "";

    if (msg.includes("expirada") || msg.includes("ExpiredSignatureError")) {
        showAlert("⏳ Tu sesión ha expirado. Iniciá sesión nuevamente.", "info", 6000);
    }
    else if (msg.includes("Bloqueado")) {
        showAlert(msg, "warning", 8000);
    }
    else if (msg.includes("InvalidAudienceError")) {
        showAlert("⚠️ El token no corresponde a este cliente (audiencia inválida).", "danger", 8000);
    }
    else if (msg.includes("InvalidIssuerError")) {
        showAlert("⚠️ Emisor del token inválido. Contactá a soporte.", "danger", 8000);
    }
    else if (msg.includes("InvalidTokenError") || msg.includes("Token inválido")) {
        showAlert("❌ Token inválido o corrupto. Por favor, volvé a iniciar sesión.", "danger", 8000);
    }
    else if (msg.includes("Error 403")) {
        showAlert("🚫 Demasiados intentos. Esperá un momento antes de intentar de nuevo.", "warning", 8000);
    }
    else if (msg.includes("Error 401") || msg.includes("Credenciales incorrectas")) {
        showAlert("❌ Usuario o contraseña incorrecta", "danger", 5000);
    }
    else if (msg.includes("Error")) {
        showAlert(msg, "danger", 8000);
    }
    else if (msg.includes("AbortError")) {
        showAlert(msg, "danger", 8000);
    }
    else {
        showAlert(`❌ Error inesperado: ${msg}`, "danger", 8000);
    }
    clearSession();
    window.history.replaceState({}, document.title, window.location.pathname);
}

export function clearSession() {
    almacenamiento.clear();
    console.log("STORAGE: " + almacenamiento.count())
}