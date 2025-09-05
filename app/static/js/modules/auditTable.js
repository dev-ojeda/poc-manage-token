import { showAlert } from "../layout.js";

// ==========================
// Constantes y estado
// ==========================
const suspiciousKeywords = [
    "ip_change",
    "user_agent_change",
    "revoked",
    "multiple_attempts",
    "logout",
    "expiration",
    "login",
    "refresh_token",
    "session_update"
];

let apiAdminRef = null;
let currentAuditPage = 1;
let totalPages = 1;
let lastLogsData = [];

const PAGE_SIZE = 10;
let currentSortColumn = "timestamp";   // default
let currentSortDirection = "desc";     // default
// ==========================
// Carga de logs de auditoría
// ==========================
export async function loadAuditLogs(page = 1, api_admin = null) {
    if (api_admin) apiAdminRef = api_admin;
    if (!apiAdminRef) {
        showAlert("❌ No se inicializó el cliente API", "danger");
        return;
    }

    const user_id = document.getElementById("userIdInput").value.trim() || "";
    const event_type = document.getElementById("eventFilter").value || "";
    const startDate = document.getElementById("filterStart").value; // UTC
    const endDate = document.getElementById("filterEnd").value;   // UTC
    const start = formatDateTs(startDate);
    const end = formatDateTs(endDate);
    try {
        const res = await apiAdminRef.post("/api/auth/admin/audit", {
            user_id,
            event_type,
            start,
            end,
            limit: PAGE_SIZE,
            page
        });

        lastLogsData = res.logs || [];
        currentAuditPage = page;
        totalPages = Math.ceil((res.total_count || lastLogsData.length) / PAGE_SIZE);

        renderTableLogs(lastLogsData, currentAuditPage);
        updatePageIndicator(currentAuditPage, res.total_count || lastLogsData.length, PAGE_SIZE);
        updatePaginationButtons();
    } catch (error) {
        showAlert(`❌ ${error.message}`, "danger");
    }
}

// ==========================
// Renderizado de tabla
// ==========================
function renderTableLogs(logs, page) {
    const sortedLogs = sortLogs([...logs]);
    const pageData = paginateLogs(sortedLogs, page, PAGE_SIZE);
    const tbody = document.querySelector("#logsTable tbody");
    tbody.innerHTML = "";

    if (!pageData.length) {
        tbody.innerHTML = "<tr><td colspan='8' class='text-center'>Sin registros</td></tr>";
        return;
    }
    pageData.forEach((log, index) => {
        const rowId = `details-${page}-${index}`;
        const trMain = document.createElement("tr");
        // 🔹 Fila principal con solo 4 columnas
        trMain.classList.add("audit-summary");
        trMain.setAttribute("data-bs-toggle", "collapse");
        trMain.setAttribute("data-bs-target", `#details-${index}`);
        trMain.innerHTML = `
            <td>${formatDateIso(log.timestamp)}</td>
            <td class="${getEventClass(log.event_type)}">${log.event_type || "-"}</td>
            <td>${log.user_id || "-"}</td>
            <td>${log.ip_address || "-"}</td>
        `;
        tbody.appendChild(trMain);

        // 🔹 Fila colapsable (detalles)
        const trDetails = document.createElement("tr");
        trDetails.classList.add("collapse");
        trDetails.id = rowId;
        trDetails.innerHTML = `<td colspan="4">${buildDetailsHtml(log)}</td>`;
        tbody.appendChild(trDetails);

    });
    //  🔹 ordenar antes de renderizar
    attachSortListeners();
    updateSortIcons();
}

// ==========================
// Renderizado de detalles
// ==========================
function getEventClass(eventType) {
    if (!isSuspicious(eventType)) return "";
    switch (eventType) {
        case "user_agent_change":
        case "session_update":
        case "refresh_token":
            return "bg-warning text-dark";
        case "revoked":
            return "bg-danger text-white";
        default:
            return "bg-primary text-white";
    }
}

