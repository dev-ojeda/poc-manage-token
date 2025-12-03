// ==============================
// Auditoría de métricas usuario (consolidado)
// ==============================
export function initUserPerformanceAudit(user_name) {
    if (!("PerformanceObserver" in window)) {
        console.warn("PerformanceObserver no soportado en este navegador.");
        return;
    }

    const metrics = {
        username: user_name,
        role: "User",
        LCP: null,
        INP: null,
        CLS: 0,
        timestamp: new Date().toISOString()
    };

    // Largest Contentful Paint
    try {
        const lcpObserver = new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            metrics.LCP = lastEntry.renderTime || lastEntry.loadTime;
        });
        lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
    } catch (e) { }

    // Interaction to Next Paint (INP)
    try {
        const inpObserver = new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                metrics.INP = entry.duration;
            }
        });
        inpObserver.observe({ type: "event", buffered: true });
    } catch (e) { }

    // Cumulative Layout Shift (CLS acumulado)
    try {
        const clsObserver = new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                    metrics.CLS += entry.value;
                }
            }
        });
        clsObserver.observe({ type: "layout-shift", buffered: true });
    } catch (e) { }

    // 🔹 Enviar métricas cuando la página termine de cargar
    window.addEventListener("load", () => {
        setTimeout(() => {
            fetch("/api/auth/metrics", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(metrics)
            })
                .then(() => console.log("📡 Métricas enviadas:", metrics))
                .catch(err => console.error("❌ Error enviando métricas:", err));
        }, 3000); // espera 3s para asegurar que LCP/INP/CLS se registren
    });
}