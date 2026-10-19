# D. Auditoría de la referencia y techo de Dice

Sólo lectura sobre artefactos existentes: no se corrió Earth Engine, ELMFIRE ni `--dry-run`. Scripts en
`/private/tmp/claude-501/-Users-ichevallier-Projects-university-tesis-igniteinsights/550f7315-60bc-43cc-824e-2a1c8674fa42/scratchpad/D/`
(`paso1_volcar.py` … `paso7_p24_estricto.py`; salidas `paso3.json`, `paso4.json`, `paso5.json`, `p24_ref.json`).
La ventana PRE del dNBR no se reabre.

Control de que se lee la misma referencia que el benchmark: `cargar_cicatriz` + `vistas` r = 375 m reproducen byte a byte el
`cicatriz.tif` y `excluido.tif` de los 11 paquetes (0 celdas de diferencia; `paso1_volcar.py`).

## 1. Qué consume igniteinsights y cómo se elige

- El run sale del campo `referencias.cicatriz.run` de cada `benchmarks/casos/<inc>/<protocolo>.json`, fijado a mano; el sha del
  `run.json` queda en `paquete.origen.cicatriz_run_json_sha`. Coincide con la columna "Resultado" del README de mask-dataset-gen
  en los 11 casos de la partición (`event-filter-001`, salvo Alerces 2023 = `event-filter-002`). **Convención documentada.**
  `scripts/anio_quema.py:RUN_VIGENTE` repite sólo la excepción de Alerces 2023.
- Todos los runs vigentes tienen `status: completed`. Umbrales idénticos en los 14 eventos: dNBR > 0,3; NBR_pre > 0,15;
  NBR_post < 0,4; NDSI > 0,25 o (brillo > 3500 y croma < 500) fuera; NDWI_pre > 0,05 fuera; componentes mín. 150 px (S2) o 67 px
  (L8); dilatación 1 px (`generar_dataset.py:92-135`). No hay runs con otro umbral: la sensibilidad al umbral no se puede leer
  de los runs.
- Bandas NBR = B8/B12 (`generar_dataset.py:97-98`). Nubes: SCL ≠ 3, 8, 9, 10, 11 (S2) / `QA_PIXEL` bits 1-5 (L8), antes de
  `median()` (líneas 42-51, 92-93). NDSI, brillo, croma y NDWI se calculan sobre la mediana **sin** máscara de nubes
  (`pre_full`/`post_full`, líneas 94-107): convención, pero un píxel de nube persistente puede disparar el filtro de nieve.
- Atribución (`filtrar_evento.py:165-182`): objetivo si el componente está a ≤ 1.500 m de la semilla, a ≤ 1.000 m de un
  hotspot del clúster objetivo o a ≤ 800 m de un componente objetivo; si no, `otro_incendio_probable` o `cambio_no_confirmado`.
  Alerces 2016, Alerces 2023 y Cholila atribuyen con VNP14A1 de 1 km (umbral 7), el resto con VIIRS NRT de 375 m
  (`config/incendios/*.json`). La semilla del evento queda a 1,4 km del punto de ignición real en Epuyén 2025 (nota en el caso).
- `validar_mcd64a1.py` **no guarda resultados**; imprime CSV. Los únicos resultados guardados son la tabla del README y no
  incluyen un Dice. Reproduje la "máscara confirmada" con `data/raw/mcd64a1/mcd64a1_anios_aoi.tif` (de igniteinsights): coincide
  con el README en los 11 eventos (p. ej. Epuyén 2019 83,4 %, El Turbio 53,5 %, Alerces 2023 90,3 %). Mide precisión de la máscara,
  no recall.

## 2. Cómo se lee y se puntúa (app/validation)

- Las teselas están en EPSG:4326 con píxel cuadrado en grados (escala nominal 20 m N-S): S2 = 14,8 × 19,9 m; L8 = 21,9 × 29,8 m.
  Se llevan a la grilla de 30 m del DEM con `Resampling.mode` sobre `src == 1` (`puntuacion.py:Grilla.traer`, líneas 55-70).
  Medido: el área por la grilla difiere de `run.json` en −0,9 % a +0,3 % en los 11 casos. **No hay sesgo de remuestreo.**
  La frase "sin remuestreo" del CLAUDE.md de mask-dataset-gen es imprecisa (hay reproyección por vecino más cercano al exportar),
  pero inocua.
- `cargar_cicatriz` (`puntuacion.py:90-107`): positivo = máscara; excluido = `~observacion_valida` ∪ `cambio_no_confirmado` ∪
  `otro_incendio_probable`; `positivo & ~excluido`. Las celdas excluidas no cuentan ni como acierto ni como falso positivo
  (`metricas`, líneas 125-130). Con `hasta_horizonte`, la cicatriz se trunca a celdas a ≤ 375 m (radio) de una detección FIRMS
  hasta el fin de la última ventana; el resto de la cicatriz pasa a excluido (`benchmark.py:78-114`). Las Golondrinas es el único
  caso con `hasta_horizonte: false` (cicatriz completa, 10.623 ha, contra 853 ha que VIIRS cubre).
