import { ApiClientSecureAESWebAuthn } from "../api/ApiClientSecureAESWebAuthn.js";

// Crear cliente WebAuthn
const api = await ApiClientSecureAESWebAuthn.create({
    baseURL: "https://localhost:5000/",
    encryptionPassphrase: "demo-pass"
});

// Ejecutar cuando DOM esté listo
document.addEventListener("DOMContentLoaded", () => {
    const formLogin = document.getElementById("login-form");
    const btnRegistrar = document.getElementById("btn-register");
    const status = document.getElementById("status");

    // --------------------------
    // LOGIN WebAuthn
    // --------------------------
    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("username").value.trim();
        if (!username) return;

        try {
            status.textContent = "Solicitando desafío de autenticación...";

            // Obtener opciones assertion desde backend
            const options = await (await fetch(`/auth/webauthn/assertion-options?username=${username}`)).json();

            // ⚡ Esperar a que la pestaña tenga foco antes de llamar a navigator.credentials
            await ensurePageFocus();

            const assertion = await api.authenticateWebAuthn(options);

            const res = await fetch("/auth/webauthn/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ assertion, username })
            });

            if (!res.ok) throw new Error("Login WebAuthn fallido");

            status.textContent = "Autenticado correctamente. Redirigiendo...";
            setTimeout(() => (location.href = "/auth/dashboard"), 1200);

        } catch (err) {
            console.error(err);
            status.textContent = `Error: ${err.message}`;
        }
    });

    // --------------------------
    // REGISTRO WebAuthn + usuario
    // --------------------------
    btnRegistrar.addEventListener("click", async (e) => {
        e.preventDefault();
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();
        if (!username || !password) return;

        try {
            status.textContent = "Registrando usuario...";

            // Crear usuario en backend
            const createUser = fetch("/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            // Obtener challenge WebAuthn
            const optionsPromise = fetch("/auth/webauthn/options").then(r => r.json());

            const [userResp, opts] = await Promise.all([createUser, optionsPromise]);
            if (!userResp.ok) throw new Error("Registro de usuario fallido");

            await ensurePageFocus();

            // Crear credencial en autenticador
            const cred = await api.registerWebAuthn(opts);

            // Guardar credencial en backend
            await fetch("/auth/webauthn/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cred, username })
            });

            status.textContent = "Registro exitoso. Redirigiendo...";
            setTimeout(() => (location.href = "/auth/dashboard"), 1200);

        } catch (err) {
            console.error(err);
            status.textContent = `Error: ${err.message}`;
        }
    });

});

// --------------------------
// Ayuda: asegurar foco antes de WebAuthn
// --------------------------
async function ensurePageFocus() {
    if (document.hasFocus()) return;
    await new Promise(resolve => {
        const onFocus = () => {
            resolve();
            window.removeEventListener("focus", onFocus);
        };
        window.addEventListener("focus", onFocus);
    });
}
