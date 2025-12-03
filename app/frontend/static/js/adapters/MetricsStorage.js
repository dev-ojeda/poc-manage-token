// MetricsStorage.js
export class MetricsStorage {
    constructor() {
        this.dbName = "MetricsDB";
        this.storeName = "metrics";
        this.dbVersion = 3; // 👈 subimos versión para asegurar upgrade
        this.db = null;
        this.subscribers = [];
        this.ready = this._init(); // 👈 devuelve Promise
    }

    async _init() {
        if (this.db) return;

        this.db = await new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onupgradeneeded = e => {
                const db = e.target.result;
                let store;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    // Creamos store con keyPath "ts"
                    store = db.createObjectStore(this.storeName, { keyPath: "ts" });
                } else {
                    store = request.transaction.objectStore(this.storeName);
                }

                // 👇 Índices útiles para consultas
                if (!store.indexNames.contains("rol")) {
                    store.createIndex("rol", "rol", { unique: false });
                }
                if (!store.indexNames.contains("username")) {
                    store.createIndex("username", "username", { unique: false });
                }
            };

            request.onsuccess = e => resolve(e.target.result);
            request.onerror = e => reject(e.target.error);
        });
    }

    async set(metric) {
        await this.ready;
        if (!metric.ts) return;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).put(metric);
            tx.oncomplete = () => { this._notify(); resolve(); };
            tx.onerror = e => reject(e.target.error);
        });
    }

    async getAll() {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readonly");
            const request = tx.objectStore(this.storeName).getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = e => reject(e.target.error);
        });
    }

    async getByRole(role) {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readonly");
            const index = tx.objectStore(this.storeName).index("rol");
            const request = index.getAll(role);
            request.onsuccess = () => resolve(request.result);
            request.onerror = e => reject(e.target.error);
        });
    }

    async getByUser(username) {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readonly");
            const index = tx.objectStore(this.storeName).index("username");
            const request = index.getAll(username);
            request.onsuccess = () => resolve(request.result);
            request.onerror = e => reject(e.target.error);
        });
    }

    subscribe(fn) { this.subscribers.push(fn); }
    _notify() { this.subscribers.forEach(fn => fn()); }

    async clear() {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).clear();
            tx.oncomplete = () => resolve();
            tx.onerror = e => reject(e.target.error);
        });
    }

    async clearAll() {
        // 🔹 mismo que clear() pero semántico
        return this.clear();
    }

    async delete(key) {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).delete(key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }
}