function buildDetailsHtml(log) {
    let html = "<ul class='mb-0'>";
    if (log.user_agent) html += `<li><strong>User Agent:</strong> ${log.user_agent}</li>`;

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
export function attachAuditListeners(api_admin, reloadFn) {
    apiAdminRef = api_admin;

    // Prefiltro: últimos 7 días
    const today = new Date();
    const lastWeek = new Date();
    lastWeek.setDate(today.getDate() - 7);

    document.getElementById("filterStart").value = formatDateToInput(lastWeek);
    document.getElementById("filterEnd").value = formatDateToInput(today);

    initFilters(reloadFn)
    document.getElementById("prevPage").addEventListener("click", prevPage);
    document.getElementById("nextPage").addEventListener("click", nextPage);

    attachSortListeners();
}

export function initFilters(reloadFn) {
    ["userIdInput", "eventFilter", "filterStart", "filterEnd"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("change", debounce(() => reloadFn(1, apiAdminRef), 400));
    });
}

function attachSortListeners() {
    const ths = document.querySelectorAll("#logsTable thead th[data-sort]");
    ths.forEach((th) => {
        const cloned = th.cloneNode(true); // reinicia listeners
        th.replaceWith(cloned);

        cloned.addEventListener("click", () => {
            const column = cloned.getAttribute("data-sort");
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === "asc" ? "desc" : "asc";
            } else {
                currentSortColumn = column;
                currentSortDirection = "asc";
            }
            renderTableLogs(lastLogsData, currentAuditPage);
        });
    });
}

function updateSortIcons() {
    document.querySelectorAll("#logsTable thead th .sort-icon").forEach((icon) => {
        icon.textContent = "";
    });

    const activeIcon = document.querySelector(
        `#logsTable thead th[data-sort="${currentSortColumn}"] .sort-icon`
    );
    if (activeIcon) {
        activeIcon.textContent = currentSortDirection === "asc" ? "▲" : "▼";
    }
}

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
function updatePaginationButtons() {
    document.getElementById("prevPage").disabled = currentAuditPage <= 1;
    document.getElementById("nextPage").disabled = currentAuditPage >= totalPages;
}

function updatePageIndicator(currentPage, totalCount, pageSize) {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalCount);
    document.getElementById("pageIndicator").textContent =
        totalCount > 0 ? `Mostrando ${start}-${end} de ${totalCount}` : "Sin registros";
}

function paginateLogs(logs, page, limit) {
    const start = (page - 1) * limit;
    return logs.slice(start, start + limit);
}

function nextPage() {
    if (currentAuditPage < totalPages) loadAuditLogs(currentAuditPage + 1);
}

function prevPage() {
    if (currentAuditPage > 1) loadAuditLogs(currentAuditPage - 1);
}

// =============================
// Sorting
// =============================
function sortLogs(logs) {
    if (!currentSortColumn) return logs;

    return logs.sort((a, b) => {
        let valA = a[currentSortColumn];
        let valB = b[currentSortColumn];

        if (currentSortColumn === "timestamp") {
            valA = new Date(valA).getTime();
            valB = new Date(valB).getTime();
        }
        if (typeof valA === "string") valA = valA.toLowerCase();
        if (typeof valB === "string") valB = valB.toLowerCase();

        if (valA < valB) return currentSortDirection === "asc" ? -1 : 1;
        if (valA > valB) return currentSortDirection === "asc" ? 1 : -1;
        return 0;
    });
}


// ==========================
// Formato de fecha
// ==========================
// Formatea fecha ISO → CLT
function formatDateIso(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString("es-CL", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
    });
}

function formatDateToInput(date) {
    return date.toISOString().split("T")[0]; // "YYYY-MM-DD"
}

// Convierte YYYY-MM-DD → timestamp UTC
function formatDateTs(dateStr) { return dateStr ? Math.floor(new Date(dateStr).getTime() / 1000) : null; }