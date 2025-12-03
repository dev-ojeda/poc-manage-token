import { showAlert } from "../layout.js";
// ==============================
// Variables globales auditoría
// ==============================
let apiAdminRef = null;
let usersData = [];           // todos los logs cargados desde backend
let filteredUsers = [];        // logs después de aplicar filtros
let currentUserPage = 1;     // página actual
const limit = 10;             // registros por página
let currentSortColumn = "username";
let currentSortDirection = "desc";
// ==========================
// Carga de logs de auditoría
// ==========================
export async function loadUsers(page = 1, api_admin = null) {
    if (api_admin) apiAdminRef = api_admin;
    if (!apiAdminRef) {
        showAlert("❌ No se inicializó el cliente API", "danger");
        return;
    }

    try {
        showTableSpinner(); // 🔹 spinner ON
        const res = await apiAdminRef.post("/api/auth/admin/user", {});
        usersData = res.logs || [];
        filteredUsers = [...usersData]; // inicializamos
        sortUsers(currentSortColumn, currentSortDirection);
        hideTableSpinner(); // 🔹 spinner OFF
        renderTableUsers();
    } catch (error) {
        hideTableSpinner(); // 🔹 spinner OFF
        showAlert(`❌ ${error.message}`, "danger");
    }

    applyFiltersUser();
}

// ==============================
// Filtros
// ==============================
function applyFiltersUser() {
    const username = document.getElementById("usernameInput")?.value.trim().toLowerCase() || "";
    const createdDate = document.getElementById("filterCreatedUser")?.value;
    const updatedDate = document.getElementById("filterUpdatedUser")?.value;

    filteredUsers = usersData.filter(log => {
        const matchUser = !username || (log.username || "").toLowerCase().includes(username);
        const ts = new Date();
        const matchStart = !createdDate || ts >= new Date(createdDate);
        const matchEnd = !updatedDate || ts <= new Date(updatedDate);
        return matchUser && matchStart && matchEnd;
    });

    sortUsers(currentSortColumn, currentSortDirection);
    currentUserPage = 1;
    renderTableUsers();
}

