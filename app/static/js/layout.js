document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);

    if (params.get("expired") === "true") {
        showAlert("⚠️ Tu sesión ha expirado. Por favor, iniciá sesión nuevamente.", "warning", 4000);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (params.get("unauthorized") === "true") {
        showAlert("🚫 Acceso no autorizado. Iniciá sesión para continuar.", "danger", 4000);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (params.get("untoken") === "true") {
        showAlert("🚫 No existe token.", "danger", 4000);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});
export function showAlert(message, type = "success", duration = 8000) {
    const container = document.getElementById("alertContainer") || document.body;

    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show mt-2`;
    alert.role = "alert";
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    container.appendChild(alert);

    // Auto-remove
    setTimeout(() => {
        alert.classList.remove("show");
        setTimeout(() => {
            if (alert) alert.remove();
        }, 300);
    }, duration);
}