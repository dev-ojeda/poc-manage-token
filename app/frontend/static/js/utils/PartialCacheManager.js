export class PartialCacheManager {
    constructor(storage) {
        this.db = storage;
    }

    async savePartial(view, html) {
        try {
            await this.db.put("partials", { id: view, html, timestamp: Date.now() });
        } catch (err) {
            console.warn("No se pudo guardar parcial:", view, err);
        }
    }

    async getPartial(view) {
        try {
            const data = await this.db.get("partials", view);
            return data?.html || null;
        } catch {
            return null;
        }
    }
}
