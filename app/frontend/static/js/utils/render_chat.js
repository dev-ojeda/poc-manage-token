import { state } from "../utils/states.js";
import { fetchMetricsEndpoint, fetchAlerts } from "../utils/api.js";
import { renderOrUpdateChart, getColor, updateLastRefresh, safeMetric, resetCanvas } from "../utils/helper.js";
import { showAlert } from "../layout.js";

// =========================
// Gráfico en tiempo real
// =========================
export function initRealtime() {
    const ctx = document.getElementById("realtimeChart");
    if (!ctx) return;

    const labels = Array.from({ length: 30 }).map((_, i) => i);
    const data = labels.map(() => Math.random() * 100 + 100);

    renderOrUpdateChart("realtime", ctx, {
        type: "line",
        data: { labels, datasets: [{ label: "Requests/s", data }] },
        options: { animation: false, responsive: true, maintainAspectRatio: false }
    });
}

// =========================
// Gráfico por categoría
// =========================
export function renderCategoryChart(metrics) {
    const ctx = document.getElementById("categoryChart");
    if (!ctx) return;

    const labels = metrics.map(m => m.name);
    const data = metrics.map(m => m.avg);

    renderOrUpdateChart("category", ctx, {
        type: "bar",
        data: { labels, datasets: [{ label: "Avg", data }] },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

export async function renderUnifiedTimeline(ctxGlobal, containerEndpoints, category = "endpoint", interval = "minute", limit = 50) {
    const api_admin = state.apiAdmin;
    if (!api_admin) {
        showAlert("❌ Cliente API no inicializado", "danger");
        return;
    }

    let series = [];
    let alerts = [];

    try {
        const res = await api_admin.fetchTimeline(category, interval, limit);
        if (Array.isArray(res)) {
            series = res;
        } else {
            series = res?.metrics ?? [];
            alerts = res?.alerts ?? [];
        }
    } catch (err) {
        showAlert("❌ Error al obtener timeline: " + err.message, "danger");
        return;
    }

    if (!series.length) {
        showAlert("⚠ No hay métricas para renderizar.", "warning");
        return;
    }

    // --- Preparar buckets únicos ---
    const labels = [...new Set(series.map(r => r.bucket))].sort();

    // --- Agrupar por endpoint ---
    const grouped = groupByEndpoint(series);

    // --- Render gráfico global ---
    const avg = labels.map(lbl => {
        const values = series.filter(r => r.bucket === lbl).map(r => r.avg ?? null);
        return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    });
    const min = labels.map(lbl => Math.min(...series.filter(r => r.bucket === lbl).map(r => r.min ?? Infinity)));
    const max = labels.map(lbl => Math.max(...series.filter(r => r.bucket === lbl).map(r => r.max ?? -Infinity)));

    renderOrUpdateChart("globalChart", ctxGlobal, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "Avg", data: avg, borderColor: "blue", tension: 0.3 },
                { label: "Min", data: min, borderColor: "green", borderDash: [5, 5], tension: 0.3 },
                { label: "Max", data: max, borderColor: "red", borderDash: [5, 5], tension: 0.3 },
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: `Promedio Global (${category})` },
                annotation: {
                    annotations: {
                        highLatency: {
                            type: "line",
                            yMin: 2000, yMax: 2000,
                            borderColor: "red", borderWidth: 2,
                            label: { content: "⚠ Límite 2000ms", enabled: true, position: "start", color: "red", font: { weight: "bold" } }
                        }
                    }
                }
            },
            scales: { x: { title: { display: true, text: "Tiempo" } }, y: { title: { display: true, text: "Duración (ms)" } } }
        }
    });

    // --- Render gráficos por endpoint ---
    if (!containerEndpoints) return;
    containerEndpoints.innerHTML = "";

    Object.entries(grouped).forEach(([endpoint, rows], idx) => {
        const wrapper = document.createElement("div");
        wrapper.className = "chart-container";
        wrapper.innerHTML = `<h2>${endpoint}</h2><canvas id="chart-${idx}" height="120"></canvas>`;
        containerEndpoints.appendChild(wrapper);

        const ctx = wrapper.querySelector("canvas").getContext("2d");
        const dataset = labels.map(lbl => rows.find(r => r.bucket === lbl)?.avg ?? null);

        const color = getColor(idx);
        new Chart(ctx, {
            type: "line",
            data: { labels, datasets: [{ label: endpoint, data: dataset, borderColor: color, backgroundColor: "transparent", tension: 0.3 }] },
            options: {
                plugins: {
                    title: { display: true, text: endpoint },
                    annotation: {
                        annotations: alerts
                            .filter(a => a.page.includes(endpoint) && a.metric === category)
                            .map((a, i) => ({
                                type: "line",
                                yMin: a.threshold,
                                yMax: a.threshold,
                                borderColor: "red",
                                borderWidth: 2,
                                label: { content: `⚠ ${a.metric} > ${a.threshold}`, enabled: true, position: "start", color: "red", font: { weight: "bold" } }
                            }))
                    }
                },
                scales: { x: { title: { display: true, text: "Tiempo" } }, y: { title: { display: true, text: "Duración (ms)" } } }
            }
        });
    });
}

