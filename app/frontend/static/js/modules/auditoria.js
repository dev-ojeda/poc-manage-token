import { showGlobalAlert } from "../layout.js";

// ==========================
// Constantes y estado
// ==========================
const suspiciousKeywords = [
    "ip_change",
    "user_agent_change",
    "revoked",
    "logout",
    "expiration",
    "login",
    "refresh_token",
    "session_update",
    "multiple_attempts"
];


// ==============================
// Variables globales auditoría
// ==============================
let apiAdminRef = null;
let auditLogs = [];           // todos los logs cargados desde backend
let filteredLogs = [];        // logs después de aplicar filtros
let currentAuditPage = 1;     // página actual
const limit = 10;             // registros por página
let currentSortColumn = "timestamp";
let currentSortDirection = "desc";

// ==========================
// Carga de logs de auditoría
// ==========================
export async function loadAuditLogs(page = 1, api_admin = null) {
    if (api_admin) apiAdminRef = api_admin;
    if (!apiAdminRef) {
        showGlobalAlert("❌ No se inicializó el cliente API", "danger");
        return;
    }
    try {
        showTableSpinner(); // 🔹 spinner ON
        const res = await apiAdminRef.loadAuditLogs();
        auditLogs = res.logs || [];
        filteredLogs = [...auditLogs]; // inicializamos
        sortLogs(currentSortColumn, currentSortDirection);
        hideTableSpinner(); // 🔹 spinner OFF
        renderTableLogs();
    } catch (error) {
        hideTableSpinner(); // 🔹 spinner OFF
        showGlobalAlert(`❌ ${error.message}`, "danger");
    }


    applyFilters();
}

// ==============================
// Filtros
// ==============================
function applyFilters() {
    const userId = document.getElementById("userIdInput")?.value.trim().toLowerCase() || "";
    const eventType = document.getElementById("eventFilter")?.value || "";
    const startDate = document.getElementById("filterStart")?.value;
    const endDate = document.getElementById("filterEnd")?.value;

    filteredLogs = auditLogs.filter(log => {
        const matchUser = !userId || (log.user_id || "").toLowerCase().includes(userId);
        const matchEvent = !eventType || log.event_type === eventType;
        const ts = new Date(log.timestamp);
        const matchStart = !startDate || ts >= new Date(startDate);
        const matchEnd = !endDate || ts <= new Date(endDate);
        return matchUser && matchEvent && matchStart && matchEnd;
    });

    sortLogs(currentSortColumn, currentSortDirection);
    currentAuditPage = 1;
    renderTableLogs();
}

// ==============================
// Ordenamiento
// ==============================
function sortLogs(column, direction) {
    currentSortColumn = column;
    currentSortDirection = direction;

    filteredLogs.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        if (column === "user_id") {
            valA = (valA || "").toLowerCase();
            valB = (valB || "").toLowerCase();
            const result = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: "base" });
            if (result !== 0) return direction === "asc" ? result : -result;
        }
        else if (column === "timestamp") {
            valA = new Date(valA);
            valB = new Date(valB);
            if (valA < valB) return direction === "asc" ? -1 : 1;
            if (valA > valB) return direction === "asc" ? 1 : -1;
        }
        return 0;
    });
}
// ==========================
// Renderizado de tabla
// ==========================
function renderTableLogs() {

    const tbody = document.querySelector("#logsTable tbody");
    if (!tbody) return;
    // 🔹 ordenar ANTES de paginar
    sortLogs(currentSortColumn, currentSortDirection);
    tbody.innerHTML = "";
    const start = (currentAuditPage - 1) * limit;
    const pageData = filteredLogs.slice(start, start + limit);
    if (!pageData.length) {
        tbody.innerHTML = "<tr><td colspan='4' class='text-center'>Sin registros</td></tr>";
        updatePageIndicator();
        return;
    }
    let html = "";
    pageData.forEach((log, index) => {
        const uniqueId = `details-${log.user_id || index}`;
        html += `
        <tr class="audit-summary" data-bs-toggle="collapse" data-bs-target="#${uniqueId}">
            <td class="border border-primary"><span class="toggle-icon me-2">➕</span> ${formatDateIso(log.timestamp)}</td>
            <td class="border border-warning ${getEventClass(log.event_type)}">${log.event_type || "-"}</td>
            <td class="border border-success">${log.user_id || "-"}</td>
            <td class="border border-info">${log.ip_address || "-"}</td>
        </tr>
        <tr class="collapse" id="${uniqueId}">
            <td class="border border-info" colspan="4">${buildDetailsHtml(log)}</td>
        </tr>
    `;
    });
    tbody.innerHTML = html;
    //  🔹 ordenar antes de renderizar
    updatePageIndicator();
}

