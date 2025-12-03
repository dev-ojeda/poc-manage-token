import { ApiClientSecureAESWebAuthn } from "./api/ApiClientSecureAESWebAuthn.js";

const api = await ApiClientSecureAESWebAuthn.create({ baseURL: "https://localhost:5000/", encryptionPassphrase: "demo-pass" });

const form = document.getElementById("login-form");
const status = document.getElementById("status");

form.addEventListener("submit", async e => {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    if (!username) return;

    try {
        status.textContent = "Autenticando...";
        const options = await (await fetch(`/auth/webauthn/assertion-options?username=${username}`)).json();
        const publicKeyCredentialCreationOptions = options.publicKey;
        const assertion = await api.authenticateWebAuthn(publicKeyCredentialCreationOptions);
        const res = await fetch("/auth/webauthn/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assertion, username }) });
        if (!res.ok) throw new Error("Login fallido");
        status.textContent = "Autenticado";
        setTimeout(() => location.href = "/auth/dashboard", 1200);
    } catch (err) {
        status.textContent = `Error: ${err.message}`;
    }
});
