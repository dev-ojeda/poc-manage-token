// js/auth.js
import { ApiUser } from "../js/api/ApiUser.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { IndexedDBStorage } from "../js/adapters/IndexedDBStorage.js";
import { clearSession, handleError } from "../js/utils/errors.js"
// =======================
// Instancias API
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
        ? api.admin.login(username, password)
        : api.user.login(username, password);
}

function redirectByRole(role) {
    switch (role) {
        case "Admin":
            location.replace("/admin/dashboard");
            break;
        case "User":
        default:
            location.replace("/dashboard");
            break;
    }
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
  
        const username = String(form.username.value.trim());
        const password = form.password.value;
        try {
            const res = await doLogin(username, password);
            if (!res) return;

            // 🚀 Ahora rediriges con lo que diga el backend
            redirectByRole(res.rol || "User");

        } catch (err) {
            handleError(err);
        }

    });
});
