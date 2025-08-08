import { ApiUser } from "./api/ApiUser.js";
import { ApiAdmin } from "./api/ApiAdmin.js";
import { LocalStorageAdapter } from "./adapters/LocalStorageAdapter.js";
import { handleError } from "./utils/errors.js";
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
        ;
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
        const user = document.getElementById("username").value.trim();
        const pass = document.getElementById("password").value;

        try {
            let success = false;
            let role = "user";
            if (user.includes("admin")) {
                success = await api_admin.login_admin(user, pass);
                role = "Admin";
            } else {
                success = await api_user.login(user, pass);
            }

            if (success) {
                const dashboardValid = role === "Admin"
                    ? await api_admin.admin_dashboard()
                    : await api_user.user_dashboard();

                if (dashboardValid) {
                    location.href = role === "Admin" ? "/admin/dashboard" : "/dashboard";
                }
            }
        } catch (err) {
            throw new Error("Error al iniciar sesión");
            handleError(err);
        }
        e.stopPropagation();
    });
});