// ==========================
// Renderizado de detalles
// ==========================
function getEventClass(eventType) {
    if (!isSuspicious(eventType)) return "";
    switch (eventType) {
        case "ip_change":
        case "user_agent_change":
        case "session_update":
        case "refresh_token": return "bg-warning text-dark";
        case "revoked":
        case "multiple_attempts":
        case "revoked": return "bg-danger text-white";
        default: return "bg-primary text-white";
    }
}

function buildDetailsHtml(log) {
    let html = "<ul class='mb-0'>";
    //if (log.user_agent) html += `<li><strong>User Agent:</strong> ${log.user_agent}</li>`;

    if (log.changes && Object.keys(log.changes).length) {
        for (const [key, change] of Object.entries(log.changes)) {
            html += `<li><strong>${key}:</strong> ${change.old || "-"} → ${change.new}</li>`;
        }
    }
    return html + "</ul>";
}
function isSuspicious(eventType) {
    return suspiciousKeywords.includes(eventType);
}
// ==========================
// Listeners y filtros
// ==========================


// Debounce genérico
function debounce(fn, delay = 400) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}
// ==========================
// Paginación
// ==========================
function updatePageIndicator() {
    const indicator = document.getElementById("pageIndicatorLog");
    if (!indicator) return;

    const totalPages = Math.max(1, Math.ceil(filteredLogs.length / limit));
    indicator.textContent = `Página ${currentAuditPage} de ${totalPages}`;

    // Deshabilitar botones según contexto
    document.getElementById("firstPageLog").disabled = currentAuditPage === 1;
    document.getElementById("prevPageLog").disabled = currentAuditPage === 1;
    document.getElementById("nextPageLog").disabled = currentAuditPage === totalPages;
    document.getElementById("lastPageLog").disabled = currentAuditPage === totalPages;
}

function updateSortIndicators() {
    const ths = document.querySelectorAll("#logsTable th[data-sort]");
    ths.forEach(th => {
        th.classList.remove("sort-asc", "sort-desc");

        // Limpia el contenido y vuelve a poner el label original
        th.innerHTML = th.dataset.label || th.textContent;

        if (th.dataset.sort === currentSortColumn) {
            th.classList.add(currentSortDirection === "asc" ? "sort-asc" : "sort-desc");

            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
            svg.setAttribute("width", "14");
            svg.setAttribute("height", "14");
            svg.setAttribute("viewBox", "0 0 24 24");
            svg.setAttribute("fill", "none");
            svg.setAttribute("stroke", "currentColor");
            svg.setAttribute("stroke-width", "2");
            svg.setAttribute("stroke-linecap", "round");
            svg.setAttribute("stroke-linejoin", "round");
            svg.style.marginLeft = "5px";
            svg.innerHTML = currentSortDirection === "asc"
                ? `<polyline points="18 15 12 9 6 15"></polyline>`   // flecha arriba
                : `<polyline points="6 9 12 15 18 9"></polyline>`; // flecha abajo

            th.appendChild(svg);
        }
    });
}

