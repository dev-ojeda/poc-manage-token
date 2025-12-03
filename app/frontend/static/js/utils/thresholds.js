import thresholds from "../thresholds.json" assert { type: "json" };

export function classifyMetric(name, value) {
    const t = thresholds.webvitals[name];
    if (!t) return "unknown";

    if (value <= t.good) return "good";
    if (value <= t.needsImprovement) return "needs-improvement";
    return "poor";
}

export function classifyApiResponseTime(ms) {
    const t = thresholds.api.responseTime;
    if (ms <= t.good) return "good";
    if (ms <= t.needsImprovement) return "needs-improvement";
    return "poor";
}

export function classifyStatusCode(status) {
    for (const [level, codes] of Object.entries(thresholds.api.status)) {
        if (codes.includes(status)) return level;
    }
    return "unknown";
}

