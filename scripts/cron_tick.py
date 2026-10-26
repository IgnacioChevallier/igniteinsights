"""Dispara un tick operativo por la red privada y termina (entrada de Railway Cron)."""

import json
import os
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def main() -> None:
    base = os.environ["API_BASE_URL"].rstrip("/")
    request = Request(
        f"{base}/api/v1/operativo/tick",
        data=json.dumps({"modo": "vivo", "ingerir": True}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for intento in range(1, 11):
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310 - URL is operator-controlled
                payload = json.load(response)
            break
        except (TimeoutError, URLError):
            if intento == 10:
                raise
            print(f"API no disponible; reintento {intento}/10 en 6 s", flush=True)
            time.sleep(6)
    if payload.get("status") != "success":
        raise RuntimeError(f"tick rechazado: {payload}")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
