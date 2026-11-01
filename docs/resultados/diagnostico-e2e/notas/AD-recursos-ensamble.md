# AD · CPU/RSS del runner y latencia de un backtest GEFS

> 2026-10-31. Diseño registrado antes de correr nada, por decisión del usuario (Parte 2, punto b2).
> **Corrido el 2026-10-31 (23:44–00:19 UTC); resultado en §2.** Se corrió con el runner arriba y libre, sin otra
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

## 2. Resultado (2026-10-31)

Se corrió con la CLI de §1, desde el checkout principal, entre las 23:44 y las 00:19 UTC, después
de 5 min seguidos con el runner libre. `scripts/diagnostico_recursos_ensamble.py` sale de los logs
de `data/ensemble-poc/medicion-recursos/` (957 muestras de `docker stats`, paso mediano de 2 s).
Las cifras están en `docs/resultados/diagnostico-e2e/datos/AD-recursos-ensamble.json`.

**Control: pasa.** Los TOA de los 31 miembros y los 6 GeoJSON de acuerdo (12 y 24 h) tienen el
mismo SHA-256 que el backtest consolidado. La medición vale.

| Etapa | Pared | Fracción |
|---|---:|---:|
| Inventario GEFS | 1,3 min | 4 % |
| Descarga GEFS | 7,6 min | 22 % |
| Materialización de los 31 miembros | 17,8 min | 51 % |
| 31 corridas (subida, ELMFIRE, bajada) | 8,2 min | 23 % |
| Base, agregación, evaluación, validación | 0,2 min | 1 % |
| **Total** | **34,9 min** | |

| Recurso | Valor |
|---|---|
| ELMFIRE, pared por miembro | mediana 10,0 s; suma 438 s (21 % de la pared) |
| CPU del contenedor durante la corrida | 432 CPU·s; ~100 % mientras corre un miembro (un núcleo: `mpirun -n 1`) |
| RAM del contenedor | 101 MiB en reposo; pico 1.491 MiB (1.390 MiB sobre el reposo) |

Por §1.2:

- **Cuello de botella: la descarga y la materialización, no ELMFIRE.** Las 31 corridas son el
  21–23 % de la pared, menos del 30 %. Paralelizar las corridas de ELMFIRE baja poco la
  latencia. Lo que pesa es la materialización de cada miembro (51 %), que es Python del cliente,
  y la descarga (22 %).
- **Paralelismo posible en la VM actual:** ⌊(7.939 − 101) / 1.390⌋ = **5** miembros a la vez. Da
  ≥ 2, así que se puede paralelizar en esta VM. La cuenta no incluye la base de datos ni la API, si
  corren en la misma VM.
- **Latencia operativa:** 35 min por reinicio en serie. Entra con holgura entre dos pasadas VIIRS
  (~12 h), pero ocupa más de un tick de 30 min de la app. Es descriptivo: no hay umbral de producto.
  El «~1 h por caso» del consolidado incluía colas y contención que esta corrida no tuvo.
- **Costo:** ~430 CPU·s (~7 CPU·min) de solver por reinicio de 31 miembros, sin convertir a dinero.

Límites (§1.3): la CPU es la del contenedor entero y sale de muestras de ~2 s; el pico de memoria
es fiable. La materialización corre fuera del contenedor, así que su CPU no está en estas cifras.
No cambió nada de `modelo-v0`, miembros, umbrales ni ciclos.
