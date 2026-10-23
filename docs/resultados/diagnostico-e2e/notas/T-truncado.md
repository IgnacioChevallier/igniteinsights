# T · Truncado asimétrico de la cicatriz (D-referencia §5, bug 1)

> 2026-10-19. Sin ELMFIRE y sin Earth Engine. Sólo calibración; Las Golondrinas va aparte. Script:
> `scripts/diagnostico_truncado.py` (`uv run python scripts/diagnostico_truncado.py`, ~1 min). Test:
> `tests/test_diagnostico_truncado.py`. Tablas: `datos/X1_truncado_por_receta.csv`,
> `X2_truncado_orden_recetas.csv`, `X3_truncado_p24.json`, `X4_truncado_p24_resumen.csv`.

## 0. Dónde está el código y qué se mide

- El truncado está en `scripts/benchmark.py:78-114` (`_referencia_cicatriz`). La línea que excluye sólo la
  cicatriz no vista es la 101: `excluido | (positivo & ~vistas)`. El puntaje principal está en
  `app/validation/cadena.py:563`. Las dos ubicaciones de D son correctas.
- P-24 (`pronostico.puntuar`) excluye `cicatriz & ~vistos`, pero no `~cicatriz & ~vistos`. Es el mismo
  patrón.
- Se re-puntúan las salidas TOA guardadas contra tres referencias:
  - **(A) actual.**
  - **(B) simétrica:** se excluye todo lo no visto, o sea que se puntúa sólo dentro de `vistas`.
  - **(C) islas no vistas:** se excluyen las celdas no vistas y no cicatriz, pero sólo dentro del relleno
    (sin huecos) de la cicatriz final. Es la corrección de P3 §1(a).
- Hay dos predicciones de control. La primera es el **perímetro perfecto**: todo lo quemable (sin NB)
  dentro del relleno de la cicatriz final, que es el techo de islas de D §4. La segunda es **todo
  quemado**: el dominio entero.
- **Controles: cumplen.**
  - Las vistas recalculadas reproducen el `cicatriz.tif` de los 6 casos truncados, celda a celda.
  - (A) da el `principal.dice` de las 37 iteraciones con diferencia 0.
  - (A) reproduce el `pronostico.json` guardado en los 34 reinicios × 2 plazos.
  - (C) reproduce P3: 0,439 / 0,501 → 0,440 / 0,501.

## 1. Calibración, `lw-100-001` (modelo-v0)

| Incendio | Dice A | Dice B | Dice C | sesgo A | sesgo B | sesgo C | B perdona fuera del perímetro final |
|---|---:|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 0,528 | 0,674 | 0,528 | 1,86 | 1,23 | 1,86 | 655 ha (33 % de lo predicho) |
| Epuyén 2025 | 0,501 | 0,594 | 0,501 | 1,41 | 1,03 | 1,41 | 874 ha (27 %) |
| Alerces 2024 | 0,635 | 0,737 | 0,635 | 1,35 | 1,02 | 1,35 | 871 ha (24 %) |
| Patriada 2026 | 0,496 | 0,507 | 0,496 | 0,70 | 0,66 | 0,70 | 197 ha (5 %) |
| Alerces 2016 | 0,389 | 0,597 | 0,389 | 1,69 | 0,76 | 1,69 | 1.283 ha (55 %) |
| Cholila 2015 | 0,513 | 0,588 | 0,518 | 0,87 | 0,63 | 0,85 | 1.513 ha (25 %) |
| **Media / mediana (7 casos)** | **0,439 / 0,501** | 0,538 / 0,594 | 0,440 / 0,501 | | | | |
| Media / mediana (sin límite) | 0,510 / 0,507 | 0,616 / 0,596 | 0,511 / 0,510 | | | | |

**Controles** (Dice A / B / C):

| Incendio | Perímetro perfecto | Todo quemado |
|---|---|---|
| Alerces 2023 | 0,995 / 0,995 / 0,995 | 0,034 / **0,627** / 0,034 |
| Epuyén 2025 | 0,954 / 0,958 / 0,958 | 0,040 / **0,730** / 0,040 |
| Alerces 2024 | 0,949 / 0,984 / 0,984 | 0,093 / **0,747** / 0,093 |
| Patriada 2026 | **0,848** / 0,972 / 0,972 | 0,110 / **0,651** / 0,112 |
| Alerces 2016 | 0,987 / 0,987 / 0,987 | 0,154 / **0,782** / 0,154 |
| Cholila 2015 | **0,850** / 0,920 / 0,920 | 0,087 / **0,767** / 0,088 |

- **El techo de D es real:** 0,85 en Patriada y en Cholila con (A). (C) lo levanta a 0,97 y 0,92, igual
  que (B).
- **Modelo-v0 no lo paga.** Con (C), el único que se mueve es Cholila (+0,005). Las recetas casi no
  queman las islas no vistas: B perdona dentro del perímetro final ≤ 127 ha por incendio. En Patriada,
  además, la receta no llega a cubrir la cicatriz (sesgo 0,70).
- **(B) premia sobrepropagar.** Quemar el dominio entero da 0,63-0,78 con (B). Eso supera a modelo-v0
  con (B) en 5 de 6 incendios y a modelo-v0 con (A) en los 6. Las ganancias de (B) en las recetas reales (+0,01 a +0,21) vienen de dejar de contar
  la sobrequema fuera del perímetro final: 5-55 % de lo predicho, nunca quemado.

**Orden de las recetas** (5 recetas con iteración en los 7 casos; `lw100-remsh8-001` está sólo en 2 casos y
queda fuera; puesto por media / por mediana):

