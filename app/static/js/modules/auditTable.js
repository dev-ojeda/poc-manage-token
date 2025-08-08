import { showAlert } from "../layout.js";
export function renderAuditLogs(logs, containerId = "auditTable") {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    if (!logs.length) {
        showAlert(`REGISTROS: ${logs.length}`, "info", 8000);
        container.innerHTML = "<tr><td colspan='5' class='text-center'>Sin registros</td></tr>";
        return;
    }

    for (const log of logs) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${log.username}</td>
            <td>${log.ip_address} <small class="text-muted">(antes: ${log.previous_ip || "-"})</small></td>
            <td>${log.user_agent} <small class="text-muted">(antes: ${log.previous_ua || "-"})</small></td>
            <td>${log.reason}</td>
            <td>${new Date(log.timestamp).toLocaleString()}</td>
        `;
        container.appendChild(tr);
    }
}