
// register.js
import { ApiClientSecureAESWebAuthn } from "../js/api/ApiClientSecureAESWebAuthn.js";

const api = await ApiClientSecureAESWebAuthn.create({
    baseURL: "https://localhost:5000/",
    encryptionPassphrase: "demo-pass"
});

const form = document.getElementById("register-form");
const status = document.getElementById("status");

form.addEventListener("submit", async (e) => {
    e.preventDefault(); // evita recarga de página

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();
    if (!username || !password) return;

    try {
        status.textContent = "Registrando...";

        const [userResp, opts] = await Promise.all([
            fetch("/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            }),
            fetch("/auth/webauthn/options").then(r => r.json())
        ]);
        if (!userResp.ok) throw new Error("Registro fallido");
        const publicKeyCredentialCreationOptions = opts.publicKey;
        const cred = await api.registerWebAuthn(publicKeyCredentialCreationOptions);
        console.table(cred);
        await fetch("/auth/webauthn/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cred, username })
        });

        status.textContent = "Registro exitoso";
        setTimeout(() => location.href = "/dashboard", 1200);

    } catch (err) {
        console.error(err);
        status.textContent = `Error: ${err.message}`;
    }
});

