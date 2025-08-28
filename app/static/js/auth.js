import { ApiUser } from "../js/api/ApiUser.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { IndexedDBStorage } from "../js/adapters/IndexedDBStorage.js";
import { clearSession, handleError } from "../js/utils/errors.js"
// =======================
// Instancias API
// =======================
// =======================
// Configuración global
// =======================
const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");

// Instancias API
const api = {
    user: new ApiUser({ baseURL: API_BASE, storage }),
    admin: new ApiAdmin({ baseURL: API_BASE, storage }),
};

// =======================
// Helpers
// =======================
async function doLogin(username, password) {
    const isAdmin = username.includes("admin");
    return isAdmin
        ? api.admin.login_admin(username, password)
        : api.user.login(username, password);
}
//async function fetchDashboard(username) {
//    const isAdmin = username.includes("admin");
//    return isAdmin
//        ? api.admin.getDashboard()
//        : api.user.getDashboard();
//}

function redirectByRole(role) {
    location.replace(role === "Admin" ? "/admin/dashboard" : "/dashboard");
}

// =======================
// Inicialización
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);

    // ✅ Logout explícito
    if (params.has("logged_out")) {
        await clearSession();
        history.replaceState(null, "", window.location.pathname);
        window.location.href = "/";
        return;
    }
    // ✅ Cache back-forward nav (Safari/Firefox)
    window.addEventListener("pageshow", async (event) => {
        if (event.persisted) {
            await clearSession();
            window.location.href = "/";
        }
    });
    // =======================
    // Login form
    // =======================
    const form = document.getElementById("loginForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
  
            const username = String(document.getElementById("username").value.trim());
            const password = document.getElementById("password").value;

            // 🔑 Login
            const res = await doLogin(username, password);
            if (!res) return;

            // 📊 Dashboard
            //const dashboard = await fetchDashboard(username);
            //console.log("DASHBOARD", dashboard);

            //if (!dashboard) return;

            // 🔥 Redirección según rol
            redirectByRole(res.rol || "User");

        } catch (err) {
            await handleError(err);
            throw err;
        }
        e.stopPropagation();
    });
});
