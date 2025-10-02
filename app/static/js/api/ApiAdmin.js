import { ApiClient } from "../api/ApiClient.js"
import { handleError } from "../utils/errors.js"

export class ApiAdmin extends ApiClient {
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

            const res = await this.post("/api/auth/admin", {
                username,
                password,
                device,
                rol: "Admin",
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

    async setTokens(res) {
        if (res?.access_token) {
            await this.storage.set("access_token", res.access_token);
        }
        if (res?.refresh_token) {
            await this.storage.set("refresh_token", res.refresh_token);
        }
    }

    async admin_dashboard() {
        try {
            const deviceId = await this.getDeviceId();
            if (!deviceId) throw new Error("Device ID no definido");

            const res = await this.get("/api/auth/admin/dashboard");
            const now = Math.floor(Date.now() / 1000);

            if (res.exp && now > res.exp) throw new Error("⏰ Token expirado del lado cliente");

            this.storage.set("username", res.username);
            this.storage.set("rol", res.rol);
            this.storage.set("device_id", res.device_id);
            this.storage.set("exp", res.exp);
            this.storage.set("jti", res.jti);

            return true;
        } catch (err) {
            handleError(err);
            return false;
        }
    }

    async fetchTimeline({ interval = "hour", limit = 24, categories = ["apiresponsetime", "webvitals"], role = "User" } = {}) {
        try {
            const catStr = categories.join(",");
            const url = role ? `/api/metrics/timeline?category=${catStr}&interval=${interval}&limit=${limit}&role=${role}`
                : `/api/metrics/timeline?category=${catStr}&interval=${interval}&limit=${limit}`;
            return await this.get(url);
        } catch (err) {
            handleError(err);
            return null;
        }
    }
    async fetchSummary({ minutes = 50, role = "User" } = {}) {
        const url = role ? `/api/metrics/summary?minutes=${minutes}&role=${role}`
            : `/api/metrics/summary?minutes=${minutes}`;
        console.log(url);
        return await this.get(url);
    }
    async logout_admin() {
        await this.clearTokens();  // Limpia storage
        window.location.href = "/?logout=true";
    }
}
