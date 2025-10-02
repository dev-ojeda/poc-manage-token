# app/thresholds.py

THRESHOLDS = {
    "default": {
        "LCP": 2500,     # Largest Contentful Paint en ms
        "FID": 100,      # First Input Delay en ms
        "CLS": 0.1,      # Cumulative Layout Shift (score)
        "INP": 200,      # Interaction to Next Paint en ms
        "TTFB": 500,     # Time To First Byte en ms
    },
    "/profile": {
        "LCP": 2000,     # esta página es más exigente
        "FID": 80,
        "CLS": 0.08,
    },
    "/checkout": {
        "LCP": 2200,
        "FID": 70,
        "CLS": 0.05,
        "INP": 150,
    },
    "apiresponsetime": {
        "avg": 800,   # promedio aceptable en ms
        "p95": 1200,  # percentil 95
        "p99": 1500,  # percentil 99
    },
    "webvitals": {
        "LCP": 2500,
        "FID": 100,
        "CLS": 0.1,
        "INP": 200,
        "TTFB": 500,
    }
}
