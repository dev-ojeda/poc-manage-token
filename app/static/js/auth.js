import { ApiUser } from "../js/api/ApiUser.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { LocalStorageAdapter } from "../js/adapters/LocalStorageAdapter.js";
import { clearSession, handleError } from "../js/utils/errors.js"
const api_user = new ApiUser({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost:5000",
    storage: new LocalStorageAdapter()
});

const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost:5000",
    storage: new LocalStorageAdapter()
});


document.addEventListener("DOMContentLoaded", () => {

    const params = new URLSearchParams(window.location.search);
    if (params.has("logged_out")) {
        clearSession();
        history.replaceState(null, "", window.location.pathname);
        // Redirigir explícitamente a la raíz del SPA
        window.location.href = "/";
    }

    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            clearSession();
            window.location.href = "/";
            //window.location.reload();
        }
    });
    const form = document.getElementById("loginForm");
    if (!form) return; // Evita ejecutar en páginas sin login
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            const user = document.getElementById("username").value.trim();
            const pass = document.getElementById("password").value;

            let res = null;
            if (user.includes("admin")) {  // Esto lo vamos a eliminar después, pero lo dejamos momentáneamente
                res = await api_admin.login_admin(user, pass);
            } else {
                res = await api_user.login(user, pass);
            }

            if (!res) return; // login falló

            const role = res.rol || "User";

            const dashboardValid = role === "Admin"
                ? await api_admin.admin_dashboard()
                : await api_user.user_dashboard();

            if (!dashboardValid) return;

            location.replace(role === "Admin" ? "/admin/dashboard" : "/dashboard");

        } catch (error) {
            handleError(error);
            console.error("Error en login:", error);
        }
        e.stopPropagation();
    });
});
