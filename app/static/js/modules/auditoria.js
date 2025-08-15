import { showAlert } from "../layout.js";
import { ApiAdmin } from "../api/ApiAdmin.js";
import { LocalStorageAdapter } from "../adapters/LocalStorageAdapter.js";
const api_admin = new ApiAdmin({
    baseURL: import.meta.env?.VITE_API_URL || "https://localhost",
    storage: new LocalStorageAdapter()
});

let currentPage = 1;
const limit = 10;

// Inicializar al cargar DOM
document.addEventListener("DOMContentLoaded", async () => {
    const user_rol = api_admin.userRol;
    const user_name = api_admin.userName;
    const dashboardContent = document.getElementById("dashboardContent");
    const expiracion = api_admin.tokenExp;
    if (!user_rol) {
        console.warn("No hay token válido, redirigiendo...");
        window.location.href = "/";
        return;
    }
    // Mostrar nombre y rol
    document.getElementById("userName").textContent = `👋 ${user_name} (${user_rol})`;

    // Mostrar secciones según rol
    showContentByRole(user_rol);

    // Mostrar dashboard y comenzar temporizador
    dashboardContent.style.display = "block";
    startTokenTimer(expiracion);
    openChat(user_rol);
    await loadLogs();
    // Cargar sesiones si es Admin
    //await auditPanel.loadFromAPI();
    PollingManager.iniciar(loadLogs, 10000);
    document.getElementById("eventFilter").addEventListener("change", () => {
        currentPage = 1; // Reinicia a la página 1 si se cambia el filtro
        loadLogs(currentPage);
    });
    document.getElementById("prevPage").addEventListener("click", () => loadLogs(currentPage - 1));
    document.getElementById("nextPage").addEventListener("click", () => loadLogs(currentPage + 1));
});


export async function loadLogs(page = 1) {
    const userId = document.getElementById("userIdInput").value.trim();
    const eventType = document.getElementById("eventFilter").value;

    const payload = {
        user_id: userId,
        page: page,
        limit: limit,
    };
    if (eventType) payload.event_type = eventType;

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

        const tbody = document.querySelector("#logsTable tbody");
        tbody.innerHTML = "";

        if (data.total_count > 0) {
            data.logs.forEach(log => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
              <td>${log.session_id}</td>
              <td>${log.user_id}</td>
              <td>${log.event_type}</td>
              <td>${log.old_value}</td>
              <td>${log.new_value}</td>
              <td>${log.ip_address || ""}</td>
              <td>${log.user_agent || ""}</td>
              <td>${new Date(log.timestamp).toLocaleString("es-CL")}</td>
            `;
                tbody.appendChild(tr);
            });
        }
        else {
            tbody.innerHTML = "<tr><td colspan='5' class='text-center'>Sin registros</td></tr>";
        }


        currentPage = data.page;
        document.getElementById("pageIndicator").textContent = `Página ${currentPage} de ${data.total_count}`;

        // Controlar botones
        document.getElementById("prevPage").disabled = currentPage <= 1;
        document.getElementById("nextPage").disabled = currentPage >= data.limit;

    } catch (error) {
        alert("Error al cargar logs: " + error.message);
    }
}

