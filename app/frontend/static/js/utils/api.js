import { nowISO } from '../utils/states.js';


const sampleMetrics = [
    { name: 'LCP', count: 120, avg: 2100, min: 1200, max: 4500, category: 'Rendering' },
    { name: 'FID', count: 95, avg: 110, min: 10, max: 500, category: 'Interactivity' },
    { name: 'CLS', count: 80, avg: 0.07, min: 0.01, max: 0.4, category: 'Stability' }
];

const sampleEndpoints = [
    { path: '/api/login', role: 'all', requests: 1023, avg: 120, max: 450 },
    { path: '/api/data', role: 'user', requests: 2031, avg: 230, max: 900 },
    { path: '/api/admin/stats', role: 'admin', requests: 312, avg: 410, max: 1200 }
];

export async function fetchMetrics(role = 'all') {
    await new Promise(r => setTimeout(r, 120)); // simula latencia
    return {
        metrics: sampleMetrics,
        endpoints: sampleEndpoints,
        errors: [{ msg: 'Error 500 en /api/data', ts: nowISO() }]
    };
}

/** Fetch de alertas */
export async function fetchAlerts() {
    try {
        const res = await fetch(`/api/metrics/alerts?last_hours=24`);
        return res;
    } catch (err) {
        console.error("Error fetching alerts:", err);
        return [];
    }
}

/** Fetch de resumen de métricas por endpoint */
export async function fetchMetricsEndpoint() {
    const res = await fetch(`/api/metrics/summary`);
    return res;
}

export async function fetchUnifiedMetrics(role = "User") {
    //const [endpointsRes, webvitalsRes, alertsRes] = await Promise.all([
    //    fetch(`/api/metrics/endpoints?role=${role}`).then(r => r.json()),
    //    fetch(`/api/metrics/webvitals?role=${role}`).then(r => r.json()),
    //    fetch(`/api/metrics/alerts?last_hours=24`).then(r => r.json())
    //]);

    const [timelineRs, alertsRes] = await Promise.all([
        fetch(`/api/metrics/endpoint/timeline?role=${role}`).then(r => r.json()),
        fetch(`/api/metrics/alerts?last_hours=24`).then(r => r.json())
    ]);

    return {
        timeline: timelineRs,
        alerts: alertsRes
    };
}

// Obtiene timeline desde backend
export async function fetchTimeline(category = "endpoint", interval = "minute", limit = 50) {
    const url = `/api/metrics/timeline`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Error cargando timeline");
    const data = await res.json();
    return data || [];
}
