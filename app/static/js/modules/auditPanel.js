import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
export class AuditPanel {
    constructor(containerSelector = '#audit-panel') {
        this.container = document.querySelector(containerSelector);
        if (!this.container) {
            console.warn(`AuditPanel: No se encontró el contenedor ${containerSelector}`);
            return;
        }
        this.api_admin = new ApiAdmin({
            baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
            storage: new LocalStorageAdapter()
        });
        this.page = 1;
        this.limit = 10;
        this.totalPages = 1;
        this.events = [];
        this.suspiciousKeywords = [
            "ip_change",
            "user_agent_change",
            "revoked",
            "multiple_attempts",
            "logout",
            "expiration",
            "login"
        ];
    }

    async loadLogs(page = 1) {
        const userId = document.getElementById("userIdInput").value.trim() || "";
        const eventType = document.getElementById("eventFilter").value || "";

        const payload = {
            user_id: userId,
            page: page,
            limit: this.limit,
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
                    "Authorization": `Bearer ${this.api_admin.accessToken}`,
                    "X-Token-Type": "access"
                },
                body: JSON.stringify(payload)
            });
            /*const res = await this.api_admin.post("/api/auth/admin/audit", payload);*/
            if (!res.ok) throw new Error(`Error: ${res.status}`);
            
            const data = await res.json();
            this.totalPages = Math.ceil(data.total_count / this.limit);
            this.renderTableLogs(data);
            this.updatePaginationButtons();

        } catch (error) {
            alert("Error al cargar logs: " + error.message);
        }
    }

    isSuspicious(reason) {
        return this.suspiciousKeywords.some(kw => reason?.toLowerCase().includes(kw));
    }


    renderTableLogs(data) {

        const tbody = document.querySelector("#logsTable tbody");
        tbody.innerHTML = "";

        if (data.total_count > 0) {
            data.logs.forEach(log => {
                const tr = document.createElement("tr");
                let celda = "";
                if (this.isSuspicious(log.event_type)) {
                    switch (log.event_type) {
                        case "user_agent_change":
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
                  <td>${this.formatDateIso(log.timestamp)}</td>
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

    formatDate(timestamp) {
        if (!timestamp) return "-";
        const date = new Date(timestamp * 1000); // si viene en segundos
        return date.toLocaleString("es-CL");
    }

    formatDateIso(isoString) {
        if (!isoString) return "-";
        // Convierte a objeto Date
        const date = new Date(isoString);
        return date.toLocaleString("es-CL");
    }

    updatePaginationButtons() {
        document.getElementById("pageIndicator").textContent = `Página ${this.page} de ${this.totalPages}`;
        document.getElementById("prevPage").disabled = this.page <= 1;
        document.getElementById("nextPage").disabled = this.page >= this.totalPages;
    }

    nextPage() {
        if (this.page < this.totalPages) {
            this.page++;
            this.loadLogs();
        }
    }

    prevPage() {
        if (this.page > 1) {
            this.page--;
            this.loadLogs();
        }
    }
}