- Puntaje principal (`cadena.py:563`): `pred = quemado & ~semilla_del_caso`, `ref = cicatriz_truncada & ~semilla`, excluido del
  paquete. La semilla se descuenta de ambos.

## 3. Referencia FIRMS: tres reglas distintas de rasterización

| Uso | Regla | Código |
|---|---|---|
| `vistas` (truncado de la cicatriz y de P-24) | discos de **radio 375 m** por detección | `benchmark.py:98`, `_horas_por_pasada` |
| `ref_firms`, `ref_firms_horas` (recall FIRMS, error de llegada) | discos de radio 187,5 m; `ref_firms` usa la reconstrucción | `benchmark.py:184, 269-287, 744` |
| Semilla / `_mascara` | casco cóncavo (ratio 0,4, sin huecos) + 187,5 m; clústeres < 4 puntos: discos de **375 m** | `perimeter_reconstruction.py:54-85` |

- `scan × track` reales de las detecciones: mediana 0,18-0,28 km² frente a 0,141 km² nominal (0,375²). Radio equivalente real
  ≈ 240-300 m. El disco de 375 m sobrecubre (≈ 1,3-1,5× el radio) y el de 187,5 m subcubre (≈ 0,6-0,8×).
- Efecto en la referencia truncada (área con r = 375 / área con r = 187,5): Alerces 2023 1,09; Epuyén 1,50; Alerces 2024 1,11;
  Patriada 1,22; Alerces 2016 1,77; Cholila 1,89; Golondrinas 2,28. Con pocas detecciones (SNPP sola en 2015-16) el área de la
  referencia depende casi cuadráticamente de esta convención.
- Cobertura de la cicatriz final por `vistas` (coincide con el README): Alerces 2023 99,7 %; Epuyén 77 %; Alerces 2024 45 %;
  Patriada 23 %; Alerces 2016 75 %; Cholila 26 %; Golondrinas 8 %.
- Precisión espacial: sólo el 58-70 % del área de un disco de 187,5 m cae sobre cicatriz (Golondrinas 16 %). Es esperable (las
  detecciones están en el frente) pero fija un piso al acuerdo FIRMS-cicatriz.

## 4. Techo de Dice por incendio

Métodos (todos sobre la cicatriz final en la grilla de 30 m, excluyendo `excluido`):

- **MCD64A1**: Dice entre la cicatriz y MCD64A1 del año. (a) a 30 m, con las celdas MODIS a ≤ 463 m de la cicatriz; (b) a
  resolución MODIS, celdas con ≥ 50 % de cicatriz contra celdas quemadas. MCD64A1 engorda bordes, así que (b) es la medida justa.
- **Umbral**: Dice entre la máscara con dNBR > 0,3 y con 0,44 (o 0,27), recomputada localmente desde los PRE/POST guardados
  (proxy sin máscara de nubes; fidelidad contra la máscara guardada: Dice 0,94-0,99 en S2; **0,78 en L8, no confiable**).
- **Grilla 375 m**: cicatriz perfecta degradada a celdas VIIRS (mayoría ≥ 50 %, 3 desfases al azar). Cuadrado de 375 m vs disco de
  187,5 m (la regla del código).
- **Islas**: modelo "perfecto de perímetro" que quema toda la vegetación quemable (CCS-BAP, sin NB) dentro del relleno de la
  cicatriz. Contra la cicatriz final y contra la referencia truncada que realmente puntúa.

| Incendio | MCD64A1 30 m | MCD64A1 463 m | Umbral 0,3 vs 0,44 | Grilla: cuadrado / disco 187 | Islas: final | Islas: truncada |
|---|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 0,76 | 0,80 | 0,86 | 0,89 / 0,78 | 0,997 | 0,997 |
| Epuyén 2025 | 0,82 | 0,87 | 0,89 | 0,88 / 0,77 | 0,966 | 0,957 |
| Alerces 2024 | 0,83 | 0,88 | 0,90 | 0,89 / 0,78 | 0,977 | 0,950 |
| Patriada 2026 | 0,80 | 0,83 | n. m. | 0,88 / 0,77 | 0,961 | 0,852 |
| Alerces 2016 (L8) | 0,83 | 0,86 | n. c. | 0,90 / 0,79 | 0,993 | 0,991 |
| Cholila 2015 (L8) | 0,84 | 0,85 | n. c. | 0,91 / 0,79 | 0,958 | 0,857 |
| Las Golondrinas 2021 (límite) | 0,85 | 0,89 | n. m. | 0,92 / 0,80 | 0,974 | 0,974 |

