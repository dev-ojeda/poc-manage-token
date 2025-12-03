export const state = {
    role: "User",
    interval: 5000,
    intervalID: null,
    intervalAPI: null,
    charts: {
        metrics: null,
        metricsUnified: null,
        durationChart: null,
        globalChart: null,
        timeline: null
    },
    lastUpdate: null,
    auditActive: false,
    apiMetrics: [],
    allMetrics: [],
    apiAdmin: null,
    browser: getNavegatorInfo(),
    os: getOSInfo(),
    page: getPage(),
    url: getUrl(),
    metric_id: generateUUID(),
};

export function nowISO() {
    return new Date().toLocaleString();
}

function getOSInfo() {
    const ua = navigator.userAgent;
    let os = "Desconocido";
    if (ua.includes("Windows")) os = "Windows";
    else if (ua.includes("Mac OS")) os = "MacOS";
    else if (ua.includes("Linux")) os = "Linux";
    else if (/Android/.test(ua)) os = "Android";
    else if (/iPhone|iPad|iPod/.test(ua)) os = "iOS";

    return os;
}
function getNavegatorInfo() {
    const ua = navigator.userAgent;
    let browser = "Desconocido";
    if (ua.includes("Chrome") && !ua.includes("Edg")) browser = "Chrome";
    else if (ua.includes("Firefox")) browser = "Firefox";
    else if (ua.includes("Safari") && !ua.includes("Chrome")) browser = "Safari";
    else if (ua.includes("Edg")) browser = "Edge";
    else if (ua.includes("OPR") || ua.includes("Opera")) browser = "Opera";

    return browser;
}

function getPage() {
    const p = window.location.pathname;
    return p;
}

function getUrl() {
    const u = window.location.href;
    return u;
}

function generateUUID() {
    return crypto.randomUUID();
}