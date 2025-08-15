import { ApiClient } from "../api/ApiClient.js"
import { handleError } from "../utils/errors.js"
export class ApiAdmin extends ApiClient {

    async login_admin(username, password) {
        try {
            const device = this.getDeviceId();
            const user_agent = this.getBrowserInfo();
            const rol = "Admin";
            const res = await this.post("/api/auth/admin", {
                username,
                password,
                device,
                rol,
                user_agent
            });

            // Guardar tokens y datos
            this.storage.set("access_token", res.access_token);
            this.storage.set("refresh_token", res.refresh_token);
            this.storage.set("device_id", res.device_id);
            this.storage.set("username", username);
            this.storage.set("rol", res.rol || "Admin");

            return res; // Retornar la respuesta completa
        } catch (err) {
            handleError(err);
            return null;
        }
    }

    async admin_dashboard() {
        try {
            if (!this.deviceId) throw new Error("Device ID no definido");

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

}
