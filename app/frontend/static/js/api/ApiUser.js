import { ApiClient } from "../api/ApiClient.js";
import { handleError } from "../utils/errors.js";

export class ApiUser extends ApiClient {
    constructor(opts) {
        super({
            baseURL: opts.baseURL,
            storage: opts.storage,
            timeout: opts.timeout || 10000,
            debugEnabled: opts.debugEnabled || false
        });

        this.isRefreshing = false;
        this.refreshQueue = [];
        this.routes = {
            login: "/api/user/acceso",
            refresh: "/api/user/refresh",
            dashboard: "/api/user/dashboard",
            items: "/api/user/items"
        };
        // 🔹 Asegura que el almacenamiento esté listo
        this.storage._init().catch(err => this._log("warn", "INIT", "IndexedDB no inicializado:", err));
    }

    // =========================================================
    // 🔹 LOGIN
    // =========================================================
    async login(username, password) {
        return this._wrap(async () => {
            await this.storage._init();
            const [device, user_agent] = [await this.getDeviceId(), this.getBrowserInfo()];

            const res = await this.fetchJson(this.routes.login, {
                method: "POST",
                body: JSON.stringify({ username, password, device, rol: "User", user_agent }),
            });

            if (res?.access_token && res?.refresh_token) {
                await this.setTokens(res);
                this._log("success", "LOGIN", "Token de usuario establecido correctamente");
            }

            this._log("debug", "LOGIN", "Token (mask):", res?.access_token?.slice(0, 12) + "...");
            return res;
        }, "LOGIN");
    }

    // =========================================================
    // 🔹 INFO USUARIO
    // =========================================================
    async loadInfoUser() {
        return this._wrap(() => this.fetchJson(this.routes.dashboard), "loadInfoUser");
    }

    // =========================================================
    // 🔹 TOKEN REFRESH (con cola)
    // =========================================================
    async tryRefreshToken() {
        if (this.isRefreshing)
            return new Promise((resolve, reject) => this.refreshQueue.push({ resolve, reject }));

        this.isRefreshing = true;
        this._log("info", "REFRESH", "Intentando renovar token de sesión...");

        return this._wrap(async () => {
            const refresh_token = await this.refreshToken("user");
            if (!refresh_token) throw new Error("No hay refresh_token disponible");

            const [device_id, user_agent] = [await this.getDeviceId(), this.getBrowserInfo()];
            const res = await this.fetchJson(this.routes.refresh, {
                method: "POST",
                body: JSON.stringify({ refresh_token, device_id, user_agent }),
            });

            if (res?.access_token) {
                await this.setTokens(res);
                const decoded = this.decodeJwt(res.access_token);

                document.dispatchEvent(new CustomEvent("startTokenTimer", {
                    detail: { new_expiracion: decoded.exp }
                }));
                document.dispatchEvent(new CustomEvent("cache:clear"));

                this.refreshQueue.forEach(p => p.resolve(res));
                this.refreshQueue = [];

                this._log("success", "REFRESH", "Token actualizado correctamente");
            }

            return res;
        }, "REFRESH", true);
    }

    // =========================================================
    // 🔹 TOKEN PROACTIVO
    // =========================================================
    async accessTokenUser() {
        const token = await this.accessToken("user");
        const decoded = this.decodeJwt(token);

        if (decoded.exp * 1000 < Date.now() + 30000) {
            this._log("warn", "TOKEN", "Expira pronto, iniciando refresh proactivo...");
            await this.tryRefreshToken();
            return await this.accessToken("user");
        }
        return token;
    }

    decodeJwt(token) {
        try {
            return JSON.parse(atob(token.split(".")[1]));
        } catch {
            return {};
        }
    }

    // =========================================================
    // 🔹 CRUD DE ITEMS
    // =========================================================
    async loadItems() {
        return this._wrap(() => this.fetchJson(this.routes.items), "loadItems");
    }

    async createItem(data = {}) {
        return this._wrap(async () => {
            const res = await this.fetchJson(this.routes.items, {
                method: "POST",
                body: JSON.stringify(data),
            });
            this._log("success", "ITEM", res.msg || "Item creado");
            return res;
        }, "createItem");
    }

    async updateItem(id, data) {
        return this._wrap(async () => {
            await this.fetchJson(`${this.routes.items}/${id}`, {
                method: "PUT",
                body: JSON.stringify(data),
            });
            return this.loadItems();
        }, "updateItem");
    }

    async deleteItem(id) {
        return this._wrap(async () => {
            await this.fetchJson(`${this.routes.items}/${id}`, { method: "DELETE" });
            return this.loadItems();
        }, "deleteItem");
    }

    // =========================================================
    // 🔹 DASHBOARD PARCIAL
    // =========================================================
    async loadDashboard(view = "panel") {
        const container = document.getElementById("mainContent");
        if (!container) return;
        return this._wrap(async () => {
            const html = await this.fetchHtml(`/user/partial?view=${view}`);
            container.innerHTML = html;
            this._log("debug", "DASHBOARD", `Cargado: ${view}`);
        }, "DASHBOARD");
    }

    // =========================================================
    // 🔹 WRAPPER GENÉRICO PARA ERRORES Y LOGS
    // =========================================================
    async _wrap(fn, label, isRefresh = false) {
        try {
            const result = await fn();
            return result;
        } catch (err) {
            await handleError(err);
            this._log("error", label, err);
            if (isRefresh) this.refreshQueue.forEach(p => p.reject(err));
            return null;
        } finally {
            if (isRefresh) {
                this.refreshQueue.forEach(p => p.reject(err || new Error("Refresh cancelado")));
                this.refreshQueue = [];
                this.isRefreshing = false;
            }
        }
    }

    // =========================================================
    // 🔹 LOGGING ESTRUCTURADO UNIFICADO
    // =========================================================
    _log(level = "info", label = "", ...args) {
        if (!this.debugEnabled) return;
        const icons = { info: "ℹ️", warn: "⚠️", error: "💥", success: "✅", debug: "🧠" };
        const styles = {
            info: "color:#0dcaf0;font-weight:bold;",
            warn: "color:#ffc107;font-weight:bold;",
            error: "color:#dc3545;font-weight:bold;",
            success: "color:#28a745;font-weight:bold;",
            debug: "color:#6f42c1;font-weight:bold;"
        };
        const time = new Date().toLocaleTimeString();
        console.groupCollapsed(
            `%c${icons[level] || "🔹"} [${level.toUpperCase()} ${time}] ${label}`,
            styles[level] || styles.info
        );
        console.log(...args);
        console.groupEnd();
    }
}
