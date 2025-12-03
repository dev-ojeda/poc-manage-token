import { ApiClient } from "../api/ApiClient.js"
import { handleError } from "../utils/errors.js"
export class ApiAdmin extends ApiClient {
    constructor(opts) {
        super({
            baseURL: opts.baseURL,
            storage: opts.storage,
            timeout: opts.timeout || 10000,
            debugEnabled: opts.debugEnabled || false 
        });
        this.isRefreshing = false;   
        this.refreshQueue = [];     
    }
    
    async login(username, password) {
        try {
            const device = await this.getDeviceId();
            const user_agent = this.getBrowserInfo();

            const res = await this.fetchJson("/api/auth/admin", {
                method: "POST",
                body: JSON.stringify({ username, password, device, rol: "Admin", user_agent }),
            });
            this._debug("login Admin → Resultado:", res);
            if (res?.access_token && res?.refresh_token) {
                await this.setTokens({ access_token: res.access_token, refresh_token: res.refresh_token, rol: res.rol });  // ✅ corregido: se llama correctamente
            }

            return res;
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    async accessTokenAdmin() {
        const data = await this.accessToken("admin");
        return data?.value || null;
    }

    async refreshTokenAdmin() {
        const data = await this.refreshToken("admin");
        return data?.value || null;
    }
    async loadInfoAdmin() {
        try {
            return await this.fetchJson("/api/auth/admin/dashboard");
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    async loadActiveSessions(payload) {
        try {
            const res = await this.fetchJson("/api/auth/sessions/active", {
                method: "POST",
                body: JSON.stringify({ payload })
            });
            return res;
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    async loadAuditLogs() {
        try {
            const res = await this.fetchJson("/api/auth/admin/audit");
            return res;
        } catch (err) {
            await handleError(err);
            return null;
        }
    }

    async fetchDashboardHtml() {
        try {
            return await this.fetchHtml("/admin/partial");
        } catch (err) {
            handleError(err);
            return "";
        }
    }

    async fetchTimeline({ interval = "hour", limit = 24, categories = ["apiresponsetime", "webvitals"], role = "User" } = {}) {
        try {
            const catStr = categories.join(",");
            const url = role
                ? `/api/metrics/timeline?category=${catStr}&interval=${interval}&limit=${limit}&role=${role}`
                : `/api/metrics/timeline?category=${catStr}&interval=${interval}&limit=${limit}`;
            return await this.fetchJson(url);
        } catch (err) {
            handleError(err);
            return null;
        }
    }


    async fetchSummary({ minutes = 50, role = "User" } = {}) {
        try {
            const url = role
                ? `/api/metrics/summary?minutes=${minutes}&role=${role}`
                : `/api/metrics/summary?minutes=${minutes}`;
            return await this.fetchJson(url);
        } catch (err) {
            handleError(err);
            return null;
        }
    }

    async logout(reason="close") {
        location.replace("/?logout=true");
    }

    _debug(label, ...args) {
        if (!this.debugEnabled) return;

        const time = new Date().toLocaleTimeString();
        const color = "color: #0dcaf0; font-weight: bold;";
        console.groupCollapsed(`🧠 %c[DEBUG ${time}] ${label}`, color);
        console.log(...args);
        console.groupEnd();
        document.dispatchEvent(
            new CustomEvent("debug:log", { detail: { label, args } })
        );
    }

}