export async function renderMetricsChart(ctx) {
    const updateEl = document.getElementById("lastUpdateMecticsChart");

    const metricsEndpoint = await fetchMetricsEndpoint();
    const { summary } = await metricsEndpoint.json() ?? {};
    if (!summary) return;

    const metricsAlert = await fetchAlerts();
    const alerts = await metricsAlert.json();
    const pages = Object.keys(summary.pages);
    const METRICS = ["LCP", "FID", "CLS", "INP", "TTFB"];

    const datasets = [];
    const colors = {
        LCP: "rgba(75,192,192,0.7)",
        FID: "rgba(255,206,86,0.7)",
        CLS: "rgba(255,99,132,0.7)",
        INP: "rgba(54,162,235,0.7)",
        TTFB: "rgba(153,102,255,0.7)",
        endpoint: "rgba(100,100,100,0.7)"
    };

    // --- Frontend metrics
    METRICS.forEach(metric => {
        const avgValues = pages.map(p => safeMetric(summary.pages[p], metric)?.avg || 0);
        const bgColors = pages.map(
            p => alerts.find(a => a.page === p && a.metric === metric)
                ? "rgba(255,0,0,0.8)"
                : colors[metric]
        );
        datasets.push({ label: `${metric} (frontend)`, data: avgValues, backgroundColor: bgColors });
    });

    // --- Threshold lines
    const annotations = {};
    METRICS.forEach(metric => {
        const t = summary.global?.[metric]?.threshold;
        if (t !== undefined) {
            annotations[`line_${metric}`] = {
                type: "line",
                yMin: t, yMax: t,
                borderColor: "red",
                borderWidth: 2,
                label: { content: `${metric} umbral`, enabled: true, position: "end", backgroundColor: "rgba(255,0,0,0.7)" }
            };
        }
    });

    renderOrUpdateChart("metrics", ctx.getContext("2d"), {
        type: "bar",
        data: { labels: pages, datasets },
        options: {
            responsive: true,
            plugins: { title: { display: true, text: "Frontend + Backend Metrics" }, annotation: { annotations } },
            scales: { y: { beginAtZero: true } }
        }
    });

    updateLastRefresh(updateEl);
}

export function renderChartByCategory(grouped) {
    const container = document.getElementById("charts");
    container.innerHTML = "";

    const colors = [
        "#FF6384", "#36A2EB", "#FFCE56",
        "#4BC0C0", "#9966FF", "#FF9F40"
    ];

    Object.entries(grouped).forEach(([category, metric]) => {
        const canvasId = `chart-${category}`;
        const ctx = resetCanvas(canvasId, "charts");

        const datasets = Object.entries(metric).map(([metric, values], i) => ({
            label: metric,
            data: values, // [{x, y}, ...]
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length],
            tension: 0.3,
            pointRadius: 2,
        }));

        new Chart(ctx, {
            type: "line",
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: `Category: ${category}` },
                    legend: { position: "bottom" }
                },
                scales: {
                    x: {
                        type: "time",
                        time: { unit: "hour" },
                        title: { display: true, text: "Tiempo" }
                    },
                    y: {
                        title: { display: true, text: "Valor (avg)" }
                    }
                }
            }
        });
    });
}

