import { showAlert } from "../layout.js";

const suspiciousKeywords = [
    "ip_change",
    "user_agent_change",
    "revoked",
    "multiple_attempts",
    "logout",
    "expiration",
    "login",
    "refresh_token"
];
let page = 1;
const limit = 10;
let totalPages = 1;
export async function loadAuditLogs(page = 1, api_admin) {
    const userId = document.getElementById("userIdInput").value.trim() || "";
    const eventType = document.getElementById("eventFilter").value || "";

    const payload = {
        user_id: userId,
        page: page,
        limit: limit,
    };
    if (eventType) {
        payload.event_type = eventType;
    }
    else {
        payload.event_type = "";
    }
    try {
        const res = await fetch("/api/auth/admin/audit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${api_admin.accessToken}`,
                "X-Token-Type": "access"
            },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`Error: ${res.status}`);

        const data = await res.json();
        totalPages = Math.ceil(data.total_count / limit);
        renderTableLogs(data);
        updatePaginationButtons();

        
    } catch (error) {
        showAlert(`❌ ${error.message}`, "danger");
    }
}

function updatePaginationButtons() {
    document.getElementById("pageIndicator").textContent = `Página ${page} de ${totalPages}`;
    document.getElementById("prevPage").disabled = page <= 1;
    document.getElementById("nextPage").disabled = page >= totalPages;
}

async function renderTableLogs(data) {

    const tbody = document.querySelector("#logsTable tbody");
    tbody.innerHTML = "";

    if (data.total_count > 0) {
        data.logs.forEach(log => {
            const tr = document.createElement("tr");
            let celda = "";
            if (isSuspicious(log.event_type)) {
                switch (log.event_type) {
                    case "user_agent_change":
                        celda = "warning";
                        break;
                    case "refresh_token":
                        celda = "warning";
                        break;
                    case "revoked":
                        celda = "danger";
                        break;
                    default:
                        celda = "primary";
                }
            }
            tr.innerHTML = `
                  <td>${log.session_id}</td>
                  <td>${log.user_id}</td>
                  <td class="bg-${celda}">${log.event_type}</td>
                  <td>${log.old_value}</td>
                  <td>${log.new_value}</td>
                  <td>${log.ip_address || ""}</td>
                  <td>${log.user_agent || ""}</td>
                  <td>${formatDateIso(log.timestamp)}</td>
                `;
            tbody.appendChild(tr);
        });
    }
    else {
        tbody.innerHTML = "<tr><td colspan='5' class='text-center'>Sin registros</td></tr>";
    }
    // Limpia y agrega el nuevo contenido
    //this.container.appendChild(tbody);
}

function isSuspicious(reason) {
    return suspiciousKeywords.some(kw => reason?.toLowerCase().includes(kw));
}

export function attachAuditListeners(api_admin, reloadFn) {
    document.getElementById("eventFilter").addEventListener("change", reloadFn);
    document.getElementById("userIdInput").addEventListener("input", reloadFn);
    document.getElementById("prevPage").addEventListener("click", () => prevPage());
    document.getElementById("nextPage").addEventListener("click", () => nextPage());
}

function nextPage() {
    if (page < totalPages) {
        page++;
        loadLogs();
    }
}

function prevPage() {
    if (page > 1) {
        page--;
        loadLogs();
    }
}

function formatDateIso(isoString) {
    if (!isoString) return "-";
    // Convierte a objeto Date
    const date = new Date(isoString);
    return date.toLocaleString("es-CL");
}