// ==============================
// Eventos UI
// ==============================
document.getElementById("applyFilters")?.addEventListener("click", applyFilters);
document.getElementById("firstPageLog")?.addEventListener("click", () => {
    currentAuditPage = 1; // 🔹 primera página
    renderTableLogs();
});
document.getElementById("prevPageLog")?.addEventListener("click", () => {
    if (currentAuditPage > 1) {
        currentAuditPage--;
        sortLogs(currentSortColumn, currentSortDirection); // 🔹 asegura orden
        renderTableLogs();
    }
});

document.getElementById("nextPageLog")?.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredLogs.length / limit);
    if (currentAuditPage < totalPages) {
        currentAuditPage++;
        sortLogs(currentSortColumn, currentSortDirection); // 🔹 asegura orden
        renderTableLogs();
    }
});
document.getElementById("lastPageLog")?.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredLogs.length / limit);
    currentAuditPage = totalPages; // 🔹 última página
    renderTableLogs();
});
document.getElementById("goToPageLog")?.addEventListener("click", () => {
    const input = document.getElementById("jumpToPageLog");
    const page = parseInt(input.value, 10);

    const totalPages = Math.ceil(filteredLogs.length / limit);
    if (!isNaN(page) && page >= 1 && page <= totalPages) {
        currentAuditPage = page;
        renderTableLogs();
    } else {
        showGlobalAlert(`❌ Número de página inválido. (1 - ${totalPages})`, "danger");
    }
});

document.querySelectorAll("#logsTable th[data-sort]")?.forEach(th => {
    th.addEventListener("click", () => {
        const col = th.dataset.sort;
        const dir = (currentSortColumn === col && currentSortDirection === "asc") ? "desc" : "asc";
        sortLogs(col, dir);
        renderTableLogs();
        updateSortIndicators(); // 🔹 aquí metemos los SVGs
    });
});

// Users - limpiar filtros
document.getElementById("clearFilters")?.addEventListener("click", () => {
    document.getElementById("userIdInput").value = "";
    document.getElementById("eventFilter").value = "";
    document.getElementById("filterStart").value = "";
    document.getElementById("filterEnd").value = "";

    // Recarga listado users sin filtros
    loadAuditLogs();
});


document.addEventListener("show.bs.collapse", (e) => {
    const collapseEl = e.target; // <tr id="details-...">
    // preferimos previousElementSibling (devuelve solo nodos element)
    const summaryRow = collapseEl.previousElementSibling
        || document.querySelector(`tr.audit-summary[data-bs-target="#${collapseEl.id}"]`);
    const icon = summaryRow?.querySelector(".toggle-icon");
    if (icon) icon.textContent = "➖";
});

document.addEventListener("hide.bs.collapse", (e) => {
    const collapseEl = e.target;
    const summaryRow = collapseEl.previousElementSibling
        || document.querySelector(`tr.audit-summary[data-bs-target="#${collapseEl.id}"]`);
    const icon = summaryRow?.querySelector(".toggle-icon");
    if (icon) icon.textContent = "➕";
});
// ==========================
// Utilidades
// ==========================
function formatDateIso(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    return `${date.getDate().toString().padStart(2, "0")}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getFullYear()}`;
}

export async function loadMockData() {
    const res = await fetch("./audit-mock.json");
    const logs = await res.json();
    auditLogs = logs || [];
    filteredLogs = [...auditLogs]; // inicializamos
    applyFilters();
}

function showTableSpinner() {
    const tbody = document.querySelector("#logsTable tbody");
    const columnCount = document.querySelectorAll("#logsTable thead th").length || 4;
    if (!tbody) return;
    tbody.innerHTML = `
        <tr>
          <td colspan="${columnCount}" class="table-spinner">
            <span class="loader"></span>
          </td>
        </tr>
    `;
}

function hideTableSpinner() {
    const tbody = document.querySelector("#logsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = ""; // limpiar antes de renderizar los datos
}
// Para pruebas sin backend
//loadMockData();