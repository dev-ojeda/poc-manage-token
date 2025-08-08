import { SessionPanel } from "../SessionPanel.js";
import { ApiClient } from "../ApiClient.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { openChat } from "../modules/chatHandler.js";

const api = new ApiClient({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

export async function cargarDashboard() {
    document.getElementById("userName").innerText = api.userName + " 👋";
    openChat(api.userRol);
    const panel = new SessionPanel("#tablaSesiones tbody");
    await panel.cargarSesionesActivas();
}
