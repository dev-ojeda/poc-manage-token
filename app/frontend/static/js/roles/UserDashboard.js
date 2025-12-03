// =============================================
// UserDashboard.js v2.2 — Offline Ready Edition
// =============================================

import { ApiUser } from "../api/ApiUser.js";
import { AuthApp } from "../AuthApp.js";
import { IndexedDBStorage } from "../adapters/IndexedDBStorage.js";
import { showGlobalAlert, GLOBAL_DEBUG } from "../layout.js";
import { SPAHelper } from "../utils/spaHelper.js";
import { PartialCacheManager } from "../utils/PartialCacheManager.js";
import { OfflineDataManager } from "../utils/OfflineDataManager.js";

export class UserDashboard extends ApiUser {
    constructor() {
        const API_BASE = import.meta.env?.VITE_API_URL || "https://localhost:5000";
        const storage = new IndexedDBStorage("AuthDB", "tokens");
        super({ baseURL: API_BASE, storage, debugEnabled: GLOBAL_DEBUG });

        this.userCache = null;
        this.auth = new AuthApp();
        this.partialCache = new Map();
        this.dashboardContent = document.getElementById("dashboardContent");

        this.partialCacheManager = new PartialCacheManager(storage);
        this.offlineData = new OfflineDataManager(storage);

        this.spa = new SPAHelper({
            spinnerId: 'loadingSpinner',
            dashboardId: 'dashboardContent',
            sectionsSelector: '#dashboardContent > section',
            apiUser: this
        });
    }

    // =============================
    // 🔹 Logger
    // =============================
    _log(level = "info", label = "", ...args) {
        if (!this.debugEnabled) return;
        const time = new Date().toLocaleTimeString();
        const styles = {
            info: "color:#0dcaf0;font-weight:bold;",
            warn: "color:#ffc107;font-weight:bold;",
            error: "color:#dc3545;font-weight:bold;",
            success: "color:#28a745;font-weight:bold;",
            debug: "color:#6f42c1;font-weight:bold;"
        };
        const prefix = { info: "ℹ️", warn: "⚠️", error: "💥", success: "✅", debug: "🧠" }[level] || "🔹";
        console.groupCollapsed(`%c${prefix} [${level.toUpperCase()} ${time}] ${label}`, styles[level] || styles.info);
        console.log(...args);
        console.groupEnd();
        document.dispatchEvent(new CustomEvent("debug:log", { detail: { label, args } }));
    }

    _debug(label, ...args) { this._log("debug", label, ...args); }
    _info(label, ...args) { this._log("info", label, ...args); }
    _warn(label, ...args) { this._log("warn", label, ...args); }
    _error(label, ...args) { this._log("error", label, ...args); }
    _success(label, ...args) { this._log("success", label, ...args); }

    // =============================
    // 🔹 Inicialización
    // =============================
    async init() {
        try {
            await this.storage._init();
            await this.loadUserCache();

            if (!this.userCache?.user_rol) {
                return this.auth.redirectToLogin("No hay token válido.");
            }

            this.renderUserSession();
            this.setupSidebar(this.userCache.user_rol);
            this.spa.showDashboard();
            this.spa.startTokenTimer(this.userCache.expira);
            this.initMenu();

            // Lazy preload en background
            setTimeout(() => this.lazyPreload(), 2000);

        } catch (err) {
            this._error("Error inicializando dashboard", err);
            return this.auth.redirectToLogin("Token inválido o expirado.");
        }
    }

    async loadUserCache() {
        try {
            const res = await this.loadInfoUser();

            if (!res?.username || !res?.rol) {
                throw new Error("Respuesta inválida o incompleta del servidor");
            }

            this.userCache = {
                user_name: res.username ?? "Desconocido",
                user_rol: res.rol ?? "User",
                expira: res.exp ?? Date.now() + 3600000
            };

            await this.offlineData.saveUserInfo(this.userCache);
            this._success("UserCache", "Datos cargados y guardados localmente");

        } catch (error) {
            this._error("UserCache", "Fallo remoto:", error);

            try {
                this.userCache = await this.offlineData.getUserInfo();
                if (this.userCache?.user_name) {
                    this._warn("Offline", "Usando datos locales del usuario");
                } else {
                    throw new Error("Sin datos de usuario locales");
                }
            } catch (error) {
                this._error("UserCache", "Fallo al recuperar datos locales:", error);
                throw new Error("Fallo crítico: sin conexión ni datos locales");
            }
        }

        return this.userCache;
    }



