import datetime
import pytz

def parse_iso8601(iso_str: str, tz_name: str) -> dict:
    """
    Convierte un string ISO-8601 con 'Z' a:
    - datetime UTC
    - timestamp en segundos
    - timestamp en milisegundos
    - datetime en otra TZ (ej: America/Santiago)
    """
    country_tz = pytz.timezone(tz_name)
    # Normalizar Z -> +00:00 para que Python lo entienda
    if iso_str.endswith("Z"):
        iso_str = iso_str.replace("Z", "+00:00")

    # Parsear como datetime aware
    dt_utc = datetime.datetime.fromisoformat(iso_str)

    # Convertir a timestamp
    ts = dt_utc.timestamp()
    ts_ms = int(ts * 1000)  # en milisegundos

    # Convertir a otra zona horaria (ej: America/Santiago)
    dt_local = dt_utc.astimezone(country_tz)

    return {
        "utc_datetime": dt_utc,
        "timestamp": ts,
        "timestamp_ms": ts_ms,
        "local_datetime": dt_local,
    }

# # 🚀 Ejemplo de uso
# result = parse_iso8601(datetime.datetime.now(tz=timezone.utc).isoformat(),"America/Santiago")["timestamp_ms"]

# #print("UTC datetime:", result["utc_datetime"])
# # print("Timestamp (s):", result["timestamp"])
# print("Timestamp (ms):", result)
# # print("Santiago datetime:", result["local_datetime"])

