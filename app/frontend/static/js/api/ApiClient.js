// ==============================
// api/ApiClient.js (v2.2 - Universal Refactor)
// ==============================

import { showGlobalAlert, GLOBAL_DEBUG } from "../layout.js";
import { handleError } from "../utils/errors.js";
import { FetchError } from "../utils/fetchError.js";

export class ApiClient {
    constructor({ baseURL, storage, timeout = 150000, notifier = showGlobalAlert, debugEnabled = GLOBAL_DEBUG }) {
        this.baseURL = baseURL;
        this.storage = storage;
        this.timeout = timeout;
        this.notifier = notifier;
        this.debugEnabled = debugEnabled;
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
        const prefix = icons[level] || "🔹";

        if (globalThis.console) {
            console.groupCollapsed(`%c${prefix} [${level.toUpperCase()} ${time}] ${label}`, styles[level]);
            console.log(...args);
            console.groupEnd();
        }
    }

    _debug(label, ...args) { this._log("debug", label, ...args); }
    _info(label, ...args) { this._log("info", label, ...args); }
    _warn(label, ...args) { this._log("warn", label, ...args); }
    _error(label, ...args) { this._log("error", label, ...args); }

    async safeGet(key) {
        try {
            return await this.storage.get(key);
        } catch (err) {
            this._error(`Error leyendo ${key}:`, err);
            return null;
        }
    }

    async _saveUserData(data) {
        const entries = Object.entries(data).filter(([_, v]) => v != null);
        await Promise.allSettled(entries.map(([k, v]) => this.storage.set(k, v)));
    }

    async clearTokens() {
        await this.storage.clear();
    }

    async getDeviceId() {
        let device = await this.safeGet("device_id");
        if (!device) {
            const cryptoRef = globalThis.crypto || (await import("crypto")).webcrypto;
            device = cryptoRef.randomUUID();
            await this.storage.set("device_id", device);
        }
        return device;
    }

    getBrowserInfo() {
        const ua = globalThis.navigator?.userAgent || "Desconocido";

        const browsers = [
            { name: "Chrome", match: ua.includes("Chrome") && !ua.includes("Edg") },
            { name: "Firefox", match: ua.includes("Firefox") },
            { name: "Safari", match: ua.includes("Safari") && !ua.includes("Chrome") },
            { name: "Edge", match: ua.includes("Edg") },
            { name: "Opera", match: ua.includes("OPR") }
        ];

        const osList = [
            { name: "Windows", match: ua.includes("Windows") },
            { name: "MacOS", match: ua.includes("Mac OS") },
            { name: "Linux", match: ua.includes("Linux") },
            { name: "Android", match: /Android/.test(ua) },
            { name: "iOS", match: /iPhone|iPad|iPod/.test(ua) }
        ];

        return {
            browser: browsers.find(b => b.match)?.name || "Desconocido",
            os: osList.find(o => o.match)?.name || "Desconocido"
        };
    }

    async userRol() {
        const rol = await this.safeGet("rol");
        return (rol?.value || rol || "user").toLowerCase();
    }

    async accessToken(rol = "") {
        rol = rol || await this.userRol();
        const key = rol === "admin" ? "access_token_admin" : "access_token_user";
        const token = await this.safeGet(key);
        return token?.value || token;
    }

    async refreshToken(rol = "") {
        rol = rol || await this.userRol();
        const key = rol === "admin" ? "refresh_token_admin" : "refresh_token_user";
        const token = await this.safeGet(key);
        return token?.value || token;
    }

    async setTokens({ access_token, refresh_token, rol = "user" }) {
        const prefix = rol.toLowerCase() === "admin" ? "admin" : "user";
        await this._saveUserData({
            [`access_token_${prefix}`]: access_token,
            [`refresh_token_${prefix}`]: refresh_token,
            rol
        });
    }
    async fetchJson(endpoint, options = {}) { return this._doFetch(endpoint, options, "json"); }
    async fetchHtml(endpoint, options = {}) { return this._doFetch(endpoint, options, "text"); }
    async fetchBlob(endpoint, options = {}) { return this._doFetch(endpoint, options, "blob"); }
    async _doFetch(endpoint, options = {}, type = "json", _retry = false) {
        const rol = await this.userRol();
        this._info(`ROL`, rol);
        try {
            const response = await this._safeFetch(endpoint, options, 2, 400, rol);
            const contentType = response.headers?.get("content-type") || "";
            const isJson = contentType.includes("application/json");
            let data = null;

            // Manejo robusto de contenido segun tipo
            if (type === "blob") {
                data = await response.blob();
            } else if (type === "text") {
                data = await response.text();
            } else if (isJson) {
                try {
                    data = await response.json();
                } catch (parseError) {
                    const raw = await response.text();
                    this._warn("⚠️ Respuesta no es JSON válido:", raw);
                    data = { rawResponse: raw };
                }
            } else {
                // Si el servidor devuelve algo inesperado (ej: texto plano con content-type erróneo)
                const raw = await response.text();
                this._warn("⚠️ Respuesta sin JSON detectada:", raw);
                data = { rawResponse: raw };
            }

            if (response.ok) return data;

            // Intento de refrescar token si 401
            if (response.status === 401 && !_retry) {
                const refreshed = await this._tryRefreshToken(rol);
                if (refreshed) {
                    this._info("🔁 Token refrescado, reintentando...");
                    return this._doFetch(endpoint, options, type, true);
                }
            }

            this._throwHttpError(response, data);

        } catch (err) {
            this._error(`💥 Error en _doFetch(${endpoint})`, err);
            return this._handleFetchError(err);
        }
    }

