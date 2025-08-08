// eventBus.js

const eventTarget = new EventTarget();
const listeners = {};
/**
 * Emite un evento personalizado con datos opcionales.
 * @param {string} nombreEvento
 * @param {*} detalle
 */
export function emitEvent(nombreEvento, detalle = null) {
    const evento = new CustomEvent(nombreEvento, { detail: detalle });
    eventTarget.dispatchEvent(evento);
}
export const emitAuditEvent = (event) => {
    const customEvent = new CustomEvent('auditEvent', { detail: event });
    eventTarget.dispatchEvent(customEvent);
};
/**
 * Registra un handler para un evento.
 * @param {string} nombreEvento
 * @param {Function} callback
 */
export function onEvent(nombreEvento, callback) {
    eventTarget.addEventListener(nombreEvento, callback);
}

/**
 * Elimina un handler para un evento.
 * @param {string} nombreEvento
 * @param {Function} callback
 */
export function offEvent(nombreEvento, callback) {
    eventTarget.removeEventListener(nombreEvento, callback);
}
/**
 * Escucha un handler para un evento.
 * @param {string} event
 * @param {Function} handler
 */
export const on = (event, handler) => {
    (listeners[event] = listeners[event] || []).push(handler);
};

/**
 * Emite un evento personalizado con datos opcionales.
 * @param {string} event
 * @param {*} data
 */
export const emit = (event, data) => {
    (listeners[event] || []).forEach(handler => handler(data));
};