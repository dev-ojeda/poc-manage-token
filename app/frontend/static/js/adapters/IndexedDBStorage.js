export class IndexedDBStorage {
    constructor(dbName = "AuthDB", storeName = "tokens") {
        this.dbName = dbName;
        this.storeName = storeName;
        this.db = null;
    }

    async _init() {
        if (this.db) return this.db;
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);
            request.onerror = e => reject(e.target.error);
            request.onsuccess = e => {
                this.db = e.target.result;
                resolve(this.db);
            };
            request.onupgradeneeded = e => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName);
                }
            };
        });
    }

    async getAllKeys() {
        const db = await this._init();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readonly");
            const store = tx.objectStore(this.storeName);
            const req = store.getAllKeys();
            req.onsuccess = () => resolve(req.result);
            req.onerror = e => reject(e.target.error);
        });
    }

    async clearAll() {
        const db = await this._init();
        const keys = await this.getAllKeys();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readwrite");
            const store = tx.objectStore(this.storeName);
            for (const key of keys) store.delete(key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }

    async set(key, value) {
        const db = await this._init();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).put(value, key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }

    async get(key) {
        const db = await this._init();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readonly");
            const store = tx.objectStore(this.storeName);
            const req = store.get(key);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async delete(key) {
        const db = await this._init();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).delete(key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }

    async clear() {
        const db = await this._init();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).clear();
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }

    async put(storeName, value, key = value.id) {
        const db = await this._init();
        if (!db.objectStoreNames.contains(storeName)) {
            db.close();
            await new Promise((resolve, reject) => {
                const req = indexedDB.open(this.dbName, db.version + 1);
                req.onupgradeneeded = e => {
                    e.target.result.createObjectStore(storeName);
                };
                req.onsuccess = e => {
                    this.db = e.target.result;
                    resolve();
                };
                req.onerror = e => reject(e.target.error);
            });
        }
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, "readwrite");
            tx.objectStore(storeName).put(value, key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = e => reject(e.target.error);
        });
    }

}
