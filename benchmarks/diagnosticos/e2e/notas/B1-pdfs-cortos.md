# B1: PDFs cortos de ELMFIRE 2025.0212 a markdown

Fecha: 2026-10-17. Fuentes en `docs/referencias/elmfire/` (seis PDF, 2 a 4 páginas cada uno). Los seis se convirtieron; `ELMFIRE_Guide.pdf` (130 páginas) no entra en esta tarea.

Método: texto extraído con pypdf y orden de bloques verificado renderizando cada página (pypdfium2). La herramienta Read no pudo leer los PDF porque falta `pdftoppm`. Ambas librerías viven en un venv del scratchpad, fuera del repo.

## Archivos creados

| Archivo | Fuente | Páginas |
|---|---|---|
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/getting-started.md` | Getting Started — ELMFIRE 2025.0212 documentation.pdf | 1–3 |
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/user-guide.md` | User Guide — ELMFIRE 2025.0212 documentation.pdf | 1–2 |
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/tutorial-01.md` | Tutorial 01_ fire spread in flat terrain under constant wind — ELMFIRE 2025.0212 documentation.pdf | 1–4 |
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/tutorial-02.md` | Tutorial 02_ fire spread in flat terrain under transient wind — ELMFIRE 2025.0212 documentation.pdf | 1–4 |
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/tutorial-03.md` | Tutorial 03_ fire spread in real-world fuel_terrain under constant_uniform wind — ELMFIRE 2025.0212 documentation.pdf | 1–2 |
| `/Users/ichevallier/Projects/university/tesis/igniteinsights/docs/referencias/elmfire/tutorial-04.md` | Tutorial 04_ Landscape-scale fire potential — ELMFIRE 2025.0212 documentation.pdf | 1–4 |

Las figuras no son texto y quedaron como `[Figura omitida: ...]`.

## Keywords de namelist

Referencias de página en el PDF. Abreviaturas: T01…T04 = Tutorial 01…04; "prosa" = aparece en el texto y no en un bloque de código.

| Keyword | Valor de ejemplo | Archivo · página · sección |
|---|---|---|
| `DT_METEOROLOGY` | `3600.` | T02 · p. 3 · `&INPUTS` (prosa y `inputs/elmfire.data`) |
| `NUM_METEOROLOGY_TIMES` | `8` | T02 · p. 3 · `&MONTE_CARLO` (bloque de código) |
| `NUM_METEOROLOGY_BANDS` | `8` (prosa) | T02 · p. 3 · `&MONTE_CARLO` (prosa; discrepa del bloque, ver abajo) |
| `NUM_IGNITIONS` | `1` (ejemplo multi: `2`) | T02 · p. 4 · `&SIMULATOR`; T04 · p. 2 · `&SIMULATOR` (`= 1`) |
| `X_IGN(1)` | `0.0` | T02 · p. 4 · `&SIMULATOR`; T04 · p. 2 · `&SIMULATOR` (`= 740548.710`) |
| `Y_IGN(1)` | `3000.0` | T02 · p. 4 · `&SIMULATOR`; T04 · p. 2 · `&SIMULATOR` (`= 4147156.024`) |
| `T_IGN(1)` | `0.0` | T02 · p. 4 · `&SIMULATOR`; T04 · p. 2 · `&SIMULATOR` (`= 0.0`) |
| `X_IGN(2)`, `Y_IGN(2)`, `T_IGN(2)` | `X2`, `Y2`, `T2` (placeholders) | T02 · p. 4 · `&SIMULATOR` (ejemplo multi-ignición) |
| `MODE` | `2` (default `1`, prosa) | T04 · p. 2 · `&SIMULATOR` (prosa en p. 2) |
| `METEOROLOGY_BAND_START` | `1` | T04 · p. 2 · `&MONTE_CARLO` |
| `METEOROLOGY_BAND_STOP` | `6` | T04 · p. 2 · `&MONTE_CARLO` |
| `METEOROLOGY_BAND_SKIP_INTERVAL` | `1` | T04 · p. 2 · `&MONTE_CARLO` |
| `CROWN_FIRE_MODEL` | `0` (desactiva; cualquier valor > 0 activa) | T04 · p. 3 · `&SIMULATOR` (prosa) |
| `A_SRS` | `"EPSG: 32610"` | T01 · p. 2 (asignación en el script `01-run.sh`); T01 · p. 3 (prosa: se fija en `elmfire.data`). Grupo no indicado en el PDF. |

Grupos de namelist que aparecen: `&INPUTS` (T02 p. 3), `&MONTE_CARLO` (T02 p. 3; T04 p. 2), `&SIMULATOR` (T02 p. 4; T04 p. 2 y 3), `&TIME_CONTROL` (T04 p. 2, eliminado en T04 por no ser relevante a potencial de fuego).

Archivos citados como contenedores de namelist: `inputs/elmfire.data` (T01 p. 3; T02 p. 3; T04 p. 1–2) y `elmfire.data.in` (plantilla; T01 p. 3; T02 p. 4).

Getting Started y User Guide no contienen keywords de namelist.

### Variables del script `01-run.sh` (no son namelist, pero se mapean a `elmfire.data`)

| Variable | Valor de ejemplo | Archivo · página |
|---|---|---|
| `CELLSIZE` | `30.0` | T01 · p. 1 |
| `DOMAINSIZE` | `12000.0` | T01 · p. 1 |
| `SIMULATION_TSTOP` | `22200.0` | T01 · p. 1 |
| `NUM_FLOAT_RASTERS` | `7` | T01 · p. 2 |
| `FLOAT_RASTER[n]` / `FLOAT_VAL[n]` | `ws ; 15.0`, `wd ; 0.0`, `m1 ; 3.0`, `m10 ; 4.0`, `m100 ; 5.0`, `adj ; 1.0`, `phi ; 1.0` | T01 · p. 2 |
| `NUM_INT_RASTERS` | `8` | T01 · p. 2 |
| `INT_RASTER[n]` / `INT_VAL[n]` | `slp ; 0`, `asp ; 0`, `dem ; 0`, `fbfm40 ; 102`, `cc ; 0`, `ch ; 0`, `cbh ; 0`, `cbd ; 0` | T01 · p. 2 |
| `LH_MOISTURE_CONTENT` | `30.0` | T01 · p. 2 |
| `LW_MOISTURE_CONTENT` | `60.0` | T01 · p. 2 |

Columnas de `wx.csv`: `ws,wd,m1,m10,m100,lh,lw` (T02 · p. 2; T04 · p. 1).

## Discrepancias detectadas en los PDF

1. `NUM_METEOROLOGY_BANDS` (prosa, T02 p. 3) contra `NUM_METEOROLOGY_TIMES = 8` (bloque de código, T02 p. 3). El repo usa `NUM_METEOROLOGY_TIMES` (`app/elmfire/builder/namelist_writer.py`); el bloque de código coincide con el repo.
2. `wx.csv` de T02 (p. 2) muestra 7 filas de datos, pero el texto y la salida de `gdallocationinfo` (p. 3) describen 8 bandas.
3. `A_SRS` aparece con espacio (`"EPSG: 32610"`) en T01 p. 2. Verificar contra el script real si se reutiliza.
4. Frase con `are are` en T04 p. 1 (texto original; se mantuvo).
