import { state } from '../utils/states.js';

export function initPerformanceAudit({
    enableHooks = false,
    debounceTime = 500,
    batchInterval = 2000,
    maxRetries = 2,
    retryDelay = 500,
    sendToBackendAPI,
    debug = false,
    onUpdate = null
} = {}) {

    class PerformanceAudit {
        constructor() {
            this.observers = [];

            this.apiQueue = [];

            this.apiDebounce = null;

            this.apiBatch = null;

            this.sendingAPI = false;

            this.browser = state.browser;
            this.os = state.os;
            this.page = state.page;
            this.url = state.url;
            this.metric_id = state.metric_id;
        }

        init() {
            this.initObservers();
        }

        initObservers() {
            if (!("PerformanceObserver" in window)) return;

            // ========== API metrics ==========
            const apiObs = new PerformanceObserver(list => {
                list.getEntries().forEach(entry => {
                    if (!["fetch", "xmlhttprequest"].includes(entry.initiatorType)) return;

                    const data = {
                        type: "endpoint",
                        category: "apiresponsetime",
                        url: entry.name,
                        page: this.page,
                        method: entry.name.includes("POST") ? "POST" :
                            entry.name.includes("PUT") ? "PUT" : "GET",
                        value: parseFloat(entry.duration.toFixed(2)),
                        transferSizeKB: entry.transferSize ? entry.transferSize / 1024 : 0,
                        browser: this.browser,
                        os: this.os,
                        metric_id: this.metric_id,
                        timestamp: Date.now()
                    };

                    if (debug) console.log("Captured API metric:", data);
                    this.enqueueAPI(data);
                });
            });
            apiObs.observe({ type: "resource", buffered: true });
            this.observers.push(apiObs);

        }

       

        // =======================
        // Enqueue API Metrics
        // =======================
        enqueueAPI(metric) {
            this.apiQueue.push(metric);

            if (onUpdate) {
                onUpdate({
                    type: "api",
                    count: this.apiQueue.length
                });
            }

            if (this.apiDebounce) clearTimeout(this.apiDebounce);
            this.apiDebounce = setTimeout(() => this.sendAPI(), debounceTime);

            if (!this.apiBatch) {
                this.apiBatch = setTimeout(() => this.sendAPI(), batchInterval);
            }
        }

        async sendAPI() {
            if (this.sendingAPI || this.apiQueue.length === 0) return;

            this.sendingAPI = true;
            const batch = [...this.apiQueue];
            this.apiQueue = [];

            try {
                await this._postWithRetry(batch, sendToBackendAPI);
            } catch (err) {
                console.error("❌ Error enviando API metrics:", err);
                this.apiQueue.unshift(...batch);
            } finally {
                this.sendingAPI = false;
                clearTimeout(this.apiBatch);
                this.apiBatch = null;

                // 🔥 reset contador tras enviar
                if (onUpdate) {
                    onUpdate({
                        type: "api",
                        count: this.apiQueue.length // → siempre 0 aquí
                    });
                }
            }
        }
        async _postWithRetry(batch, sendFn, retries = maxRetries) {
            for (let i = 0; i <= retries; i++) {
                try {
                    await sendFn(batch);
                    if (debug) console.log("✅ Metrics sent:", batch.length);
                    return;
                } catch (err) {
                    if (i < retries) await new Promise(r => setTimeout(r, retryDelay));
                    else throw err;
                }
            }
        }
        start() {
            if (this.observers.length === 0) this.initObservers();
            console.log("✅ Auditoría iniciada");
        }

        stop() {
            this.disconnect();
            console.log("⏹ Auditoría detenida");
        }
        disconnect() {
            this.observers.forEach(o => o.disconnect());
            this.observers = [];

            clearTimeout(this.apiDebounce);
            clearTimeout(this.apiBatch);

            this.apiQueue = [];
        }
    }

    const audit = new PerformanceAudit();
    if (enableHooks) audit.init();
    return audit;
}
