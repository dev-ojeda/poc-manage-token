// js/auth.js
import { ApiUser } from "../js/api/ApiUser.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { IndexedDBStorage } from "../js/adapters/IndexedDBStorage.js";
import { clearSession, handleError } from "../js/utils/errors.js";

// =======================
// Configuración
// =======================
const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
const storage = new IndexedDBStorage("AuthDB", "tokens");

const api = {
    user: new ApiUser({ baseURL: API_BASE, storage }),
    admin: new ApiAdmin({ baseURL: API_BASE, storage }),
};

// =======================
// Helpers
// =======================
async function doLogin(username, password) {
    return username.includes("admin")
        ? api.admin.login(username, password)
        : api.user.login(username, password);
}

async function redirectToDashboard(role) {
    if (role === "Admin") {
        window.location.href = "/admin/dashboard";
    } else {
        window.location.href = "/dashboard";
    }
}
// =======================
// Inicialización
// =======================
document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);

    // Logout explícito
    if (params.has("logged_out")) {
        await clearSession();
        history.replaceState(null, "", window.location.pathname);
        location.href = "/";
        return;
    }

    // Cache back-forward nav (Safari/Firefox)
    window.addEventListener("pageshow", async (event) => {
        if (event.persisted) {
            await clearSession();
            location.href = "/";
        }
    });

    // Login form
    const form = document.getElementById("loginForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const username = String(form.username.value.trim());
        const password = form.password.value;

        try {
            const res = await doLogin(username, password);
            if (!res) return;

            // Redirección automática según rol
            await redirectToDashboard(res.rol || "User");

        } catch (err) {
            handleError(err);
        }
    });
});
