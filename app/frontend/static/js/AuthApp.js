// AuthApp.js – versión refactorizada y optimizada
import { ApiUser } from "../js/api/ApiUser.js";
import { ApiAdmin } from "../js/api/ApiAdmin.js";
import { IndexedDBStorage } from "../js/adapters/IndexedDBStorage.js";
import { showGlobalAlert, GLOBAL_DEBUG } from "../js/layout.js";
import { validateForm, decodeJwt } from "../js/utils/helper.js";

export class AuthApp {
    constructor() {
        this.API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
        this.DEBUG = import.meta.env?.VITE_DEBUG_MODE === "true";
        this.storage = new IndexedDBStorage("AuthDB", "tokens");

        const opts = { baseURL: this.API_BASE, storage: this.storage, debugEnabled: GLOBAL_DEBUG };
        this.api_admin = new ApiAdmin(opts);
        this.api_user = new ApiUser(opts);

        this.sessionCache = null;
        this.tokenTimeout = null;
        this.refreshInProgress = false;
        this.debugEnabled = GLOBAL_DEBUG;
        this._initialized = false;
    }

    async init() {
        if (this._initialized) return;
        this._initialized = true;

        try {
            await this.storage._init();
            await this._waitForCSS();
            document.body.classList.remove("invisible");
            this._log("debug", "AuthApp inicializado", { API_BASE: this.API_BASE });
            this._initLoginForm();
        } catch (err) {
            console.error("❌ Error en init:", err);
            showGlobalAlert("Error inesperado. Intenta nuevamente.", "danger", 5000);
        }
    }

    async _waitForCSS() {
        const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
        await Promise.all(links.map(link => link.sheet ? Promise.resolve() : new Promise(res => link.onload = res)));
    }

    async _checkStoredTokens() {
        const [adminToken, userToken] = await Promise.all([
            this.api_admin.accessToken("admin"),
            this.api_user.accessToken("user")
        ]);

        if (adminToken && userToken) {
            this._log("warn", "Tokens duplicados detectados → limpiando");
            await this.storage.clear();
            return { exists: false, rol: null };
        }

        const now = Date.now();
        const decodedAdmin = decodeJwt(adminToken);
        const decodedUser = decodeJwt(userToken);

        if (adminToken && decodedAdmin?.exp * 1000 > now)
            return { exists: true, rol: "admin", exp: decodedAdmin.exp };

        if (userToken && decodedUser?.exp * 1000 > now)
            return { exists: true, rol: "user", exp: decodedUser.exp };

        return { exists: false, rol: null };
    }

    async checkSession() {
        for (const role of ["admin", "user"]) {
            const token = await this.storage.get(`access_token_${role}`);
            if (!token?.value) continue;

            const decoded = decodeJwt(token.value);
            if (decoded?.exp * 1000 > Date.now()) {
                this.sessionCache = { username: decoded.sub, rol: role, exp: decoded.exp };
                this._emitSessionChange(true, role);
                return true;
            }
        }
        return false;
    }

    _emitSessionChange(loggedIn, role) {
        document.dispatchEvent(new CustomEvent("session:change", { detail: { loggedIn, role } }));
    }

    scheduleNextTokenCheck() {
        clearTimeout(this.tokenTimeout);

        const role = this.sessionCache?.rol;
        if (!role) return;

        this.storage.get(`access_token_${role}`).then(entry => {
            if (!entry?.value) return;

            const decoded = decodeJwt(entry.value);
            const remaining = decoded.exp * 1000 - Date.now();
            const checkIn = Math.max(remaining - 60000, 10000);

            this._log("debug", `⌛ Próximo check de token ${role} en ${(checkIn / 1000).toFixed(1)}s`);
            this.tokenTimeout = setTimeout(() => this._checkAndRefreshToken(role), checkIn);
        });
    }

    async _checkAndRefreshToken(role) {
        if (this.refreshInProgress) return;

        const tokenEntry = await this.storage.get(`access_token_${role}`);
        if (!tokenEntry?.value) return;

        const decoded = decodeJwt(tokenEntry.value);
        const remaining = decoded.exp * 1000 - Date.now();

        if (remaining <= 0) {
            await this.apiLogout(role);
            this.redirectToLogin("⚠️ Tu sesión expiró. Iniciá sesión nuevamente.");
            return;
        }

        if (remaining < 60000) await this.refreshSession(role);
        this.scheduleNextTokenCheck();
    }

    async refreshSession(role) {
        if (localStorage.getItem("refreshLock") === "true") return;
        localStorage.setItem("refreshLock", "true");

        try {
            this.refreshInProgress = true;
            this._log("debug", `♻️ Intentando refresh de token (${role})`);

            const api = role === "admin" ? this.api_admin : this.api_user;
            const res = await api.tryRefreshToken();

            if (!res?.access_token) throw new Error("Refresh sin token válido");

            await this.storage.set(`access_token_${role}`, { value: res.access_token });
            const decoded = decodeJwt(res.access_token);
            this.sessionCache.exp = decoded.exp;

            this._log("success", "Token renovado", decoded);
        } catch (err) {
            console.error("Error refrescando token:", err);
            await this.apiLogout(role);
            this.redirectToLogin("🚫 Sesión caducada o inválida.");
        } finally {
            localStorage.removeItem("refreshLock");
            this.refreshInProgress = false;
        }
    }