n. m. = no medido (el recómputo local sólo se hizo en 4 eventos); n. c. = no confiable (L8, fidelidad 0,78). Prueba, para
referencia: El Turbio 0,57 / 0,65 (MCD64A1 omite el fuego fragmentado, ver README); Puerto Café 0,81 / 0,84; Epuyén 2019 0,73 / 0,81;
Alerces 2015 0,80 / 0,83.

**Techo razonable del Dice principal contra la cicatriz:** ≈ 0,85-0,90 en los incendios sanos (Epuyén, Alerces 2024/2016,
Golondrinas), ≈ 0,80-0,85 en Alerces 2023 y Patriada, y ≈ 0,85 en Cholila por las islas. Es el acuerdo entre referencias
independientes y la sensibilidad al umbral, no una cota dura. Un Dice de 0,44-0,50 está por debajo de ese techo con holgura.
El efecto de grilla de 375 m **no limita** el Dice principal (la cicatriz está a 30 m); limita las referencias basadas en FIRMS
(recall FIRMS, error de llegada, semilla, anillo de P-24): techo 0,88-0,92 con el cuadrado nominal y 0,77-0,80 con la regla de
código (disco de 187,5 m, que cubre sólo el 78 % del píxel).

Sensibilidad al filtro: Dice baseline vs objetivo por área (`run.json`, el objetivo está contenido en el baseline): Epuyén 0,96;
Alerces 2024 0,99; Alerces 2016 0,98; Alerces 2023 0,88; Cholila 0,83; Golondrinas 0,84; Patriada 0,54 (40.744 ha de
"otro incendio" en el ROI). Como lo excluido no puntúa, el filtro sólo cambia el puntaje si atribuyó mal: en Patriada la máscara
(24.513 ha) supera la cifra oficial (14.770) en 66 %, y MCD64A1 también la supera, así que la atribución es plausible.

## 5. Hallazgos

### Bug posible

1. **Asimetría del truncado (sesgo contra el modelo).** El truncado a `vistas` excluye las celdas de cicatriz no vistas, pero no
   las celdas no quemadas del mismo interior. Un modelo que quema el interior (como ELMFIRE) recibe falsos positivos en las islas
   sin puntuar los aciertos de la cicatriz interior. Dice máximo de un modelo perfecto de perímetro contra la referencia truncada:
   Patriada 0,85 y Cholila 0,86 (islas = 35 % y 33 % del área de la referencia), Alerces 2024 0,95, Epuyén 0,96 y los demás
   ≥ 0,97. Las islas son 4,5-7,9 % del perímetro en los incendios grandes y 0,6-1,3 % en Alerces 2023/2016; el 85-100 % de los
   huecos es combustible quemable. Corrección posible: excluir también las celdas no vistas que no sean cicatriz (o puntuar
   sólo dentro de `vistas`).
2. **Anillo "ya visto" en P-24 (sesgo a favor de P-24 y de la persistencia).** `pronostico.puntuar` define `vistos = vistas_h ≤ plazo`
   (incluye `vistas_h ≤ 0`). La referencia de crecimiento contiene celdas ya detectadas al reiniciar y fuera de la semilla
   (ésta es casco + 187,5 m; `vistas` usa 375 m). Es el 17-35 % del área de la referencia a 12 h y el 5-20 % a 24 h (por incendio,
   `p24_ref.json`). Re-puntuando con las salidas guardadas y excluyendo ese anillo (`paso7_p24_estricto.py`), el Dice de P-24 a 12 h
   baja: Alerces 2023 0,31 → 0,24; Epuyén 0,22 → 0,12; Alerces 2024 0,47 → 0,34; Patriada 0,20 → 0,15; Alerces 2016 0,15 → 0,09;
   Cholila 0,21 → 0,07. El ΔDice mediano contra la cadena v0 a 12 h pasa de +0,168 a +0,096 (6 de 6 igual) y contra la persistencia
   queda en +0,06. A 24 h el efecto es menor (+0,163 → +0,131).
3. **Cifras invertidas en DIA-1-PROPUESTA §7.2 y RIESGOS_Y_SUPOSICIONES:201.** El resultado principal de la tabla ("FIRMS acumulada":
   +0,107 / +0,141) es el de la semilla **oráculo**. `data/benchmark/p24/tabla-pronostico-v6.md:47,96` (semilla FIRMS) da +0,168 / +0,163;
   `tabla-pronostico-oraculo-v6.md:47,96` da +0,107 / +0,141. Lo confirmé re-puntuando las salidas de ambas. La tabla por incendio
   del mismo §7.2 sí es la de FIRMS. Además, la semilla oráculo queda por debajo de la FIRMS, lo contrario de lo que el texto sugiere.
