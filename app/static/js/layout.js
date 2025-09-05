import { clearSession } from "../js/utils/errors.js";

document.addEventListener("DOMContentLoaded", async () => {

    // -----------------------------
    // 1️⃣ Alertas según parámetros
    // -----------------------------
    const params = new URLSearchParams(window.location.search);
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
    if (triggered) window.history.replaceState({}, document.title, window.location.pathname);

    // -----------------------------
    // 2️⃣ Sidebar toggle responsive
    // -----------------------------
    const sidebar = document.getElementById("sidebar");
    const mainContent = document.getElementById("mainContent");
    const toggleBtn = document.getElementById("sidebarToggle");

    if (sidebar && mainContent && toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
            mainContent.classList.toggle("expanded");
        });

        const handleResize = () => {
            if (window.innerWidth < 992) {
                sidebar.classList.add("collapsed");
                mainContent.classList.add("expanded");
            } else {
                sidebar.classList.remove("collapsed");
                mainContent.classList.remove("expanded");
            }
        };
        window.addEventListener("resize", handleResize);
        handleResize();
    }

});


// -----------------------------
// 8️⃣ Función de alertas reutilizable
// -----------------------------
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

    setTimeout(() => {
        alert.classList.remove("show");
        setTimeout(() => alert.remove(), 300);
    }, duration);
}
