export function formatDate(iso) {
    const date = new Date(iso);
    return date.toLocaleString("es-CL");
}

export function renderButtonRevocar(sesion, isCurrent) {
    return isCurrent
        ? '<span class="badge bg-primary">Actual</span>'
        : `<button class="btn btn-danger btn-sm btn-revocar" 
                data-session="${sesion.user_id}" 
                data-device="${sesion.device_id}" 
                data-username="${sesion.username}"
                data-rol="${sesion.rol}"
                data-refresh="${sesion.refresh_token}"
                <i class="bi bi-lock-fill"></i> Revocar
            </button>`;
}

export function getStatusBadge(status) {
    switch (status) {
        case "active":
            return `<span class="badge bg-success">Activa</span>`;
        case "revoked":
            return `<span class="badge bg-warning text-dark">Revocada</span>`;
        case "expired":
            return `<span class="badge bg-danger">Expirada</span>`;
        default:
            return `<span class="badge bg-secondary">Desconocido</span>`;
    }
}
