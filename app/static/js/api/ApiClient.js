import { showAlert } from "../layout.js";
import { handleError } from "../utils/errors.js";

/**
 * Clase base que contien los metodos necesarios de acceso y salida.
 */
export class ApiClient {
    constructor({ baseURL, storage, timeout = 10000, notifier = showAlert }) {
        this.baseURL = baseURL;
        this.storage = storage;
        this.timeout = timeout;
        this.notifier = notifier;
    }

    // =============================
    // Tokens & Metadata
    // =============================
    async safeGet(key) {
        try {
            return await this.storage.get(key);
        } catch (err) {
            console.error(`Error leyendo ${key}:`, err);
            return null;
        }
    }
    async accessToken() { return await this.safeGet("access_token"); }
    async refreshToken() { return await this.safeGet("refresh_token"); }
    async deviceId() { return await this.safeGet("device_id"); }
    async userRol() { return await this.safeGet("rol"); }
    async userName() { return await this.safeGet("username"); }
    async tokenExp() { return await this.safeGet("exp"); }
    async userJti() { return await this.safeGet("jti"); }

    setTokens({ access_token, refresh_token }) {
        this.storage.set("access_token", access_token);
        this.storage.set("refresh_token", refresh_token);
    }

    async clearTokens() {
        await this.storage.clear();
    }

    async getDeviceId() {
        let device = await this.safeGet("device_id");
        if (!device) {
            device = crypto.randomUUID();
            await this.storage.set("device_id", device);
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


    // =============================
    // Core Fetch with Timeout
    // =============================
    async fetch(endpoint, options = {}) {
        //const controller = new AbortController();
        //const id = setTimeout(() => controller.abort(), this.timeout);
        //const token = await this.safeGet("access_token");
        //console.log("TOKEN", token);
        //const headers = {
        //    "Content-Type": "application/json",
        //    ...(token ? { Authorization: `Bearer ${token}`, "X-Token-Type": "access" } : {}),
        //    ...options.headers,
        //};

        try {

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            const token = await this.accessToken();
            const headers = {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
                headers["X-Token-Type"] = "access";
            }
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers,
                signal: controller.signal,
                keepalive: true,
            });

            clearTimeout(timeoutId);

            const contentType = response.headers.get("Content-Type") || "";
            const data = contentType.includes("application/json")
                ? await response.json()
                : { msg: await response.text(), code: "UNKNOWN" };

            // 🚨 Errores específicos
            if (response.status === 401) {
                throw { message: `${data.message}`, code: data.code || "UNAUTHORIZED", raw: data };
            }
            if (response.status === 403) {
                throw { message: `🚫 Bloqueado: ${data.msg} ${data.bloqueado_hasta ? "hasta " + data.bloqueado_hasta : ""}`, code: data.code || "FORBIDDEN", raw: data };
            }
            if (response.status === 409) {
                throw { message: `⚠️ ${data.msg}`, code: data.code || "CONFLICT", raw: data };
            }
            if (response.status === 500) {
                throw { message: `💥 ${data.msg}`, code: data.code || "INTERNAL_SERVER_ERROR", raw: data };
            }

            if (!response.ok) {
                throw { message: data.msg || "Error desconocido", code: data.code || "UNKNOWN_ERROR", raw: data };
            }

            return data;
        
        } catch (err) {
            handleError(err);
            throw err; // Permitir catch a nivel superior
        }
    }

    
   


    /**
     * Método privado para centralizar almacenamiento
     * @param {Object} data
     */
    async _saveUserData(data) {
        for (const [key, value] of Object.entries(data)) {
            if (value === undefined || value === null) continue;
            try {
                await this.storage.set(key, value);
            } catch (err) {
                console.error(`Error guardando ${key}:`, err);
            }
        }
    }

    // =============================
    // Métodos HTTP base
    // =============================
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