    renderUserSession() {
        const userEl = document.getElementById("userName");
        if (userEl) userEl.textContent = `👋 ${this.userCache.user_name} (${this.userCache.user_rol})`;
        showGlobalAlert(`✨ Bienvenido, ${this.userCache.user_name}!`, "success", 3000);
    }

    setupSidebar(role) {
        if (!role) return;
        const roleLower = String(role).toLowerCase();
        for (const el of document.querySelectorAll("#sidebar [class*='role-']")) {
            const roles = [...el.classList].filter(c => c.startsWith("role-")).map(c => c.replace("role-", ""));
            el.style.display = roles.includes(roleLower) ? "block" : "none";
        }
    }

    // =============================
    // 🔹 Navegación SPA optimizada
    // =============================
    initMenu() {
        for (const btn of document.querySelectorAll("#sidebar button[data-action]")) {
            btn.addEventListener("click", async () => {
                const action = btn.dataset.action;
                const viewMap = {
                    "item-usuario": "items",
                    "user-chat": "chat",
                    "token-progress": "tokens",
                    "user-panel": "panel"
                };
                const view = viewMap[action] || "panel";
                const url = `/user/partial?view=${view}`;

                this._debug("SPA", `Cargando vista: ${view}`);

                try {
                    const html = await this.fetchPartialView(url);
                    this.dashboardContent.innerHTML = html;
                } catch (err) {
                    this._warn("SPA", `Fallo al cargar vista ${view}:`, err);
                    showGlobalAlert(`Modo offline: mostrando cache local.`, "warning", 3000);
                    const cached = await this.partialCacheManager.getPartial(view);
                    if (cached) {
                        this.dashboardContent.innerHTML = cached;
                    } else {
                        this.dashboardContent.innerHTML = `<div class='alert alert-danger'>No se pudo cargar la vista "${view}".</div>`;
                    }
                }

                await this.lazyLoadModule(view);
            });
        }
    }

    async fetchPartialView(url) {
        const view = new URL(url, globalThis.location.origin).searchParams.get("view") || "panel";
        if (this.partialCache.has(url)) return this.partialCache.get(url);

        try {
            const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const html = await resp.text();
            this.partialCache.set(url, html);
            await this.partialCacheManager.savePartial(view, html);
            return html;
        } catch (err) {
            const cached = await this.partialCacheManager.getPartial(view);
            if (cached) {
                this._warn("Offline", `Vista "${view}" desde cache`);
                return cached;
            }
            throw err;
        }
    }

    // =============================
    // 🔹 Lazy loading de módulos
    // =============================
    async lazyLoadModule(view) {
        try {
            switch (view) {
                case "items": {
                    const { loadItemUser } = await import("../modules/items.js");
                    await loadItemUser(1, this);
                    break;
                }
                case "chat": {
                    const { initChatModule } = await import("../modules/chat.js");
                    initChatModule(this);
                    break;
                }
                case "tokens": {
                    const { initTokenPanel } = await import("../modules/tokens.js");
                    initTokenPanel(this);
                    break;
                }
                default:
                    this._debug("LazyLoad", `Sin módulo para ${view}`);
            }
        } catch (err) {
            this._warn("LazyLoad", `Error cargando módulo ${view}:`, err);
        }
        finally {
            document.dispatchEvent(new CustomEvent("module:loaded", { detail: { view } }));
        }
    }

    // =============================
    // 🔹 Precarga silenciosa
    // =============================
    async lazyPreload() {
        this._debug("Preload", "Precargando módulos en background...");
        const preloadViews = ["items", "chat"];
        for (const v of preloadViews) {
            try {
                await this.lazyLoadModule(v);
            } catch {
                continue;
            }
        }
    }
}

// =============================
// 🔹 Bootstrap
// =============================
function bootstrapDashboard() {
    const dashboard = new UserDashboard();
    dashboard.init().then(() => {
        document.dispatchEvent(new CustomEvent("session:change", {
            detail: { loggedIn: true, role: dashboard.userCache?.user_rol }
        }));
    });
}

if (document.readyState === "loading") {
    document.addEventListener("layout:ready", bootstrapDashboard, { once: true });
} else {
    bootstrapDashboard();
}
