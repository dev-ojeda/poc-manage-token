// utils/dbReset.js
export async function resetMetricsDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.deleteDatabase("MetricsDB");
        req.onsuccess = () => {
            console.log("✅ MetricsDB eliminada correctamente");
            resolve(true);
        };
        req.onerror = e => {
            console.error("❌ Error eliminando MetricsDB:", e);
            reject(e.target.error);
        };
        req.onblocked = () => {
            console.warn("⚠️ Eliminación bloqueada. Cierra otras pestañas usando la app.");
        };
    });
}
