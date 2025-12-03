import { ApiClientSecureAESWebAuthn } from "../api/ApiClientSecureAESWebAuthn.js";

const api = await ApiClientSecureAESWebAuthn.create({
    baseURL: "https://localhost:5000/",
    encryptionPassphrase: "demo-pass"
});

const userLabel = document.getElementById("user-label");
const btnLogout = document.getElementById("btn-logout");
const btnTestApi = document.getElementById("btn-test-api");
const apiResponse = document.getElementById("api-response");

// Verificación de sesión
//try {
//    const profile = await api.get("/auth/me");
//    if (profile?.username) {
//        userLabel.textContent = `Usuario: ${profile.username}`;
//    } else {
//        globalThis.location.href = "/auth/login";
//    }
//} catch {
//    globalThis.location.href = "/auth/login";
//}

//btnLogout.addEventListener("submit", async () => {
//    await api.clearTokens();
//    await api.clearWebAuthnBinding();
//    //globalThis.location.href = "/login";
//});

btnTestApi.addEventListener("click", async () => {
    try {
        const data = await api.get("/secure/ping");
        apiResponse.textContent = `✅ API responde: ${JSON.stringify(data)}`;
    } catch (err) {
        apiResponse.textContent = `❌ Error: ${err.message}`;
    }
});