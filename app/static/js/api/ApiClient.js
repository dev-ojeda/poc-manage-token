import { showAlert } from "../layout.js";
import { handleError, clearSession } from "../utils/errors.js";

export class ApiClient {
    constructor(params = {}) {
        const {
            baseURL,
            storage,
            timeout = 8000,
            retries = 2,
            retryDelay = 1000,
        } = params;
        this.baseURL = baseURL;
        this.storage = storage;
        this.timeout = timeout;
        this.retries = retries;
        this.retryDelay = retryDelay;
    }

  

    get accessToken() {
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

    get userJti() {
        return this.storage.get("jti");
    }

    getDeviceId() {
        let device = this.storage.get("device_id");
        if (!device) {
            device = crypto.randomUUID();
            this.storage.set("device_id", device);
        }
        return device;
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

    async fetchWithTimeout(resource, options = {}) {
        const controller = new AbortController();
        const timeout = options.timeout ?? this.timeout;
        const id = setTimeout(() => controller.abort(), timeout);

        const opts = {
            ...options,
            signal: controller.signal,
        };

        try {
            const response = await fetch(resource, opts);
            return response;
        } catch (error) {
            if (error.name === "AbortError") {
                throw new Error(
                    `⏱️ La solicitud a ${resource} fue abortada por timeout (${timeout}ms)`
                );
            }
            throw error;
        } finally {
            clearTimeout(id);
        }
    }

    async fetch(endpoint, options = {}, retries = this.retries, retryDelay = this.retryDelay) {
        const headers = {
            "Content-Type": "application/json",
            ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}`, "X-Token-Type": "access" } : {}),
            ...options.headers,
        };

        try {
            const response = await this.fetchWithTimeout(`${this.baseURL}${endpoint}`, {
                ...options,
                headers,
            });

            const contentType = response.headers.get("Content-Type") || "";
            const data = contentType.includes("application/json")
                ? await response.json()
                : await response.text();

            if ([400, 403].includes(response.status)) {
                const errorMsg =
                    response.status === 403
                        ? `🚫 Bloqueado: ${data.msg} hasta ${data.bloqueado_hasta}`
                        : `🚫 ${data.code}`;
                throw new Error(errorMsg);
            }

            if (response.status === 401 && this.refreshToken) {
                throw new Error(`401 Unauthorized: ${data.msg} ${data.code}`);
            }

            if (!response.ok) {
                throw new Error(`Error ${data.msg || "desconocido"} ${data.code || ""}`);
            }

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
        return new Promise((res) => setTimeout(res, ms));
    }

    setTokens({ access_token, refresh_token }) {
        this.storage.set("access_token", access_token);
        this.storage.set("refresh_token", refresh_token);
    }

    async getRefreshToken() {
        const token = this.storage.get("refresh_token");
        if (!token) throw new Error("Token no encontrado");
        return token;
    }

    async logout_admin() {
        showAlert(`👋 Admin ha cerrado sesión`, "info", 4000);
        clearSession(); // tokens, flags, device_id, etc.
        window.history.replaceState({}, document.title, window.location.pathname);
        location.href = "/";

    }

    async logout(reason = "logout") {
        try {
            const access_token = this.accessToken;
            const refresh_token = this.refreshToken;
            const device_id = this.deviceId;

            if (!access_token) throw new Error("Token no existe");

            const res = await fetch(`${this.baseURL}/api/auth/logout`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${refresh_token || ""}`,
                    "Content-Type": "application/json",
                    "X-Token-Type": "refresh",
                },
                body: JSON.stringify({ access_token, refresh_token, device_id, reason }),
            });

            const data = await res.json();

            if (!res.ok) throw new Error(data.msg || "Error al cerrar sesión");

            showAlert(`👋 ${data.msg}`, "info", 4000);
        } catch (err) {
            handleError(err);
            console.warn("Logout error:", err);
        } finally {
            clearSession();
            window.history.replaceState({}, document.title, window.location.pathname);
            location.href = "/";
        }
    }

    // Métodos HTTP base
    async get(endpoint, options = {}) {
        return this.fetch(endpoint, { ...options, method: "GET" });
    }

    async post(endpoint, body = {}, options = {}) {
        return this.fetch(endpoint, {
            ...options,
            method: "POST",
            body: JSON.stringify(body),
        });
    }

    async put(endpoint, body = {}, options = {}) {
        return this.fetch(endpoint, {
            ...options,
            method: "PUT",
            body: JSON.stringify(body),
        });
    }

    async delete(endpoint, options = {}) {
        return this.fetch(endpoint, { ...options, method: "DELETE" });
    }
}
