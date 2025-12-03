export class OfflineDataManager {
    constructor(storage) {
        this.db = storage;
    }

    async saveUserInfo(user) {
        await this.db.put("user_info", { id: "current", ...user });
    }

    async getUserInfo() {
        return (await this.db.get("user_info", "current")) || null;
    }

    async saveItems(items) {
        await this.db.put("user_items", { id: "latest", items, timestamp: Date.now() });
    }

    async getItems() {
        const data = await this.db.get("user_items", "latest");
        return data?.items || [];
    }
}
