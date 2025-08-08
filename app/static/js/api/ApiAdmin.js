// ApiClient.js
import { showAlert } from "../layout.js";
import { handleError } from "../utils/errors.js";
export class ApiAdmin {
    constructor(params = {}) {
        const { baseURL, storage, timeout = 8000, retries = 2, retryDelay = 1000 } = params;
        this.baseURL = baseURL;
        this.storage = storage;
        this.timeout = timeout;
        this.retries = retries;
        this.retryDelay = retryDelay;
    }

    get accessToken() {
        return this.storage.get("access_token");
    }

    get accessTokenAdmin() {
        return this.storage.get("access_token");
    }

    get refreshToken() {
        return this.storage.get("refresh_token");
    }

    get deviceId() {
        return this.storage.get("device_id");
    }

    get userRol() {
        return this.storage.get("rol");
    }

    get userName() {
        return this.storage.get("username");
    }

    get tokenExp() {
        return this.storage.get("exp");
    }
    get userAgent() {
        return this.storage.get("user_agent");
    }

    get userJti() {
        return this.storage.get("jti");
    }


    async fetchWithTimeout(resource, options = {}) {
        const controller = new AbortController();
        const timeout = options.timeout ?? this.timeout ?? 8000;
        const id = setTimeout(() => controller.abort(), timeout);

        const opts = {
            ...options,
            signal: controller.signal
        };

        try {
            const response = await fetch(resource, opts);
            return response;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error(`⏱️ La solicitud a ${resource} fue abortada por timeout (${timeout}ms)`);
            }
            throw error;
            handleError(error);
        } finally {
            clearTimeout(id);
        }
    }

    async fetch(endpoint, options = {}, retries = this.retries, retryDelay = this.retryDelay) {
        const headers = {
            "Content-Type": "application/json",
            ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}`, "X-Token-Type": "access" }),
            ...options.headers
        };
        try {
            const response = await this.fetchWithTimeout(`${this.baseURL}${endpoint}`, {
                ...options,
                headers
            });
            const contentType = response.headers.get("Content-Type") || "";
            const data = contentType.includes("application/json")
                ? await response.json()
                : await response.text();
    
            if (response.status === 403 || response.status === 400) {
                const errorMsg = response.status === 403
                    ? `🚫 Bloqueado: ${data.msg} hasta ${data.bloqueado_hasta}`
                    : `🚫 ${data.code}`;
                throw new Error(errorMsg);
            }
            // Si el token expiró y hay refresh token disponible
            if (response.status === 401 && this.refreshToken) {
                throw new Error(`Error ${data.msg} ${data.code}`);
            }

            // Otros errores
            if (!response.ok) {
                throw new Error(`Error ${data.msg} ${data.code}`);
            }

            // ✅ Ya no se vuelve a leer el body aquí
            return data;
        } catch (err) {
            if (retries > 0) {
                showAlert(`🔁 Reintentando ${retries}...`, "warning");
                await this.delay(retryDelay);
                return this.fetch(endpoint, options, retries - 1, retryDelay * 2);
            }

            handleError(err);
            throw err;
        }
    }

    delay(ms) {
        return new Promise(res => setTimeout(res, ms));
    }

    setTokens({ access_token, refresh_token }) {
        this.storage.setItem("access_token", access_token);
        this.storage.setItem("refresh_token", refresh_token);
    }

    async getToken() {
        const token = await this.storage.get("access_token");
        if (!token) throw new Error("Token no encontrado");
        return token;
    }
    async getRefreshToken() {
        const token = await this.storage.get("refresh_token");
        if (!token) throw new Error("Token no encontrado");
        return token;
    }
    getDeviceId() {
        let device_id = crypto.randomUUID();
        this.storage.set("device_id", device_id);
        return device_id;
    }

    getUserRol() {
        return this.storage.get("rol");
    }

    getTokenExp() {
        let rol = this.storage.get("exp");
        return rol;
    }

    getUserName() {
        let user = this.storage.get("username");
        return user;
    }

    getUserJti() {
        return this.userJti;
    }

    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = "Desconocido";

        if (ua.includes("Chrome") && !ua.includes("Edg")) browser = "Chrome";
        else if (ua.includes("Firefox")) browser = "Firefox";
        else if (ua.includes("Safari") && !ua.includes("Chrome")) browser = "Safari";
        else if (ua.includes("Edg")) browser = "Edge";
        else if (ua.includes("OPR") || ua.includes("Opera")) browser = "Opera";

        let os = "Desconocido";
        if (ua.includes("Windows")) os = "Windows";
        else if (ua.includes("Mac OS")) os = "MacOS";
        else if (ua.includes("Linux")) os = "Linux";
        else if (/Android/.test(ua)) os = "Android";
        else if (/iPhone|iPad|iPod/.test(ua)) os = "iOS";

        return { browser, os };
    }

    getUserAgent() {
        this.storage.set("user_agent", navigator.userAgent);
        return navigator.userAgent;
    }

   
    async login_admin(username, password) {
        try {
            const device = this.getDeviceId();
            const user_agent = this.getBrowserInfo();
            const res = await this.post("/api/auth/admin", { username, password, device, user_agent, rol: "Admin" });
            const { access_token, refresh_token, device_id, rol } = res;

            this.storage.set("access_token", access_token);
            this.storage.set("refresh_token", refresh_token);
            this.storage.set("device_id", device_id);
            this.storage.set("username", username);
            this.storage.set("rol", rol || "User");

            return true;
        } catch (err) {
            handleError(err);
            return false;
        }
    }

    async admin_dashboard() {
        try {
            if (this.deviceId) {
                const res = await this.get("/api/auth/admin/dashboard", {});
                const { username, rol, device_id, exp, jti } = res;
                const now = Math.floor(Date.now() / 1000);
                if (exp && now > exp) {
                    throw new Error("⏰ Token expirado del lado del cliente");
                }
                this.storage.set("username", username);
                this.storage.set("rol", rol);
                this.storage.set("device_id", device_id);
                this.storage.set("exp", exp);
                this.storage.set("jti", jti);
                return true;
            }
            else {
                throw new Error("Token no existe y Device!!!");
            }

        } catch (err) {
            handleError(err);
            return false;
        }
    }

    async logout_admin() {
        showAlert(`👋 Admin ha cerrado sesión`, "info", 4000);
        this.clearSession(); // tokens, flags, device_id, etc.
        window.history.replaceState({}, document.title, window.location.pathname);
        location.href = "/";
        
    }
    async get(endpoint, options = {}) {
        return this.fetch(endpoint, { ...options, method: "GET" });
    }

    async post(endpoint, body = {}, options = {}) {
        return this.fetch(endpoint, {
            ...options,
            method: "POST",
            body: JSON.stringify(body)
        });
    }

    async put(endpoint, body = {}, options = {}) {
        return this.fetch(endpoint, {
            ...options,
            method: "PUT",
            body: JSON.stringify(body)
        });
    }

    async delete(endpoint, options = {}) {
        return this.fetch(endpoint, { ...options, method: "DELETE" });
    }
}
