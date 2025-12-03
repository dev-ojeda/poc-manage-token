
export class ApiClientSecureAESWebAuthn {
    constructor({
        baseURL,
        timeout = 15000,
        retry = 2,
        tokenEndpoint = "/auth/refresh",
        dbName = "auth_tokens",
        storeName = "tokens",
        encryptionPassphrase,
        pbkdf2Iterations = 150_000
    } = {}) {
        if (!encryptionPassphrase) throw new Error("encryptionPassphrase required");

        this.baseURL = baseURL.endsWith("/") ? baseURL.slice(0, -1) : baseURL;
        this.timeout = timeout;
        this.retry = retry;
        this.tokenEndpoint = tokenEndpoint;
        this.dbName = dbName;
        this.storeName = storeName;
        this._passphrase = encryptionPassphrase;
        this._pbkdf2Iterations = pbkdf2Iterations;
        this.defaultHeaders = { "Content-Type": "application/json", Accept: "application/json" };

        this._db = null;
        this._cryptoKeyPromise = null;
    }

    static async create(options) {
        const instance = new ApiClientSecureAESWebAuthn(options);
        await instance.init();
        return instance;
    }

    async init() {
        this._db = await this._initDB();
        this._cryptoKeyPromise = this._prepareCrypto();
        return this;
    }

    /**
     * Abrir conexion IndexDB
     * @returns
     */
    _openDBRequest() {
        return indexedDB.open(this.dbName, 1);
    }

