// =========================
// Clase Auditoría de Performance
// =========================
export class PerformanceAudit {
    constructor(sendAuditLogFn) {
        if (typeof sendAuditLogFn !== "function") {
            throw new Error("Debes proporcionar una función sendAuditLog");
        }
        this.sendAuditLog = sendAuditLogFn;
        this.observers = [];
    }

    init() {
        if (!("PerformanceObserver" in window)) {
            console.warn("PerformanceObserver no soportado en este navegador.");
            return;
        }

        this.observeLCP();
        this.observeFID();
    }

    observeLCP() {
        const lcpObserver = new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            if (lastEntry) {
                this.sendAuditLog({
                    metric: "LCP",
                    value: lastEntry.startTime, // ms
                    element: lastEntry.element?.tagName || null,
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                });
            }
        });
        lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
        this.observers.push(lcpObserver);
    }

    observeFID() {
        const fidObserver = new PerformanceObserver((entryList) => {
            entryList.getEntries().forEach((entry) => {
                this.sendAuditLog({
                    metric: "FID",
                    inputDelay: entry.processingStart - entry.startTime,
                    processingDuration: entry.duration,
                    target: entry.target?.tagName || null,
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                });
            });
        });
        fidObserver.observe({ type: "first-input", buffered: true });
        this.observers.push(fidObserver);
    }

    disconnect() {
        this.observers.forEach((observer) => observer.disconnect());
        this.observers = [];
    }
}

//// =========================
//// Ejemplo de uso
//// =========================
//const audit = new PerformanceAudit((data) => {
//    console.log("Audit Log:", data);
//    // Aquí podrías enviar a tu API con fetch()
//    // fetch("/api/audit", { method: "POST", body: JSON.stringify(data) });
//});

//audit.init();