| Receta | A | B | C |
|---|---|---|---|
| lw-100-001 | 1 / 1 | 1 / 1 | 1 / 1 |
| lw100-atlas-001 | 2 / 2 | 2 / 2 | 2 / 2 |
| base-001 | 3 / 4 | 4 / 3 | 3 / 4 |
| lw100-supresion-30-001 | 4 / 3 | 3 / 4 | 4 / 3 |
| lw100-supresion-60-001 | 5 / 5 | 5 / 5 | 5 / 5 |

**La elección de receta no cambia con ninguna referencia.** (B) sólo intercambia el 3.º y el 4.º, que
están a ≤ 0,01 de distancia. La conclusión de MODELO-V0 (0,439 / 0,501, la mejor receta) se mantiene. Lo
mismo sin el caso límite.

**Las Golondrinas (límite, `hasta_horizonte: false`).** (A) 0,012 contra la cicatriz completa
(10.622 ha). (C) 0,012, porque excluye 686 ha de islas sin efecto. (B) 0,072, pero trunca la referencia a
853 ha y deja de medir lo mismo, así que no es comparable.

## 2. P-24 (`*/pronostico-v6`, `lw-100-obs-001`)

Dice medio de P-24 por incendio (k ≥ 1), a 12 h / 24 h. El sesgo es la mediana por reinicio.

| Incendio | A | B | C | sesgo A | sesgo B |
|---|---|---|---|---|---|
| Alerces 2023 | 0,239 / 0,324 | 0,341 / 0,504 | 0,239 / 0,324 | 2,3 / 2,6 | 1,5 / 1,2 |
| Epuyén 2025 | 0,147 / 0,189 | 0,508 / 0,610 | 0,150 / 0,190 | 18,5 / 9,9 | 1,4 / 1,6 |
| Alerces 2024 | 0,342 / 0,443 | 0,580 / 0,640 | 0,344 / 0,444 | 1,5 / 1,7 | 0,5 / 1,0 |
| Patriada 2026 | 0,149 / 0,208 | 0,506 / 0,435 | 0,151 / 0,210 | 27,9 / 2,4 | 0,8 / 0,7 |
| Alerces 2016 | 0,087 / 0,122 | 0,471 / 0,515 | 0,087 / 0,122 | 9,7 / 32,7 | 0,9 / 2,4 |
| Cholila 2015 | 0,070 / 0,262 | 0,442 / 0,499 | 0,074 / 0,272 | 4,0 / 3,3 | 0,6 / 0,9 |

| ΔDice mediano de P-24 (12 h / 24 h) | A | B | C |
|---|---|---|---|
| contra la cadena | +0,096 / +0,131 (6/6, 5/6) | +0,396 / +0,322 (5/6, 5/6) | +0,097 / +0,132 (6/6, 5/6) |
| contra la persistencia | +0,060 / +0,142 (6/6, 6/6) | +0,044 / +0,127 (5/6, 6/6) | +0,063 / +0,143 (6/6, 6/6) |

- (C) mueve el Dice de P-24 en ≤ 0,01 (Cholila a 24 h, 0,262 → 0,272) y no cambia ninguna conclusión.
- (B) convierte un P-24 que sobrepredice ×1,5-33 en uno con sesgo ≈ 0,5-2,4. Del crecimiento predicho, entre el 27
  y el 79 % cae fuera de lo visto y fuera del perímetro final, y (B) lo deja de contar. Esa es casi toda la
  sobrepredicción que F e I atribuyen a la forma isótropa.
- (B) también infla a la cadena y a la persistencia, que sobrequeman igual. El ΔDice contra la cadena se
  cuadruplica.

## 3. Respuesta y recomendación

- **(B) no se adopta en ningún lado.** Su costo es exactamente el que se temía: premia quemar fuera de lo
  visto. Un modelo que quema todo el dominio supera a modelo-v0. Además esconde el error de forma que el
  diagnóstico ya identificó como la causa principal (DIAGNOSTICO-PRECISION-E2E). P3 ya la había descartado
  en calibración; acá se confirma en P-24 y con el control de todo quemado.
- **(C) es la corrección correcta del bug 1, pero hoy vale ≤ 0,005 en calibración y ≤ 0,01 en P-24.** No
  cambia la elección de receta, la conclusión de MODELO-V0 ni la de P-24. El sesgo de D existe como
  **techo** (0,85 → 0,92-0,97 en Patriada y Cholila), no como pérdida medida: ELMFIRE no quema las islas
  no vistas.
- **Dónde, si se adopta.** En el empaquetado, `benchmark._referencia_cicatriz`, con
  `excluido |= relleno(final) & ~final & ~vistas`. Eso corrige `cadena.puntuar` sin tocarlo, pero exige un
  protocolo nuevo, porque los paquetes son inmutables. P-24 necesita la versión por plazo (`~vistos` en vez
  de `~vistas`). Para eso `pronostico.puntuar` tendría que recibir el relleno de la cicatriz final, que
  podría ir como capa `perimetro.tif` del paquete.
- **Decisión (2026-10-23): (C) no se adopta.** Renumerar modelo-v0 y la prueba por +0,001 no vale la
  pena. El techo y su magnitud quedan como límite declarado (`PENDING_PARAMETERS.md` §3).
- **No va en `puntuacion.metricas`**, que es genérica. Mi recomendación: dejar (C) para el próximo cambio
  de protocolo y no abrir uno sólo por esto. Mientras tanto, citar el techo con (C) en el informe.

## 4. Límites

- El relleno usa la cicatriz final, que incluye crecimiento posterior al horizonte. Así, (C) perdona
  también islas de la zona que ardió después (≤ 127 ha por incendio con modelo-v0).
- El perímetro perfecto quema todo lo no NB del relleno. Es una cota, no un modelo.
