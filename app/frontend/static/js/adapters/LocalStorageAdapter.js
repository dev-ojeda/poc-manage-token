// adapters/LocalStorageAdapter.js

export class LocalStorageAdapter {
    getItem(key) {
        return this.get(key);
    }

    setItem(key, value) {
        return this.set(key, value);
    }

    removeItem(key) {
        return this.remove(key);
    }

    countItem() {
        return this.count();
    }

    clear() {
        localStorage.clear();
    }

    get(key) {
        return localStorage.getItem(key);
    }

    set(key, value) {
        if (value === undefined) {
            console.warn(`[LocalStorageAdapter] Valor 'undefined' ignorado para clave '${key}'`);
            return;
        }
        localStorage.setItem(key, value);
    }

    remove(key) {
        localStorage.removeItem(key);
    }

    count() {
        return localStorage.length;
    }

    // Nuevos métodos para objetos
    setObject(key, obj) {
        try {
            const json = JSON.stringify(obj);
            this.set(key, json);
        } catch (e) {
            console.error(`[LocalStorageAdapter] Error al serializar objeto para '${key}':`, e);
        }
    }

    getObject(key) {
        const value = this.get(key);
        try {
            return JSON.parse(value);
        } catch (e) {
            console.warn(`[LocalStorageAdapter] Error al parsear objeto de '${key}':`, e);
            return null;
        }
    }
}