    async _initDB() {
        return new Promise((resolve, reject) => {
            const req = this._openDBRequest();
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains(this.storeName)) db.createObjectStore(this.storeName);
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async _idbGet(key) {
        const db = this._db;
        return new Promise((res, rej) => {
            const tx = db.transaction(this.storeName, "readonly");
            const req = tx.objectStore(this.storeName).get(key);
            req.onsuccess = () => res(req.result);
            req.onerror = () => rej(req.error);
        });
    }

    async _idbPut(key, value) {
        const db = this._db;
        return new Promise((res, rej) => {
            const tx = db.transaction(this.storeName, "readwrite");
            const req = tx.objectStore(this.storeName).put(value, key);
            req.onsuccess = () => res();
            req.onerror = () => rej(req.error);
        });
    }

    async _idbDel(key) {
        const db = this._db;
        return new Promise((res, rej) => {
            const tx = db.transaction(this.storeName, "readwrite");
            const req = tx.objectStore(this.storeName).delete(key);
            req.onsuccess = () => res();
            req.onerror = () => rej(req.error);
        });
    }

    /**
     * Convert arbitrary bytes (Uint8Array) to base64 safely using chunking
     * @param {any} u8
     * @returns
     */
    _u8ToB64(u8) {
        const CHUNK = 0x8000;
        let binary = "";
        for (let i = 0; i < u8.length; i += CHUNK) {
            binary += String.fromCharCode.apply(null, u8.subarray(i, i + CHUNK));
        }
        return btoa(binary);
    }

    /**
     * Convert base64 to Uint8Array using codePointAt for Unicode-aware handling
     * @param {any} b64
     * @returns
     */
    _b64ToU8(b64) {
        const binary = atob(b64);
        /**Convert base64 to Uint8Array using codePointAt for Unicode-aware handling */
        return Uint8Array.from(binary, (c) => c.codePointAt(0));
    }
    /**
     * Base64URL helpers
     * @param {any} buf
     * @returns
     */
    _b64uEncode(buf) {
        const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
        let binary = '';
        const chunk = 0x8000;
        for (let i = 0; i < u8.length; i += chunk) {
            binary += String.fromCharCode.apply(null, u8.subarray(i, i + chunk));
        }
        return btoa(binary)
            .replaceAll('+', '-')
            .replaceAll('/', '_')
            .replace(/=+$/, '');
    }

    _b64uDecode(b64u) {
        const pad = "=".repeat((4 - (b64u.length % 4)) % 4);
        const b64 = b64u.replaceAll("-", "+").replaceAll("_", "/") + pad;
        const str = atob(b64);
        return new TextEncoder().encode(str).buffer;
    }

    /**
     * Crypto AES-GCM
     * @returns
     */
    async _prepareCrypto() {
        let salt = await this._idbGet("__enc_salt");
        salt = salt ? this._b64ToU8(salt) : crypto.getRandomValues(new Uint8Array(16));

        const webraw = await this._idbGet("__webauthn_rawid");
        if (webraw) {
            const rawU8 = this._b64ToU8(webraw);
            const combined = new Uint8Array(salt.length + rawU8.length);
            combined.set(salt, 0);
            combined.set(rawU8, salt.length);
            salt = new Uint8Array(await crypto.subtle.digest("SHA-256", combined));
        }

        if (!await this._idbGet("__enc_salt")) await this._idbPut("__enc_salt", this._u8ToB64(salt));

        const enc = new TextEncoder();
        const baseKey = await crypto.subtle.importKey("raw", enc.encode(this._passphrase), "PBKDF2", false, ["deriveKey"]);

        return crypto.subtle.deriveKey(
            { name: "PBKDF2", salt, iterations: this._pbkdf2Iterations, hash: "SHA-256" },
            baseKey,
            { name: "AES-GCM", length: 256 },
            false,
            ["encrypt", "decrypt"]
        );
    }

    async _encryptString(plaintext) {
        const key = await this._cryptoKeyPromise;
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(plaintext));
        return JSON.stringify({ iv: this._u8ToB64(iv), ct: this._u8ToB64(new Uint8Array(ct)) });
    }

    async _decryptString(payloadStr) {
        if (!payloadStr) return null;
        const key = await this._cryptoKeyPromise;
        try {
            const { iv, ct } = JSON.parse(payloadStr);
            const ptBuf = await crypto.subtle.decrypt({ name: "AES-GCM", iv: this._b64ToU8(iv) }, key, this._b64ToU8(ct));
            return new TextDecoder().decode(ptBuf);
        } catch {
            return null;
        }
    }

    async setTokens({ access_token, refresh_token } = {}) {
        if (access_token) await this._idbPut("access_token", await this._encryptString(access_token));
        if (refresh_token) await this._idbPut("refresh_token", await this._encryptString(refresh_token));
    }

    async getAccessToken() {
        const enc = await this._idbGet("access_token");
        return enc ? await this._decryptString(enc) : null;
    }

    async getRefreshToken() {
        const enc = await this._idbGet("refresh_token");
        return enc ? await this._decryptString(enc) : null;
    }

    async clearTokens() {
        await this._idbDel("access_token");
        await this._idbDel("refresh_token");
    }

    async request(endpoint, { method = "GET", data = null, headers = {}, retryCount = 0 } = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        const token = await this.getAccessToken();

        const config = {
            method,
            headers: { ...this.defaultHeaders, ...headers },
            signal: controller.signal,
            credentials: "include"
        };
        if (token) {
            config.headers["Authorization"] = `Bearer ${token}`;
            config.headers["X-Token-Type"] = "access";
        }
        if (data) config.body = JSON.stringify(data);

        try {
            const res = await fetch(`${this.baseURL}${endpoint}`, config);
            clearTimeout(timeoutId);

            if (res.status === 401 && retryCount < this.retry) {
                const refreshed = await this._tryRefreshToken();
                if (refreshed) return this.request(endpoint, { method, data, headers, retryCount: retryCount + 1 });
                await this.clearTokens();
                throw new Error("Sesión expirada");
            }

            if (!res.ok) {
                const text = await res.text();
                throw new Error(`Error ${res.status}: ${text || res.statusText}`);
            }

            const ct = res.headers.get("Content-Type");
            return ct?.includes("application/json") ? await res.json() : await res.text();
        } catch (err) {
            clearTimeout(timeoutId);
            throw err;
        }
    }

    async _tryRefreshToken() {
        const refresh = await this.getRefreshToken();
        if (!refresh) return false;
        try {
            const res = await fetch(`${this.baseURL}${this.tokenEndpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refresh }),
                credentials: "include"
            });
            if (!res.ok) return false;
            const data = await res.json();
            if (data.access_token) await this.setTokens({ access_token: data.access_token, refresh_token: data.refresh_token || refresh });
            return !!data.access_token;
        } catch {
            return false;
        }
    }

    get(endpoint, opts = {}) { return this.request(endpoint, { method: "GET", ...opts }); }
    post(endpoint, data, opts = {}) { return this.request(endpoint, { method: "POST", data, ...opts }); }
    put(endpoint, data, opts = {}) { return this.request(endpoint, { method: "PUT", data, ...opts }); }
    delete(endpoint, opts = {}) { return this.request(endpoint, { method: "DELETE", ...opts }); }

    /**
     * Passphrase rotation 
     * @param {any} passphrase
     * @param {any} saltU8
     * @returns
     */
    async _deriveKeyFromPassphrase(passphrase, saltU8 = null) {
        const enc = new TextEncoder();
        let salt = saltU8;
        if (!salt) {
            const stored = await this._idbGet("__enc_salt");
            salt = stored ? this._b64ToU8(stored) : crypto.getRandomValues(new Uint8Array(16));
        }
        const baseKey = await crypto.subtle.importKey("raw", enc.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
        const derivedKey = await crypto.subtle.deriveKey(
            { name: "PBKDF2", salt, iterations: this._pbkdf2Iterations, hash: "SHA-256" },
            baseKey,
            { name: "AES-GCM", length: 256 },
            false,
            ["encrypt", "decrypt"]
        );
        return { derivedKey, salt };
    }

    async rotatePassphrase(oldPassphrase, newPassphrase) {
        if (!oldPassphrase || !newPassphrase) throw new Error("Both passphrases required");

        const { derivedKey: oldKey } = await this._deriveKeyFromPassphrase(oldPassphrase);

        const decryptWithKey = async (payload, key) => {
            if (!payload) return null;
            try {
                const { iv, ct } = JSON.parse(payload);
                const ptBuf = await crypto.subtle.decrypt({ name: "AES-GCM", iv: this._b64ToU8(iv) }, key, this._b64ToU8(ct));
                return new TextDecoder().decode(ptBuf);
            } catch {
                return null;
            }
        };

        const accessPlain = await decryptWithKey(await this._idbGet("access_token"), oldKey);
        const refreshPlain = await decryptWithKey(await this._idbGet("refresh_token"), oldKey);

        this._passphrase = newPassphrase;
        this._cryptoKeyPromise = this._prepareCrypto();

        await this.setTokens({ access_token: accessPlain, refresh_token: refreshPlain });
        return true;
    }

    /**
     * WebAuthn
     * @param {any} publicKeyCredentialCreationOptions
     * @returns
     */
    async registerWebAuthn(publicKeyCredentialCreationOptions) {
        if (!globalThis.PublicKeyCredential) throw new Error("WebAuthn not supported");

        const prepare = (opt) => {
            const copy = structuredClone(opt);

            const fix = (b64u) => {
                if (typeof b64u === "string") {
                    const pad = "=".repeat((4 - (b64u.length % 4)) % 4);
                    const b64 = b64u.replaceAll("-", "+").replaceAll("_", "/") + pad;
                    const bin = atob(b64);
                    return Uint8Array.from(bin, (c) => c.codePointAt(0)).buffer;
                }
                return b64u;
            };

            if (copy.challenge) copy.challenge = fix(copy.challenge);
            if (copy.user?.id) copy.user.id = fix(copy.user.id);
            if (copy.excludeCredentials) copy.excludeCredentials = copy.excludeCredentials.map(c => ({ ...c, id: fix(c.id) }));

            return copy;
        };

        const opts = prepare(publicKeyCredentialCreationOptions);
        const cred = await globalThis.navigator.credentials.create({ publicKey: opts });
        if (!cred) throw new Error("WebAuthn registration failed");
        console.table(cred);
        await this._idbPut("__webauthn_rawid", this._u8ToB64(new Uint8Array(cred.rawId)));
        this._cryptoKeyPromise = this._prepareCrypto();

        const payload = {
            rawId: this._u8ToB64(new Uint8Array(cred.rawId)),
            type: cred.type,
            attestationObject: this._u8ToB64(new Uint8Array(cred.response.attestationObject)),
            clientDataJSON: this._u8ToB64(new Uint8Array(cred.response.clientDataJSON))
        };

        return  payload;
    }
  
    _fixBase64Url(b64u) {
        const pad = "=".repeat((4 - (b64u.length % 4)) % 4);
        const b64 = b64u.replaceAll("-", "+").replaceAll("_", "/") + pad;
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i) & 0xff;
        }
        return bytes.buffer;
    }
    async authenticateWebAuthn(options) {
        console.table(options);

        const safeDecode = (v) =>
            typeof v === "string" && v.length ? this._fixBase64Url(v) : null;

        options.challenge = safeDecode(options?.challenge);
        options.timeout = 120000; // 2 minutos

        options.allowCredentials = options?.allowCredentials
            ?.filter(c => c?.id)
            .map(c => ({
                ...c,
                id: safeDecode(c.id)
            })) ?? [];

        if (options.extensions) delete options.extensions;

        if (!options.challenge) {
            throw new Error("Challenge faltante o inválido");
        }

        const credential = await globalThis.navigator.credentials.get({ publicKey: options })
            .catch(e => {
                console.error("WebAuthn error:", e.name, e.message);
                throw e;
            });

        return {
            id: credential.id,
            rawId: this._b64uEncode(credential.rawId),
            type: credential.type,
            response: {
                authenticatorData: this._b64uEncode(credential.response?.authenticatorData),
                clientDataJSON: this._b64uEncode(credential.response?.clientDataJSON),
                signature: this._b64uEncode(credential.response?.signature),
                userHandle: credential.response?.userHandle
                    ? this._b64uEncode(credential.response.userHandle)
                    : null
            }
        };
    }

    async clearWebAuthnBinding() {
        await this._idbDel("__webauthn_rawid");
        this._cryptoKeyPromise = this._prepareCrypto();
    }
}
