# Diagnóstico: el acuerdo del ensamble quema ~10× más que el P-24 en la demo de Patriada

2026-11-01. Pasada del 05-01 19:20 UTC (ciclo GEFS 2026-01-05T12Z, inicio 19:00 UTC, 31/31
miembros válidos). La capa ≥ 0,80 cubre decenas de miles de ha; el P-24 da 890,5 ha.

## Veredicto

**Es un bug de meteorología del camino operativo, no ELMFIRE ni la agregación, y no es GEFS de
verdad más seco ni más ventoso.** `correr_ensamble` baja GEFS recortado a la `caja` exacta, sin
el margen de 0,5° que `servicio._clima` le da al GFS del P-24. Sobre la grilla de 0,25° de
GEFS, `from_bounds(...).round_offsets().round_lengths()` deja una ventana de **1 × 2 celdas**
(lat −42,125 … −41,875) para una caja que llega hasta −42,286. Patriada (−42,148) y toda la
mitad sur del dominio quedan fuera del dato.

`weather_builder._read_aligned` reproyecta con el `nodata = -9999` que `_write_stack` declara
en los GeoTIFF de GEFS, así que lo no cubierto se rellena con −9999 **y después se trata como
dato**:

- `u10 = v10 = -9999 m/s` → `ws = 27.530 mph` (`derive_wind`);
- `t2m = rh = -9999` → `rh` recortada a 0 → EMC de Nelson ≈ 0,03 → **`m1 = 1 %`**,
  `m10 = 2 %`, `m100 = 5 %` (`derive_moisture`, `np.clip(..., 1, 40)`).

Los 31 miembros tienen el mismo hueco en el mismo lugar, así que todos queman lo mismo ahí:
por eso la mancha sale casi entera en la banda ≥ 0,80. No es incertidumbre meteorológica, es
un artefacto común a todos.

## Evidencia

Reproducción local con el camino del operativo (`inspect_gefs_archive` + `download_gefs_member`
con inventario, `derive_wind`/`derive_moisture`) y el del P-24 (`servicio._clima`), sin
ELMFIRE. Como grilla de referencia usé la de un P-24 de Patriada guardado en local
(`operativo-d868b6d6…`, caja −71,734 / −42,286 / −71,325 / −42,038). La del 05-01 de
producción es casi la misma (−71,732 / −42,286 / −71,324 / −42,041), y su recorte GEFS es
idéntico (ver «Producción», más abajo).

| | recorte GEFS | celdas de la grilla con ws > 200 mph | celdas con m1 = 1 % |
|---|---|---|---|
| caja exacta (hoy) | 1 × 2 celdas, [−71,875, −42,125, −71,375, −41,875] | **69,5 %** (c00, p01, p02 y p03, todas las bandas) | **69,5 %** |
| caja + 0,5° (arreglo) | 5 × 6 celdas, [−72,375, −42,625, −70,875, −41,375] | 0 % | 0 % |

Tabla horaria sobre toda la grilla, banda 0 = 05-01 19:00 UTC (ws en mph a 20 ft; m1 en %).
GFS = ciclo 18Z, el que usó el P-24; GEFS c00 = ciclo 12Z.

| h | ws GFS media / p90 | ws c00 hoy media / p90 | ws c00 con margen media / p90 | m1 GFS | m1 c00 hoy | m1 c00 con margen |
|---|---|---|---|---|---|---|
| 0 | 6,6 / 7,6 | 19.130 / 27.530 | 8,8 / 9,4 | 4,0 | 2,1 | 4,4 |
| 3 | 7,9 / 9,6 | 19.130 / 27.530 | 9,0 / 10,2 | 5,7 | 2,7 | 6,2 |
| 6 | 6,5 / 7,3 | 19.129 / 27.530 | 7,1 / 8,2 | 15,5 | 4,2 | 11,0 |
| 9 | 5,5 / 6,0 | 19.129 / 27.530 | 6,0 / 6,9 | 23,9 | 7,1 | 19,4 |
| 12 | 5,3 / 5,8 | 19.129 / 27.530 | 5,8 / 6,7 | 24,0 | 8,4 | 24,1 |
| 15 | 4,8 / 5,0 | 19.129 / 27.530 | 5,8 / 6,6 | 19,0 | 8,0 | 22,2 |
| 18 | 4,8 / 5,3 | 19.129 / 27.530 | 6,3 / 7,0 | 10,6 | 5,3 | 13,0 |
| 21 | 5,6 / 6,5 | 19.129 / 27.530 | 7,6 / 8,3 | 6,8 | 3,2 | 7,8 |
| 24 | 7,3 / 8,5 | 19.130 / 27.530 | 9,5 / 10,6 | 5,5 | 2,7 | 6,4 |

