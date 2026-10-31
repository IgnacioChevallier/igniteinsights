# AD · CPU/RSS del runner y latencia de un backtest GEFS

> 2026-10-31. Diseño registrado antes de correr nada, por decisión del usuario (Parte 2, punto b2).
> **Todavía no se corrió:** el runner estaba caído. Se corre con el runner arriba y libre, sin otra
> corrida de ELMFIRE en curso.

## 0. Problema

`DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md` deja abiertos dos puntos del ensamble: la CPU y
la RAM del runner, para estimar el costo, y la latencia operativa. Hoy sólo hay pared de cliente:
mediana de 592 s de solver por caso y 16 s por miembro, y ~1 h por caso en serie con descarga y
materialización. Los `run-metrics.json` traen la CPU y el RSS del cliente, no los del runner
(`ENSAMBLE-BACKTESTS-CONSOLIDADO.md`).

## 1. Diseño registrado (antes de correr)

**Caso:** `los-alerces-2023/pronostico-v6`, ventana 1, ciclo GEFS `2023020500`, inicio
`2023-02-05T06:06:00Z`. Es el caso de solver mediano entre los 24 con 31 miembros (592 s;
`data/ensemble-poc/backtest-lote-a/los-alerces-2023-w01`). No se elige por su resultado.

**Corrida:** la misma CLI de los backtests, con salida a un directorio nuevo. No pisa nada
congelado.

```bash
uv run python scripts/run_ensemble_backtest_case.py \
  --case los-alerces-2023/pronostico-v6 --window 1 --cycle 2023020500 \
  --forecast-start 2023-02-05T06:06:00+00:00 \
  --output data/ensemble-poc/medicion-recursos/los-alerces-2023-w01 2>&1 | tee …/corrida.log
```

**Muestreo**, en paralelo y sin tocar el runner: cada ~2 s, `docker stats --no-stream` del
contenedor del runner (CPU %, memoria usada) con hora UTC, a `…/docker-stats.csv`, desde antes de
lanzar hasta después de que termine.

**Antes de lanzar:** el runner responde en `:8001`, `ps` no muestra ningún `scripts/benchmark.py
correr` durante varios minutos seguidos y nadie avisó que va a correr ELMFIRE. El script ya
serializa ELMFIRE con su lock global.

**Duración estimada:** ~1 h de reloj. Unos 10 min son de solver; el resto, descarga y
materialización.

### 1.1 Qué se mide

| Magnitud | Cómo |
|---|---|
| Latencia de punta a punta | Pared desde que se lanza hasta que existe `integrity.json` |
| Latencia por etapa | Horas del log: descarga GEFS, materialización, 31 ELMFIRE, agregación |
| CPU del runner | Integral del CPU % de `docker stats` durante cada miembro, en CPU·s; mediana por miembro y total |
| RAM del runner | Pico y mediana de la memoria del contenedor durante los miembros, menos la del contenedor en reposo |

**Control:** el mapa de acuerdo y el TOA de c00 tienen que tener el mismo SHA-256 que en el
backtest consolidado. Si no coinciden, la medición no vale y no se informa. ELMFIRE es
determinista, así que una diferencia indicaría otra entrada, no ruido.

### 1.2 Qué se concluye (fijado antes)

- **Cuello de botella.** Si los 31 ELMFIRE son < 30 % de la pared, el cuello de botella es la
  descarga y materialización: paralelizar miembros no baja mucho la latencia. Si son ≥ 50 %,
  paralelizar miembros es lo que la baja. Entre 30 y 50 %, se informan las dos partes sin
  recomendación.
- **Paralelismo posible en la VM actual** (7,75 GB): ⌊(7,75 GB − memoria en reposo) / pico por
  miembro⌋. Si da ≥ 2, se puede paralelizar en esta VM. Si da 1, hace falta otra máquina.
- **Latencia operativa:** se informa la pared total contra el intervalo entre pasadas VIIRS
  (~12 h) y el tick de 30 min de la app. Es descriptivo: no hay umbral de producto fijado y no se
  inventa uno.
- **Costo:** CPU·s por caso, sin convertir a dinero. El precio depende del proveedor, que no está
  decidido.

Qué no se hace, sea cual sea el resultado: no se cambian miembros, umbrales, ciclos, `modelo-v0` ni
`lw-100-001`, y no se abre el conjunto de prueba. El resultado cierra los puntos 2 y 3 de
`DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md` §9 como límites medidos.

### 1.3 Límites del método

`docker stats` mide el contenedor entero, incluido el servidor HTTP. Con muestras cada ~2 s y
miembros de ~16 s, la CPU por miembro es aproximada (~8 muestras); el pico de memoria es fiable.
Para CPU y maxRSS exactos haría falta instrumentar `../elmfire-runner` con `getrusage`, y eso se
descartó para no cambiar otro repositorio.
