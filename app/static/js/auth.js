import { ApiUser } from "./api/ApiUser.js";
import { ApiAdmin } from "./api/ApiAdmin.js";
import { LocalStorageAdapter } from "./adapters/LocalStorageAdapter.js";
const api_user = new ApiUser({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});


document.addEventListener("DOMContentLoaded", () => {
 
    const params = new URLSearchParams(window.location.search);
    if (params.has("logged_out")) {
        localStorage.clear();
        history.replaceState(null, "", window.location.pathname);
        // Redirigir explícitamente a la raíz del SPA
        window.location.href = "/";
    }

    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            //window.location.href = "/";
            window.location.reload();
        }
    });
    document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user = document.getElementById("username").value;
        const pass = document.getElementById("password").value;

        if (user.includes("admin")) {
            const success = await api_admin.login_admin(user, pass);
            if (success) {
                const validar = await api_admin.admin_dashboard();
                if (validar) {
                    location.href = "/admin/dashboard";
                }
            }
        }
        else {
            const success = await api_user.login(user, pass);
            if (success) {
                const validar = await api_user.user_dashboard();
                if (validar) {

                    location.href = "/dashboard";
                }
            }
        }
       
    });
});