Con el recorte correcto, GEFS c00 queda a +1 a 2 mph de GFS y su m1 sigue el mismo ciclo
diurno (de noche hasta 6 puntos más seco y a la tarde hasta 4 más húmedo). No hay diferencia
meteorológica que explique un ×10. Las unidades están bien: t2m en K (`GRIB_NORMALIZE_UNITS=NO`),
rh en %, 25 bandas desde t0 (alcanzan para `tstart + 24 h` según `validate_weather_coverage`).

**Por qué los backtests no lo vieron:** `run_ensemble_backtest_case.py` baja GEFS con una caja
fija y amplia (`--bbox -72 -44 -70 -41.8`), y `weather_ensemble_poc.py cmd_prepare` aborta si
el clima no cubre la grilla ("re-download with a margin"). El operativo no tiene ni lo uno ni
lo otro. Los números de `ENSAMBLE-BACKTESTS-CONSOLIDADO.md` y el veredicto del ensamble **no
están afectados**.

### Producción (volumen de Railway, leído el 2026-11-01, antes del arreglo)

Áreas con `0 < TOA ≤ 86.400 s`, el mismo corte de `agreement.py`:

| pronóstico | recorte GEFS c00 | semilla | P-24 | c00 | ≥ 0,10 | ≥ 0,50 | ≥ 0,80 |
|---|---|---|---|---|---|---|---|
| `ab4ce38c` (05-01 19:20, 31/31) | 1 × 2, [−71,875, −42,125, −71,375, −41,875] | 156 ha | 891 ha | **10.233 ha** | 10.261 ha | 10.232 ha | **10.222 ha** |
| `ca5fb7a3` (sin `metadata.json`) | 1 × 2, el mismo | 11.593 ha | 17.324 ha | 41.154 ha | — | — | — |

- **05-01:** c00 quema 11,5 veces lo del P-24. La banda 0,10–0,80 mide 39 ha, el 0,4 % de c00;
  en los backtests es el 4–14 %. Los 31 miembros queman prácticamente lo mismo, como corresponde
  a un clima inventado igual para todos y no a una dispersión meteorológica.
- **Contra lo observado:** si el sesgo 0,44 del primer reinicio de Patriada
  (`ESTADO-RESEARCH.md`) vale para esta ventana, lo observado a 24 h ronda las 2.000 ha. Con
  eso, la capa ≥ 0,80 lo excede unas 5 veces.
- **`ca5fb7a3`:** probablemente es la pasada del 08-01. Su ensamble quedó incompleto: tiene las
  corridas pero no la agregación, y el dashboard no lo ofrece. Tiene el mismo recorte de 1 × 2
  celdas sobre una grilla que llega más al sur (−42,378) y al este (−71,201), así que el hueco es
  todavía más grande. c00 da 2,4 veces el P-24.

Lo que se espera con el arreglo, todavía sin medir: c00 debería volver al orden del P-24, como
en los backtests (c00 ≈ 1.220 ha en Patriada w01).

## Arreglo (aplicado el 2026-11-01)

Toca sólo `app/operativo/ensamble.py`. La capa publicada en la demo sigue siendo la vieja hasta
que se redespliegue la API y se recalculen las pasadas.

1. `correr_ensamble` baja GEFS con la caja + `MARGEN_GEFS_GRADOS = 0.5`, igual que
   `servicio.MARGEN_GFS_GRADOS`.
2. `_preparar_miembro` levanta `RuntimeError("GEFS … no cubre la grilla …")` si `u10.tif` no
   contiene el DEM. El miembro cuenta como fallido en lugar de inventar clima.

Test: `tests/test_operativo.py::test_el_miembro_gefs_que_no_cubre_la_grilla_falla_en_vez_de_inventar_clima`.
Usa una fila de celdas GEFS que cubre sólo la mitad norte del DEM. Sin el arreglo falla con
`DID NOT RAISE`; con el arreglo pasa, junto con el resto de `test_operativo.py`.

Hay que recalcular las tres pasadas de la demo (`scripts/demo_ensamble.py`, después de borrar sus
`ensemble_agreement.json`). Las del 08-01 y 09-01 seguramente tienen el mismo defecto: depende
de cómo cae su caja sobre la grilla de 0,25°.

**Para considerar en `app/elmfire/` (sólo propuesta):** `_read_aligned` deja que el nodata de la
fuente llegue al cálculo físico sin avisar. Una guarda ahí, que falle si quedan píxeles en
nodata después de reproyectar, cubriría a cualquier llamador, incluido el P-24 si algún día su
margen no alcanza.

## Secundario (no explica el ×10)

`agreement.py` cuenta `0 < TOA <= horizon·3600`, con el TOA absoluto desde la banda 0. Así
incluye la semilla (TOA = `SIMULATION_TSTART`, 156 ha el 05-01) y corta en 24 h desde la banda 0,
no desde `tstart`. Para comparar con el P-24 hay que descontar la semilla y usar el mismo corte.
