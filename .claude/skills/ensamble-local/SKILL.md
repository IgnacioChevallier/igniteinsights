---
name: ensamble-local
description: Correr en la computadora local el ensamble GEFS (31 miembros) de un pronóstico operativo de Railway y subir su acuerdo al dashboard. Usar cuando se pida "correr/subir el ensamble", "acuerdo del ensamble" para un pronóstico vivo o demo, o al tocar scripts/ensamble_exportar.py, ensamble_local.py o ensamble_registrar.py.
---

# Ensamble GEFS en local

Railway sólo corre el P-24 (el cron). El ensamble cuesta ~35 min y ~1,7 GB por corrida, así que
se corre a mano acá y a Railway sube sólo `ensemble_agreement.json`. Que ese archivo exista en
la salida del pronóstico **es** lo que hace aparecer la capa (`/operativo/estado` →
`pronostico.ensamble: true`); el toggle del admin "Acuerdo del ensamble visible para clientes"
(`calcular_ensamble`) tiene que estar prendido para que los clientes la vean.

Todo corre desde la raíz del checkout principal (el que tiene `data/`), no desde un worktree:
el runner monta `./data` en `/app/data`.

## Antes

- `railway status` muestra el proyecto Ignite Insights; `railway ssh -s api -- true` conecta
  (si la api duerme, la primera llamada la despierta).
- Docker andando y `make dev-simulation` (necesita `../elmfire-runner`). **Un ELMFIRE por vez**
  (VM de 7,75 GB): si otra sesión o un benchmark usa el runner, esperar a que termine.

## Pasos

```bash
# 1. Exportar (por defecto el último pronóstico vivo listo; --id para uno demo).
#    Imprime la ventana y los insumos congelados (estáticos de Railway recortados, tabla,
#    phi.tif) en base64, ~25 MB; el aviso de la llave SSH va a stderr.
railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_exportar.py [--id ID]' \
    2>/dev/null > paquete.json

# 2. Correr (~20-35 min). Reanudable: si el acuerdo ya está, sólo reimprime el paso 3.
uv run python scripts/ensamble_local.py paquete.json

# 3. Subir y registrar: valida el contrato (layer.id, ≥ 24 miembros) antes de dejarlo visible.
railway ssh -s api -- 'cd /app && uv run python scripts/ensamble_registrar.py ID' \
    < data/ensamble-local/ID/ensemble_agreement.json
```

## Verificar

```bash
railway ssh -s api -- 'python3 -c "import urllib.request as u; print(u.urlopen(\"http://localhost:8000/api/v1/operativo/estado\").read().decode())"' | grep -o '"ensamble": [a-z]*'
```

Y en el dashboard: el pronóstico ofrece "Acuerdo del ensamble" y la capa se dibuja.

## Qué puede salir mal

- **`phi.tif no está`**: el pronóstico se podó antes de que `podar` conservara la semilla
  (2026-11-07). Ese no se puede ensamblar sin rehacerlo con la base de Railway.
- **`no coincide` (grilla)**: Railway regeneró los estáticos sobre otra grilla después de
  congelar el pronóstico. No forzar: el ensamble quedaría sobre otro dominio.
- **No usar los estáticos locales** (`data/operativo/estaticos/`): el 2026-11-07 los de la
  computadora (23-10) diferían de los de Railway (26-10) en combustibles y dosel, y el ensamble
  de Patriada quemaba 450 ha de más. Por eso el paquete trae los de Railway.
- **`sólo N miembros descargados`**: el mínimo es 24 de 31 (`MIN_MIEMBROS_VALIDOS`). Si el
  pronóstico tiene más de 4 días, GEFS sale del archivo histórico (AWS), más lento y a veces
  incompleto; reintentar más tarde.
- **El script no está en Railway**: el Dockerfile copia `scripts/` y los watchPatterns de la
  api incluyen `/scripts/ensamble_*.py`; un script nuevo con otro nombre necesita su pattern.
