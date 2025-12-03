// ==============================
// Service Worker - Refactor v2
// Uso de globalThis en lugar de self/window
// ==============================

const CACHE_NAME = 'neo-dashboard-v2';
const ASSETS = [
    '/',
    '/index.html',
    '/static/css/app.css',
    '/static/js/layout.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/icons/neo1.ico'
];

// ==============================
// 🔹 Instalación del SW
// ==============================
globalThis.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('📦 Cacheando recursos iniciales...');
            return cache.addAll(ASSETS);
        })
    );
    globalThis.skipWaiting();
});

// ==============================
// 🔹 Activación y limpieza de caché vieja
// ==============================
globalThis.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('🧹 Eliminando caché antigua:', key);
                    return caches.delete(key);
                }
            }))
        )
    );
    globalThis.clients.claim();
});

// ==============================
// 🔹 Interceptar peticiones de red
// ==============================
globalThis.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request)
            .then((cached) =>
                cached ||
                fetch(event.request).then((resp) => {
                    // Cachea dinámicamente los nuevos recursos
                    const respClone = resp.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, respClone));
                    return resp;
                })
            )
            .catch(() => caches.match('/offline.html'))
    );
});

// ==============================
// 🔹 Comunicación con la página
// ==============================
globalThis.addEventListener('message', (event) => {
    if (event.data?.action === 'skipWaiting') {
        console.log('⚡ SW: Activando nueva versión inmediatamente');
        globalThis.skipWaiting();
    }
});
