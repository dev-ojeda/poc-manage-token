import { clearSession } from "../js/utils/errors.js";

document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);

    // --- Mapeo de alertas según parámetros ---
    const alerts = {
        logout: { msg: "⚠️ Tu sesión ha expirado. Por favor, iniciá sesión nuevamente.", type: "warning", clear: true },
        unauthorized: { msg: "🚫 Acceso no autorizado. Iniciá sesión para continuar.", type: "danger" },
        untoken: { msg: "🚫 No existe token.", type: "danger" },
    };

    let triggered = false;
    for (const [key, { msg, type, clear }] of Object.entries(alerts)) {
        if (params.get(key) === "true") {
            showAlert(msg, type, 5000);
            if (clear) await clearSession();
            triggered = true;
        }
    }

    // Limpia la URL si hubo algún parámetro especial
    if (triggered) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // --- Sidebar toggle ---
    const sidebar = document.getElementById("sidebar");
    const mainContent = document.getElementById("mainContent");
    const toggleBtn = document.getElementById("sidebarToggle");

    if (sidebar && mainContent && toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
            mainContent.classList.toggle("expanded");
        });

        // --- Responsive sidebar ---
        const handleResize = () => {
            if (window.innerWidth < 992) { // Bootstrap breakpoint "lg"
                sidebar.classList.add("collapsed");
                mainContent.classList.add("expanded");
            } else {
                sidebar.classList.remove("collapsed");
                mainContent.classList.remove("expanded");
            }
        };

        window.addEventListener("resize", handleResize);
        handleResize(); // corre al inicio
    }
});

// --- Alerts ---
export function showAlert(message, type = "success", duration = 6000) {
    const container = document.getElementById("alertContainer") || document.body;

    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show mt-2 shadow`;
    alert.role = "alert";
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    container.appendChild(alert);

    // Auto-remove
    setTimeout(() => {
        alert.classList.remove("show");
        setTimeout(() => alert.remove(), 300);
    }, duration);
}

//// --- BroadcastChannel para logout global ---
//const channel = new BroadcastChannel("auth");

//// Escuchar mensajes de logout en otras pestañas
//channel.onmessage = async (e) => {
//    if (e.data === "logout") {
//        await clearSession();
//        window.location.href = "/";
//    }
//};

//// Función para disparar logout y propagarlo a todas las pestañas
//export async function triggerLogout() {
//    await clearSession();
//    channel.postMessage("logout");
//    window.location.href = "/";
//}