    _handleFetchError(err) {
        if (err.name === "AbortError") {
            this._error("⏱ Timeout: servidor no respondió", err);
            return handleError({ message: "⏱ Timeout: servidor no respondió", code: "TIMEOUT" });
        }
        if (err instanceof TypeError && err.message.includes("fetch")) {
            this._error("🌐 Error de red o servidor inaccesible", err);
            return handleError({ message: "🌐 Error de red o servidor inaccesible", code: "NETWORK_ERROR" });
        }
        this._error("Error interno", err);
        return handleError(err);
    }

    _throwHttpError(response, data) {
        const defaultMsg = data?.message || data?.msg || "Error desconocido";
        const messages = {
            401: ["No autorizado", "UNAUTHORIZED"],
            403: [`🚫 Bloqueado: ${data?.msg || defaultMsg}`, "FORBIDDEN"],
            409: [`⚠️ ${data?.msg || defaultMsg}`, "CONFLICT"],
            429: ["⏳ Límite excedido", "RATE_LIMIT"],
            500: ["💥 Error interno del servidor", "SERVER_ERROR"]
        };

        const [message, code] = messages[response.status] || [defaultMsg, "UNKNOWN"];
        throw new FetchError(message, response.status, data, code);
    }
    async _safeFetch(endpoint, options = {}, retries = 3, baseDelay = 500, rol = "") {
        const url = `${this.baseURL}${endpoint}`;
        const controller = new AbortController();

        for (let attempt = 1; attempt <= retries + 1; attempt++) {
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            try {
                const response = await this._executeFetch(url, options, controller, rol, attempt);
                clearTimeout(timeoutId);

                if (response.ok) return response;

                // --- Manejo seguro del cuerpo de error (sin romper si no es JSON) ---
                let data = {};
                try {
                    const raw = await response.text();
                    if (raw.trim().startsWith("{") || raw.trim().startsWith("[")) {
                        data = JSON.parse(raw);
                    } else {
                        this._warn("⚠️ Respuesta no JSON (raw):", raw.slice(0, 200));
                        data = { rawResponse: raw };
                    }
                } catch (err) {
                    this._error("❌ Error leyendo respuesta del servidor", err);
                    data = { rawResponse: "[Invalid response]" };
                }

                // --- Decide si reintentar o lanzar error ---
                if (this._shouldRetryStatus(response.status, attempt, retries)) {
                    await this._retryDelay(attempt, baseDelay, response.status);
                    continue;
                }

                throw new FetchError(`HTTP ${response.status}`, response.status, data);

            } catch (err) {
                clearTimeout(timeoutId);

                if (this._shouldRetryError(err, attempt, retries)) {
                    await this._retryDelay(attempt, baseDelay, err.name);
                    continue;
                }

                this._error(`💥 Fetch falló tras ${attempt} intentos`, err);
                throw err;
            }
        }
    }

    async _executeFetch(url, options, controller, rol, attempt) {
        let token = await this.accessToken(rol);
        if (!token) {
            this._warn("⏳ Esperando token...");
            for (let i = 0; i < 5; i++) {
                await new Promise(r => setTimeout(r, 200));
                token = await this.accessToken(rol);
                if (token) break;
            }
        }

        if (!token) this._warn("⚠️ No se encontró token antes del fetch");

        const headers = {
            "Content-Type": "application/json",
            ...options?.headers,
            ...(token && { Authorization: `Bearer ${token}`, "X-Token-Type": "access" })
        };

        this._debug(`🌍 Attempt ${attempt}`, { url, headers });

        return globalThis.fetch(url, {
            ...options,
            headers,
            signal: controller.signal,
            keepalive: true
        });
    }
    _shouldRetryStatus(status, attempt, retries) {
        return [429, 500, 502, 503, 504].includes(status) && attempt <= retries;
    }
    _shouldRetryError(err, attempt, retries) {
        return (err.name === "AbortError" || (err instanceof TypeError && err.message.includes("fetch"))) && attempt <= retries;
    }

    _retryDelay(attempt, baseDelay, reason) {
        const delay = baseDelay * 2 ** (attempt - 1);
        this._warn(`⚠️ Reintentando (${reason}) en ${delay}ms`);
        return new Promise(r => setTimeout(r, delay));
    }
    async get(endpoint, options = {}) { return this.fetchJson(endpoint, { ...options, method: "GET" }); }
    async post(endpoint, body = {}, options = {}) { return this.fetchJson(endpoint, { ...options, method: "POST", body: JSON.stringify(body) }); }
    async put(endpoint, body = {}, options = {}) { return this.fetchJson(endpoint, { ...options, method: "PUT", body: JSON.stringify(body) }); }
    async delete(endpoint, options = {}) { return this.fetchJson(endpoint, { ...options, method: "DELETE" }); }
}
