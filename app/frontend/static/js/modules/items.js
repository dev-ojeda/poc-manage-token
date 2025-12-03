// js/modules/items.js

import { showGlobalAlert } from "../layout.js";
// ==============================
// Variables globales auditoría
// ==============================
let apiUserRef = null;
let usersItemsData = [];           // todos los logs cargados desde backend
let filteredUsers = [];        // logs después de aplicar filtros
let currentUserPage = 1;     // página actual
const limit = 10;             // registros por página
let currentSortColumn = "username";
let currentSortDirection = "desc";
// ==========================
// Carga de logs de auditoría
// ==========================
export async function loadItemUser(page = 1, api_user = null) {
    if (api_user) apiUserRef = api_user;
    if (!apiUserRef) {
        showGlobalAlert("❌ No se inicializó el cliente API", "danger");
        return;
    }

    try {
        showTableSpinner(); // 🔹 spinner ON
        const res = await apiUserRef.loadItems();
        usersItemsData = res.items || [];
        //filteredUsers = [...usersData]; // inicializamos
        //sortUsers(currentSortColumn, currentSortDirection);
        hideTableSpinner(); // 🔹 spinner OFF
        renderTableItemUsuario();
    } catch (error) {
        hideTableSpinner(); // 🔹 spinner OFF
        showGlobalAlert(`❌ ${error.message}`, "danger");
    }
}
function renderTableItemUsuario() {
    const tbody = document.querySelector("#userItemsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!usersItemsData.length) {
        tbody.innerHTML = "<tr><td colspan='4' class='text-center'>Sin registros</td></tr>";
        //updatePageIndicator();
        return;
    }

    usersItemsData.forEach(item => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
        <td>${item.name}</td>
        <td>${item.description}</td>
        <td>
            <button class="user-items-btn btn-edit" data-id="${item.id}" data-action="edit">✏️ Editar</button>
            <button class="user-items-btn btn-delete" data-id="${item.id}" data-action="delete">🗑 Eliminar</button>
        </td>
    `;

        tbody.appendChild(tr);
    });
    attachItemsListeners();
}

function showTableSpinner() {
    const tbody = document.querySelector("#userItemsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = `
        <tr>
            <td colspan="4" class="table-spinner">
                <span class="loader"></span>
            </td>
        </tr>
    `;
}
function hideTableSpinner() {
    const tbody = document.querySelector("#userItemsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = ""; // limpiar antes de renderizar los datos
}

function renderButtonAcciones(items) {

    let btnAccioones = `
        <button class="btn btn-sm btn-primary" data-action="edit" data-id="${items.item_id}" data-user="${items.user_id}">Editar</button>
        <button class="btn btn-sm btn-danger" data-action="delete" data-id="${items.item_id}" data-user="${items.user_id}">Eliminar</button>`;
    return btnAccioones;
}

function attachItemsListeners() {
    const tbody = document.querySelector("#userItemsTable tbody");

    if (!tbody || tbody.hasListener) return; // evitar listeners duplicados

    tbody.addEventListener("click", (e) => {
        const target = e.target;
        // 1) ¿Se clickeó directamente un elemento que tenga data-action (ej: botón)?
        const elWithAction = target.closest("[data-action]");
        if (elWithAction && tbody.contains(elWithAction)) {
            const action = elWithAction.dataset.action; // "edit" o "delete" o "row-edit"
            const itemId = elWithAction.dataset.id;         // "abc123"
            const userId = elWithAction.dataset.user;         // "abc123"
            console.log("Elemento con data-action:", action, itemId, userId);
            handleAction(action, itemId, userId, elWithAction);
            return;
        }

        // 2) Si se quiere detectar clic en la fila (tr) aunque el botón no tenga data-action:
        const tr = target.closest("tr");
        if (tr && tbody.contains(tr)) {
            const rowAction = tr.dataset.action; // "row-edit" o undefined
            const itemId = tr.dataset.id;
            const userId = tr.dataset.user;
            if (rowAction) {
                console.log("Acción desde la fila:", rowAction, itemId, userId);
                handleAction(rowAction, itemId, userId, tr);
            }
        }
    });

    tbody.hasListener = true;
}

function handleAction(action, itemId, userId, sourceEl) {
    switch (action) {
        case "edit":
            showGlobalAlert(`EDITAR ${itemId} - ${userId}`, "info", 5000);
            break;
        case "delete":
            showGlobalAlert(`ELIMINAR ${itemId} - ${userId}`, "warning", 5000);
            break;
        default:
            console.log("Acción desconocida:", action);
    }
}