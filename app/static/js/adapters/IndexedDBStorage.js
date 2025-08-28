export class IndexedDBStorage {
    constructor(dbName = "AuthDB", storeName = "tokens") {
        this.dbName = dbName;
        this.storeName = storeName;
        this.db = null;
        this.ready = this._init(); // 👈 devuelve Promise
    }

    async _init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);
            request.onerror = (event) => reject(event.target.error);
            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName);
                }
            };
        });
    }

    async getAllKeys() {
        await this.ready;
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readonly");
            const store = tx.objectStore(this.storeName);
            const req = store.getAllKeys();

            req.onsuccess = () => resolve(req.result);
            req.onerror = (e) => reject(e.target.error);
        });
    }

    async clearAll() {
        await this.ready;
        const keys = await this.getAllKeys();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            const store = tx.objectStore(this.storeName);

            keys.forEach((key) => store.delete(key));

            tx.oncomplete = () => resolve(true);
            tx.onerror = (e) => reject(e.target.error);
        });
    }
    async set(key, value) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).put(value, key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = (e) => reject(e);
        });
    }

    async get(key) {
        await this.ready; // 👈 esperar siempre
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readonly");
            const store = tx.objectStore(this.storeName);
            const req = store.get(key);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async delete(key) {
        await this.ready; // 👈 esperar siempre
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).delete(key);
            tx.oncomplete = () => resolve(true);
            tx.onerror = (e) => reject(e);
        });
    }

    async clear() {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(this.storeName, "readwrite");
            tx.objectStore(this.storeName).clear();
            tx.oncomplete = () => resolve(true);
            tx.onerror = (e) => reject(e);
        });
    }
}