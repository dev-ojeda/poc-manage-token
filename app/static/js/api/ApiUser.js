import { ApiClient } from "../api/ApiClient.js";
import { handleError } from "../utils/errors.js";

/**
 * Clase que contiene los métodos necesarios
 * para el acceso del Usuario
 */
export class ApiUser extends ApiClient {
    constructor(opts) {
        super({
            baseURL: opts.baseURL,
            storage: opts.storage,
            timeout: opts.timeout || 10000
        });
        this.isRefreshing = false;   // lock
        this.refreshQueue = [];      // cola de promesas
    }

    /**
     * Login de usuario
     */
    async login(username, password) {
        try {
            const device = await this.getDeviceId();
            const user_agent = this.getBrowserInfo();

            const res = await this.post("/api/auth/acceso", {
                username,
                password,
                device,
                rol: "User",
                user_agent
            });

            if (res?.access_token && res?.refresh_token) {
                await this.setTokens(res);
            }
            return res;
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    // =============================
    // Logout Unificado con broadcast
    // =============================
    async logout({ reason = "logout" } = {}) {
        try {
            // 🔹 Primero obtengo los tokens ANTES de limpiar
            let access_token = await this.accessToken();
            let refresh_token = await this.refreshToken();
            let device_id = await this.deviceId();
            let user_agent = this.getBrowserInfo();

            if (!access_token && !refresh_token) {
                throw new Error("Token no existe");
            }

            // 🔄 Aviso al backend con keepalive
            const res = await this.post("/api/auth/logout", {
                access_token,
                refresh_token,
                device_id,
                user_agent,
                reason
            }); // 🔹 útil si cerrás pestaña rápido

            // 🔹 Aviso al usuario
            this.notifier?.(`👋 ${res.msg}`, "info", 4000);

        } catch (err) {
            await handleError(err);
        } finally {
            // 🔹 Redirigir al login
            //window.location.href = "/?logout=true";
            location.replace("/?logged_out=1");
        }
    }

    /**
     * Fetch con token + reintento en caso de expiración
     */
    async fetchWithAuth(url, options = {}) {
        let access_token = await this.storage.get("access_token");

        const baseHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${access_token}`,
            "X-Token-Type": "access"
        };

        let res = await fetch(url, {
            ...options,
            headers: { ...baseHeaders, ...(options.headers || {}) }
        });

        // Si expiró el access_token
        if (res.status === 401) {
            await this.tryRefreshToken();
            access_token = await this.storage.get("access_token");

            res = await fetch(url, {
                ...options,
                headers: {
                    ...baseHeaders,
                    "Authorization": `Bearer ${access_token}`
                }
            });
        }

        return res;
    }

    /**
     * Refresh de token con lock para evitar condiciones de carrera
     */
    async tryRefreshToken() {
        if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
                this.refreshQueue.push({ resolve, reject });
            });
        }

        this.isRefreshing = true;

        try {
            const refresh_token = await this.refreshToken();
            if (!refresh_token) throw new Error("No hay refresh_token disponible");

            const device_id = await this.deviceId();
            const user_agent = this.getBrowserInfo();

            const res = await this.post("/api/auth/refresh", {
                refresh_token,
                device_id,
                user_agent
            });

            if (res?.access_token) {
                await this.setTokens(res);

                // Notificar a los listeners (ej: main/user.js) del nuevo exp
                const decoded = this.decodeJwt(res.access_token);
                document.dispatchEvent(new CustomEvent("startTokenTimer", {
                    detail: { new_expiracion: decoded.exp }
                }));

                this.refreshQueue.forEach(p => p.resolve(res));
                this.refreshQueue = [];
            }

            return res;
        } catch (err) {
            this.refreshQueue.forEach(p => p.reject(err));
            this.refreshQueue = [];
            await handleError(err);
            throw err;
        } finally {
            this.isRefreshing = false;
        }
    }

    decodeJwt(token) {
        try {
            return JSON.parse(atob(token.split(".")[1]));
        } catch {
            return {};
        }
    }

    /**
     * Guarda access_token y refresh_token en storage
     */
    async setTokens(res) {
        if (res?.access_token) {
            await this.storage.set("access_token", res.access_token);
        }
        if (res?.refresh_token) {
            await this.storage.set("refresh_token", res.refresh_token);
        }
    }

    async loadItems() {
        try {
            return await this.get("/api/auth/user/items", {});
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    async createItem(data = {}) {
        try {
            const res = await this.post("/api/auth/user/items", data);
            this.notifier?.(`✅ ${res.msg}`, "sucess", 4000);
        } catch (err) {
            await handleError(err);
            return null;
        }
    }
    async updateItem(api, id, data) {
        try {
            await api.put(`/api/user/items/${id}`, data);
            await this.loadItems();
        } catch (err) {
            await handleError(err);
            return null;
        }
    }
    async deleteItem(id) {
        try {
            await this.delete(`/api/user/items/${id}`);
            await this.loadItems();
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

}