    _initLoginForm() {
        const form = document.getElementById("loginForm");
        const btn = document.getElementById("loginBtn");
        const msg = document.getElementById("loginStatusMsg");
        if (!form || !btn || !msg) return;

        form.addEventListener("submit", async e => {
            e.preventDefault();
            if (!validateForm(form)) return showGlobalAlert("Completa todos los campos.", "warning", 3000);

            btn.classList.add("loading");
            msg.textContent = "Validando credenciales...";
            msg.className = "login-status active loading";

            try {
                const username = form.username.value.trim();
                const password = form.password.value;
                const data = await this.doLogin(username, password);
                const rol = (data?.rol || "user").toLowerCase();
                const decoded = decodeJwt(data.access_token);

                this.sessionCache = { rol, username, exp: decoded.exp };
                showGlobalAlert("✅ Bienvenido, redirigiendo...", "success", 1500);
                setTimeout(() => this.redirectByRole(rol), 1200);
            } catch (err) {
                this._log("error", "Login", err);
                showGlobalAlert("Credenciales inválidas o error de red.", "danger", 5000);
            } finally {
                btn.classList.remove("loading");
                setTimeout(() => msg.classList.remove("active"), 3000);
            }
        });
    }

    async doLogin(username, password) {
        const api = username.includes("admin") ? this.api_admin : this.api_user;
        return api.login(username, password);
    }

    async apiLogout(role) {
        const api = role === "admin" ? this.api_admin : this.api_user;
        try {
            const res = await api.fetchJson("/api/user/logout", {
                method: "POST",
                body: JSON.stringify({
                    device_id: navigator.userAgentData?.platform || "unknown",
                    user_agent: navigator.userAgent,
                    reason: "manual_logout"
                })
            });
            api.notifier?.(`👋 ${res?.msg || "Sesión finalizada"}`, "info", 4000);
        } catch (err) {
            this._log("warn", "Error al cerrar sesión", err);
        }

        await this.storage.clear();
        this.sessionCache = null;
        this._emitSessionChange(false, role);
        this._log("info", `Sesión ${role} cerrada`);
    }

    redirectByRole(role) {
        const routes = { admin: "/admin/dashboard", user: "/user/dashboard" };
        this._emitSessionChange(true, role);
        globalThis.location.href = routes[role] || "/";
    }

    redirectToLogin(msg) {
        if (msg) showGlobalAlert(msg, "danger", 5000);
        if (globalThis.location.pathname !== "/")
            globalThis.location.replace("/?logout=true");
    }

    _log(level = "info", label = "", ...args) {
        if (!this.debugEnabled) return;
        const time = new Date().toLocaleTimeString();
        const styles = {
            info: "color:#0dcaf0;font-weight:bold;",
            warn: "color:#ffc107;font-weight:bold;",
            error: "color:#dc3545;font-weight:bold;",
            success: "color:#28a745;font-weight:bold;",
            debug: "color:#6f42c1;font-weight:bold;"
        };
        const icons = { info: "ℹ️", warn: "⚠️", error: "💥", success: "✅", debug: "🧠" };
        console.groupCollapsed(`%c${icons[level] || "🔹"} [${level.toUpperCase()} ${time}] ${label}`, styles[level] || styles.info);
        console.log(...args);
        console.groupEnd();
        document.dispatchEvent(new CustomEvent("debug:log", { detail: { level, label, args } }));
    }
}

document.addEventListener("DOMContentLoaded", () => {
    globalThis.AuthAppInstance ||= new AuthApp();
    globalThis.AuthAppInstance.init();

    const userNameEl = document.getElementById("userName");
    const logoutBtn = document.getElementById("logoutBtn");

    document.addEventListener("session:change", async e => {
        const { loggedIn, role } = e.detail;
        const storage = globalThis.AuthAppInstance.storage;

        if (loggedIn) {
            const token = await storage.get(`access_token_${role}`);
            const decoded = token?.value ? decodeJwt(token.value) : null;
            if (userNameEl) userNameEl.textContent = decoded?.sub || "Usuario";
        } else if (userNameEl) {
            userNameEl.textContent = "";
        }
    });

    logoutBtn?.addEventListener("click", async () => {
        const role = globalThis.AuthAppInstance?.sessionCache?.rol;
        await globalThis.AuthAppInstance.apiLogout(role);
        globalThis.AuthAppInstance.redirectToLogin("👋 Sesión cerrada correctamente.");
    });
});