4. **Semilla P-24 sobrestima.** La reconstrucción (casco cóncavo sin huecos) deja el 26-61 % de la semilla fuera de la cicatriz
   final (media por reinicio: Alerces 2023 47 %, Epuyén 39 %, Alerces 2024 37 %, Patriada 52 %, Alerces 2016 26 %, Cholila 25 %
   más 13 % en exclusión). El 3-30 % cae a más de 375 m del borde. La semilla no puntúa (se excluye), pero arranca ELMFIRE con
   área quemada que la cicatriz no confirma. No se aplica `radio_cicatriz_m` en los casos de pronóstico: las detecciones son
   las de toda la caja, vecinos incluidos.
   **Descompuesto en [T-semilla.md](T-semilla.md) (2026-10-18).** Las detecciones ajenas (el bug) son el 26 % del área de afuera
   y están casi todas en Cholila. La huella y el margen del píxel de 375 m explican el 43 %, el relleno del casco el 16 % y la
   quema que la cicatriz no marca el 16 %. Una regla de tiempo real (conexión a la ignición con saltos ≤ 3 km) equivale al
   oráculo de 2 km. Con ella sólo cambia Cholila, y la mediana de P-24 no se mueve.

### Convención documentada (con magnitud)

- Radio 375 m para `vistas` (tolerancia "un píxel", `TOLERANCIA_VIIRS_M`) frente a 187,5 m para `ref_firms`: ver tabla de la §3.
- Umbral único 0,3 (sensibilidad medida abajo), componentes mínimos de 6 ha (S2) / 6 ha (L8: 67 px × 900 m²) y dilatación de 1 px.
  La dilatación infla el borde: la erosión de 30 m reduce el Dice a 0,92-0,96, es decir ≤ 8 % del área en el peor caso.
- `cambio_no_confirmado` y `otro_incendio_probable` excluidos: neutral. Pero en Alerces 2023 son 292 ha (27 % del objetivo) y
  Cholila 9.040 + 2.214 ha; si fueran fuego real, el modelo no es premiado ni penalizado ahí.
- El dominio excluido por falta de observación o fuera de ROI es 11-57 % de la grilla (Alerces 2023 57 %): predicciones fuera del
  ROI no puntúan.
- Eventos Landsat 2015-16: POST en abril-mayo (otoño, caída de hoja de lenga) con PRE en verano. No medí falso positivo
  fenológico (la mediana POST guardada no tiene máscara de nubes); MCD64A1 confirma el 88-90 % de la máscara, así que no hay
  evidencia de problema. Riesgo bajo, sin cuantificar.

## 6. Lista de sesgos y magnitud

| Sesgo | Dirección | Magnitud |
|---|---|---|
| Islas internas con truncado asimétrico | contra el modelo | −0,15 de Dice en Patriada/Cholila; −0,03 a −0,05 en Epuyén/Alerces 2024; ≤ −0,01 resto |
| Umbral dNBR (0,27-0,44) | incertidumbre simétrica | área 0,3 → 0,44: −19 a −25 %; Dice entre ambos 0,86-0,90; 0,3 vs 0,27: 0,94-0,98 |
| Quemas de baja severidad (dNBR 0,1-0,3) dentro del perímetro | contra el modelo si quema todo | 7-82 ha (≈ 0,4-2,4 % del perímetro; sólo S2 y L8 de 4 eventos); el no marcado interior total es 1-7 % |
| Acuerdo con MCD64A1 | incertidumbre | Dice 0,80-0,89 a 463 m en 9 de 11 eventos; El Turbio 0,65 |
| Radio 375 m vs 187,5 m en la referencia FIRMS | infla/deflata el área de referencia | ×1,09 a ×2,28 |
| Grilla 375 m en referencias basadas en FIRMS | techo | 0,88-0,92 (cuadrado), 0,77-0,80 (regla del código) |
| Anillo "ya visto" en P-24 | a favor de P-24 | −0,03 a −0,14 de Dice a 12 h, ΔDice mediano −0,07 |
| Semilla P-24 fuera de la cicatriz | afecta el arranque | 26-61 % del área sembrada |
| Remuestreo `mode` | ninguno | |Δárea| ≤ 0,9 % |
| Cicatriz final truncada vs completa | cambia qué se mide | referencia = 8-100 % de la cicatriz (Golondrinas 8 % si se truncara) |

## 7. Límites de esta auditoría

- MCD64A1 usa bandas anuales (no fecha); en años con varios incendios vecinos el acuerdo a 30 m está sesgado a la baja.
- El recómputo de umbral es un proxy (mediana sin máscara de nubes); no se hizo para Landsat ni para Patriada/Cholila.
- No se corrió `--dry-run` ni se reabrió la ventana PRE.
- No hay un Dice entre runs de umbrales distintos: no existen.
