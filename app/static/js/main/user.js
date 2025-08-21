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
    const expiracion = api_user.tokenExp;
    const dashboardContent = document.getElementById("dashboardContent");
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

    document.addEventListener("startTokenTimer", (event) => {
        console.log("TIMER: " + tokenTimerInterval);
        const progressBar = document.getElementById("tokenProgress");
        progressBar.classList.remove("bg-danger");
        progressBar.classList.add("bg-success");
        const { new_expiracion } = event.detail;
        startTokenTimer(new_expiracion);
    });


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
                device_id: api_user.deviceId,  // <-- paréntesis acá
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
            
            console.log("TIMER 1: " + tokenTimerInterval)
            console.log("EXP: " + data.exp)
            document.dispatchEvent(new CustomEvent("startTokenTimer", {
                detail: { new_expiracion: parseFloat(data.exp) }
            }));
        } else {
            showAlert(`⚠️ Error al refrescar token: ${data.msg}`, "danger", 5000);
            await api_user.logout("intentos");
        }
    } catch (err) {
        handleError(err);
        showAlert("❌ No se pudo renovar sesión. Inicia sesión de nuevo.", "danger", 5000);
        await api_user.logout("intentos");
    }
}

function startTokenTimer(expTimestamp) {
    const timerElement = document.getElementById("tokenTimer");
    const progressBar = document.getElementById("tokenProgress");
    if (!timerElement || !expTimestamp || !progressBar) return;

    clearInterval(tokenTimerInterval);  // Evita múltiples intervalos

    const expDate = new Date(expTimestamp * 1000);
    console.log("🕒 Expira exactamente en:", expDate.toLocaleString("es-CL"));

    // Guardamos el tiempo total del token (en ms) desde ahora hasta expiración
    const totalDuration = expTimestamp * 1000 - Date.now();
    // Transiciones suaves (ancho y color)
    tokenTimerInterval = setInterval(() => {
        const remaining = expTimestamp * 1000 - Date.now();
        let percentage = Math.max(0, Math.floor((remaining / totalDuration) * 100));
        if (remaining <= 0) {
            timerElement.textContent = "⏱ Token expirado";
            timerElement.classList.replace("text-success", "text-danger");
            progressBar.classList.remove("bg-success", "bg-warning");
            progressBar.classList.add("bg-danger");
            clearInterval(tokenTimerInterval);
            return;
        }

        // Actualizar barra de progreso
        progressBar.style.width = `${percentage}%`;
        if (percentage <= 29) {
            progressBar.classList.replace("bg-warning", "bg-danger");
        }
        else if (percentage <= 49) {
            progressBar.classList.replace("bg-success", "bg-warning");
        }
        else progressBar.classList.add("bg-success");
        // Refrescar automáticamente 30s antes de expirar
        if (remaining <= 30000) {
            showAlert("♻️ Refrescando sesión automáticamente...", "info", 3000);
            timerElement.textContent = "♻️ Renovando token...";
            clearInterval(tokenTimerInterval);
            tryRefreshToken();
            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        timerElement.textContent = `⏱ Expira en ${minutes}:${seconds.toString().padStart(2, "0")}`;
        timerElement.classList.add("text-success");
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

//let tokenTimer = {
//    intervalId: null,
//    endTimestamp: null,
//    progressBar: document.getElementById("tokenProgress"),

//    start(expTimestamp) {
//        this.stop();
//        this.endTimestamp = expTimestamp;

//        this.intervalId = setInterval(() => {
//            const remainingMs = this.endTimestamp * 1000 - Date.now();

//            if (remainingMs <= 0) {
//                this.updateUI(0, "⏱ Token expirado", "danger");
//                this.stop();
//                return;
//            }

//            // Refrescar token automáticamente 30s antes
//            if (remainingMs <= 30000) {
//                this.stop();
//                showAlert("♻️ Renovando token automáticamente...", "info", 3000);
//                tryRefreshToken();
//            }

//            this.updateUI(remainingMs);
//        }, 500); // actualización más fluida
//    },

//    stop() {
//        if (this.intervalId) {
//            clearInterval(this.intervalId);
//            this.intervalId = null;
//        }
//    },

//    updateUI(remainingMs, text = null, status = null) {
//        const timerElement = document.getElementById("tokenTimer");
//        const totalMs = this.endTimestamp * 1000 - (Date.now() - remainingMs);
//        const percent = Math.max(0, Math.min(100, (remainingMs / totalMs) * 100));

//        // Actualizar texto
//        if (timerElement) {
//            if (!text) {
//                const minutes = Math.floor(remainingMs / 60000);
//                const seconds = Math.floor((remainingMs % 60000) / 1000);
//                text = `⏱ Expira en ${minutes}:${seconds.toString().padStart(2, "0")}`;
//            }
//            timerElement.textContent = text;

//            // Cambiar color según tiempo restante
//            timerElement.classList.remove("text-success", "text-warning", "text-danger");
//            if (status) {
//                timerElement.classList.add(`text-${status}`);
//            } else if (percent <= 10) {
//                timerElement.classList.add("text-danger");
//            } else if (percent <= 30) {
//                timerElement.classList.add("text-warning");
//            } else {
//                timerElement.classList.add("text-success");
//            }
//        }

//        // Actualizar barra de progreso
//        if (this.progressBar) {
//            this.progressBar.style.transition = "width 0.5s linear";
//            this.progressBar.style.width = `${percent}%`;

//            // Cambiar color según tiempo restante
//            this.progressBar.classList.remove("bg-success", "bg-warning", "bg-danger");
//            if (percent <= 10) this.progressBar.classList.add("bg-danger");
//            else if (percent <= 30) this.progressBar.classList.add("bg-warning");
//            else this.progressBar.classList.add("bg-success");
//        }
//    }
//};

