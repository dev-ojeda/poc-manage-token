// =========================
// Helpers genéricos para gráficos y métricas
// =========================

import { state } from "../utils/states.js";

// 🎨 Paleta fija de colores (evita random repetitivo)
const palette = [
    "#4dc9f6", "#f67019", "#f53794", "#537bc4",
    "#acc236", "#166a8f", "#00a950", "#58595b", "#8549ba"
];

export function getColor(i) {
    return palette[i % palette.length];
}

// 🔄 Crea o actualiza un gráfico Chart.js
export function renderOrUpdateChart(ref, ctx, config) {
    if (state.charts[ref]) {
        state.charts[ref].data = config.data;
        state.charts[ref].options = config.options;
        state.charts[ref].update();
    } else {
        state.charts[ref] = new Chart(ctx, config);
    }
}

// 📅 Actualiza la hora de última actualización
export function updateLastRefresh(el) {
    if (!el) return;
    const now = new Date().toLocaleString();
    el.textContent = `Última actualización: ${now}`;
    state.lastUpdate = now;
}

// 🔐 Acceso seguro a métricas
export function safeMetric(obj, key) {
    return obj?.[key] ?? null;
}

export function groupByCategory(data) {
    const grouped = {};
    const arr = Object.values(data);

    arr.forEach(item => {
        const { category, metric, bucket, avg } = item;

        if (!grouped[category]) grouped[category] = {};
        if (!grouped[category][metric]) grouped[category][metric] = [];

        grouped[category][metric].push({ x: bucket, y: avg });
    });

    return grouped;
}

export function transformData(data) {
    const grouped = {};

    Object.values(data).forEach(item => {
        const { category, metric, bucket, avg } = item;

        if (!grouped[category]) grouped[category] = {};
        if (!grouped[category][metric]) grouped[category][metric] = [];

        grouped[category][metric].push({
            x: new Date(bucket), // eje X = tiempo
            y: avg                // eje Y = promedio
        });
    });

    return grouped;
}

export function resetCanvas(id, parentId = "charts") {
    // Si existe, destruir el chart y el canvas
    const existingCanvas = document.getElementById(id);
    if (existingCanvas) {
        if (Chart.getChart(id)) {
            Chart.getChart(id).destroy();
        }
        existingCanvas.remove();
    }

    // Crear un nuevo canvas limpio dentro del contenedor
    const parent = document.getElementById(parentId);
    if (!parent) {
        console.error(`Parent container con id="${parentId}" no encontrado`);
        return null;
    }

    const newCanvas = document.createElement("canvas");
    newCanvas.id = id;
    newCanvas.className = "chart-container";
    parent.appendChild(newCanvas);

    return newCanvas.getContext("2d");
}

export function destroyCanvasById(id) {
    const canvas = document.getElementById(id);
    if (canvas) {
        // Si hay un gráfico de Chart.js asociado, destrúyelo primero
        if (Chart.getChart(id)) {
            Chart.getChart(id).destroy();
        }
        // Luego elimina el canvas del DOM
        canvas.remove();
    }
}


