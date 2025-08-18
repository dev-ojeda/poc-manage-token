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
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const toggleBtn = document.getElementById('sidebarToggle');

    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
    });



    window.addEventListener('resize', handleResize);
    window.addEventListener('load', handleResize);
});
function handleResize() {
    if (window.innerWidth < 992) { // <lg
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
    } else {
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
    }
}
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