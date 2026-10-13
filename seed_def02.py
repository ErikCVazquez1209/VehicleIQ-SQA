"""Load 75 declared simulated samples per garage vehicle through the running API.

Run from the repository root: python seed_def02.py
This appends 225 test records; it does not delete existing telemetry.
"""

import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_demo_samples():
    start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=74)
    samples = []
    for vehicle_id, scenario in [
        ("VEHICLE_001", "city_driving"),
        ("VEHICLE_002", "aggressive_sport"),
        ("VEHICLE_003", "thermal_overheat"),
    ]:
        for index in range(75):
            aggressive = vehicle_id == "VEHICLE_002"
            overheated = vehicle_id == "VEHICLE_003"
            accelerating = index % 2 == 0
            samples.append({
                "vehicle_id": vehicle_id,
                "timestamp": (start + timedelta(seconds=index)).isoformat(),
                "scenario": scenario,
                "rpm": (6500.0 if accelerating else 1800.0) if aggressive else 2000.0,
                "speed_kph": (110.0 if accelerating else 45.0) if aggressive else 40.0,
                "coolant_temp_c": 125.0 if overheated else 90.0,
                "battery_voltage": 10.8 if overheated else 14.0,
                "throttle_pos_pct": (90.0 if accelerating else 10.0) if aggressive else 20.0,
                "short_fuel_trim_pct": 0.0,
                "long_fuel_trim_pct": 0.0,
                "maf_g_s": 8.0,
            })
    return samples


def main():
    payload = json.dumps({"samples": build_demo_samples()}).encode("utf-8")
    request = Request(
        "http://localhost:8000/api/v1/ingest", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        print(f"Muestras simuladas guardadas: {result['saved_count']}")
        print("Selecciona los tres vehiculos en el panel y revisa el origen declarado.")
    except HTTPError as error:
        print(f"Error de la API ({error.code}): {error.read().decode('utf-8')}")
        raise SystemExit(1)
    except URLError as error:
        print(f"No se pudo conectar a la API: {error.reason}. Inicia el backend primero.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