// ==============================
// Ordenamiento
// ==============================
function sortUsers(column, direction) {
    currentSortColumn = column;
    currentSortDirection = direction;

    filteredUsers.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        if (column === "username") {
            valA = (valA || "").toLowerCase();
            valB = (valB || "").toLowerCase();
            const result = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: "base" });
            if (result !== 0) return direction === "asc" ? result : -result;
        }
        else if (column === "created_at") {
            valA = new Date(valA);
            valB = new Date(valB);
            if (valA < valB) return direction === "asc" ? -1 : 1;
            if (valA > valB) return direction === "asc" ? 1 : -1;
        }
        return 0;
    });
}
function updateSortIndicators() {
    const ths = document.querySelectorAll("#userTable th[data-sort]");
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
// ==========================
// Renderizado de tabla
// ==========================
function renderTableUsers() {
    const tbody = document.querySelector("#userTable tbody");
    if (!tbody) return;
    // 🔹 ordenar ANTES de paginar
    sortUsers(currentSortColumn, currentSortDirection);
    tbody.innerHTML = "";
    const start = (currentUserPage - 1) * limit;
    const pageData = filteredUsers.slice(start, start + limit);
    if (!pageData.length) {
        tbody.innerHTML = "<tr><td colspan='7' class='text-center'>Sin registros</td></tr>";
        updatePageIndicator();
        return;
    }
    //pageData.forEach(log => {
    //    // 🔹 Fila principal con 4 columnas
    //    const trMain = document.createElement("tr");
        
    //    trMain.innerHTML = `
    //        <td class="border border-primary">${log.username}</td>
    //        <td class="border border-primary">${log.rol}</td>
    //        <td class="border border-primary">${log.failed_attempts}</td>
    //        <td class="border border-primary">${formatDate(log.created_at)}</td>
    //        <td class="border border-primary">${formatTime(log.created_at)}</td>
    //        <td class="border border-primary">${formatDate(log.updated_at)}</td>
    //        <td class="border border-primary">${formatTime(log.updated_at)}</td>
    //        <td class="border border-primary">${apiAdminRef.formatDateSantiago(log.blocked_until)}</td>
    //    `;
    //    tbody.appendChild(trMain);

    //});
    let html = "";
    pageData.forEach(log => {
        html += `
            <tr>
                <td>${log.username}</td>
                <td>${log.rol}</td>
                <td>${log.failed_attempts}</td>
                <td>${formatDate(log.created_at)}</td>
                <td>${formatTime(log.created_at)}</td>
                <td>${formatDate(log.updated_at)}</td>
                <td>${formatTime(log.updated_at)}</td>
            </tr>`;
    });
    tbody.innerHTML = html;
    //  🔹 ordenar antes de renderizar
    updatePageIndicator();
}

// ==========================
// Paginación
// ==========================
function updatePageIndicator() {
    const indicator = document.getElementById("pageIndicatorUser");
    if (!indicator) return;

    const totalPages = Math.max(1, Math.ceil(filteredUsers.length / limit));
    indicator.textContent = `Página ${currentUserPage} de ${totalPages}`;

    // Deshabilitar botones según contexto
    document.getElementById("firstPageUser").disabled = currentUserPage === 1;
    document.getElementById("prevPageUser").disabled = currentUserPage === 1;
    document.getElementById("nextPageUser").disabled = currentUserPage === totalPages;
    document.getElementById("lastPageUser").disabled = currentUserPage === totalPages;
}
// ==============================
// Eventos UI
// ==============================
document.getElementById("applyFiltersUser")?.addEventListener("click", applyFiltersUser);
document.getElementById("firstPageUser")?.addEventListener("click", () => {
    currentUserPage = 1; // 🔹 primera página
    renderTableUsers();
});
document.getElementById("prevPageUser")?.addEventListener("click", () => {
    if (currentUserPage > 1) {
        currentUserPage--;
        sortUsers(currentSortColumn, currentSortDirection); // 🔹 asegura orden
        renderTableUsers();
    }
});

document.getElementById("nextPageUser")?.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredUsers.length / limit);
    if (currentUserPage < totalPages) {
        currentUserPage++;
        sortUsers(currentSortColumn, currentSortDirection); // 🔹 asegura orden
        renderTableUsers();
    }
});
document.getElementById("lastPageUser")?.addEventListener("click", () => {
    const totalPages = Math.ceil(filteredUsers.length / limit);
    currentUserPage = totalPages; // 🔹 última página
    renderTableUsers();
});
document.getElementById("goToPageUser")?.addEventListener("click", () => {
    const input = document.getElementById("jumpToPageUser");
    const page = parseInt(input.value, 10);

    const totalPages = Math.ceil(filteredUsers.length / limit);
    if (!isNaN(page) && page >= 1 && page <= totalPages) {
        currentUserPage = page;
        renderTableUsers();
    } else {
        showAlert(`❌ Número de página inválido. (1 - ${totalPages})`, "danger");
    }
});
document.querySelectorAll("#userTable th[data-sort]")?.forEach(th => {
    th.addEventListener("click", () => {
        const col = th.dataset.sort;
        const dir = (currentSortColumn === col && currentSortDirection === "asc") ? "desc" : "asc";
        sortUsers(col, dir);
        renderTableUsers();
        updateSortIndicators(); // 🔹 aquí metemos los SVGs
    });
});
// Users - limpiar filtros
document.getElementById("clearFiltersUser")?.addEventListener("click", () => {
    document.getElementById("usernameInput").value = "";
    document.getElementById("filterCreatedUser").value = "";
    document.getElementById("filterUpdatedUser").value = "";

    // Recarga listado users sin filtros
    loadUsers();
});
// ==========================
// Utilidades
// ==========================
function formatDate(isoString) {
    const date = new Date(isoString);
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0"); // meses empiezan en 0
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");
    return `${hours}:${minutes}:${seconds}`;
}

function showTableSpinner() {
    const tbody = document.querySelector("#userTable tbody");
    if (!tbody) return;
    tbody.innerHTML = `
        <tr>
          <td colspan="3" class="table-spinner">
            <span class="loader"></span>
          </td>
        </tr>
    `;
}

function hideTableSpinner() {
    const tbody = document.querySelector("#userTable tbody");
    if (!tbody) return;
    tbody.innerHTML = ""; // limpiar antes de renderizar los datos
}