export function renderEndpointCharts(groups) {
    const container = document.getElementById("endpointCharts");
    container.innerHTML = "";

    Object.entries(groups).forEach(([page, metrics], idx) => {
        const wrapper = document.createElement("div");
        wrapper.className = "chart-container";
        wrapper.innerHTML = `<h2>${page}</h2><canvas id="chart-${idx}" height="120"></canvas>`;
        container.appendChild(wrapper);

        const ctx = wrapper.querySelector("canvas").getContext("2d");
     
        const labels = Object.keys(metrics);
        const data = labels.map((m) => metrics[m].p75 || metrics[m].avg);
        const thresholds = labels.map((m) => metrics[m].threshold);

        new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Valor (p75)",
                        data,
                        backgroundColor: "rgba(75, 192, 192, 0.6)"
                    },
                    {
                        label: "Umbral",
                        data: thresholds,
                        backgroundColor: "rgba(255, 159, 64, 0.4)"
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: `Página: ${page}` }
                }
            }
        });
    });
}

export function renderGlobalChart(summary, ctxElement) {
    const labels = Object.keys(summary);
    const data = labels.map((m) => summary[m].p75 || summary[m].avg);
    const thresholds = labels.map((m) => summary[m].threshold);

    renderOrUpdateChart("globalChart", ctxElement, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Valor (p75)",
                    data,
                    backgroundColor: "rgba(54, 162, 235, 0.6)"
                },
                {
                    label: "Umbral",
                    data: thresholds,
                    backgroundColor: "rgba(255, 99, 132, 0.4)"
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: "Resumen Global" }
            }
        }
    });
}

// =========================
// Timeline (ej. endpoints)
// =========================
export async function renderTimelineChart(timeline, ctxElement) {
    const buckets = Object.keys(timeline).sort();
    const datasets = [];
    const seriesByKey = {};
    buckets.forEach((bucket) => {
        timeline[bucket].forEach((row) => {
            const key = `${row.method} ${row.url}`;
            if (!seriesByKey[key]) seriesByKey[key] = [];
            seriesByKey[key].push({ x: bucket, y: row.avg });
        });
    });
    Object.entries(seriesByKey).forEach(([label, data]) => {
        datasets.push({
            label,
            data,
            borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
            tension: 0.3,
            fill: false
        });
    });
    renderOrUpdateChart("timeline", ctxElement, {
        type: "line",
        data: { datasets },
        options: {
            responsive: true,
            scales: {
                x: { type: "time", time: { unit: "minute" } }
            },
            plugins: {
                title: { display: true, text: "Timeline de Endpoints" }
            }
        }
    });
}

// =========================
// API Metrics (tabla + gráfico)
// =========================
export function renderMetricsApi(ctx) {
    const tbody = document.querySelector("#metricsTable tbody");
    tbody.innerHTML = "";

    const metrics = state.apiMetrics.slice(-10);
    const rows = metrics.map(m => `
    <tr>
      <td>${m.url}</td>
      <td><span class="badge bg-dark">${m.method}</span></td>
      <td>${m.duration}</td>
      <td>${m.transferSizeKB.toFixed(1)}</td>
    </tr>`
    ).join("");
    tbody.innerHTML = rows;

    renderOrUpdateChart("durationChart", ctx.getContext("2d"), {
        type: "line",
        data: {
            labels: metrics.map((_, i) => i + 1),
            datasets: [{ label: "Duración (ms)", data: metrics.map(m => m.duration), borderColor: "#28a745", fill: false, tension: 0.3 }]
        },
        options: { responsive: true, plugins: { legend: { display: true } }, scales: { x: { title: { display: true, text: "Requests" } }, y: { title: { display: true, text: "ms" } } } }
    });
}
