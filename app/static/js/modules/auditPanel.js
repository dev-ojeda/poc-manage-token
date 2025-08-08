import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
import { emit } from "../utils/eventBus.js";
export class AuditPanel {
    constructor(containerSelector = '#audit-panel') {
        this.container = document.querySelector(containerSelector);
        if (!this.container) {
            console.warn(`AuditPanel: No se encontró el contenedor ${containerSelector}`);
            return;
        }
        this.api_admin = new ApiAdmin({
            baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
            storage: new LocalStorageAdapter()
        });
        this.events = [];
    }

    async loadFromAPI({ start = null, end = null } = {}) {
        try {
            const body = {};
            if (start) body.start = start;
            if (end) body.end = end;

            const res = await this.api_admin.post("/api/admin/audit", body);
            if (Array.isArray(res.logs)) {
                res.logs.forEach(log => {
                    this.addEvent({
                        type: this.classify(log.reason),
                        detail: `${log.reason} desde IP ${log.ip_address}`,
                        timestamp: log.timestamp
                    });
                });
                // después de procesar logs:
                emit('auditLogsLoaded', res.logs);
            }

        } catch (error) {
            console.error("Error al cargar eventos del backend:", error);
        }
    }

    classify(reason) {
        const suspiciousKeywords = ["reuso", "múltiple", "bloqueado", "revocado"];
        return suspiciousKeywords.some(kw => reason.toLowerCase().includes(kw))
            ? "suspicious"
            : "normal";
    }

    addEvent({ type, detail, timestamp = new Date() }) {
        const event = {
            type,
            detail,
            timestamp: new Date(timestamp),
        };

        this.events.unshift(event);
        this.render();
    }

    render() {
        this.container.innerHTML = this.events.map(event => this.formatEvent(event)).join('');
    }

    formatEvent({ type, detail, timestamp }) {
        const time = timestamp.toLocaleString();
        const color = type === 'suspicious' ? 'bg-danger text-white' : 'bg-secondary text-light';
        return `
            <div class="card mb-2 ${color}">
                <div class="card-body p-2">
                    <strong>[${type.toUpperCase()}]</strong> ${detail}
                    <div class="text-end small"><i>${time}</i></div>
                </div>
            </div>
        `;
    }
}
