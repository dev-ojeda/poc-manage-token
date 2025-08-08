export class SessionService {
    constructor(api) {
        this.api = api;
    }

    async getSesionesActivas() {
        const token = this.api.refreshToken;
        const res = await fetch("/api/auth/sessions", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Error al cargar sesiones");
        return res.json();
    }

    async revocarSesion({ session_id, access, username, device, rol, refresh }) {
        const res = await fetch("/api/auth/sessions/revoke", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${access}`,
                "X-Token-Type": "refresh"
            },
            body: JSON.stringify({ user_id: session_id, username: username, device_id: device, user_rol: rol, refresh_token: refresh })
        });

        if (!res.ok) throw new Error("No se pudo revocar");
        return res;
    }
}
