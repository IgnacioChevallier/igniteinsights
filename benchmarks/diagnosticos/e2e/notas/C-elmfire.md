# Nota C: qué hace ELMFIRE 2025.0212 y dónde hay margen para mejorar la predicción

> 2026-10-17. Detalle y citas archivo:línea en `docs/referencias/ELMFIRE-COMO-FUNCIONA.md`. Todo sale
> del fuente del tag `2025.0212`; no se corrió ELMFIRE. No se propone cambiar de versión.

## Hallazgos más relevantes

1. **Un solo modelo de copa y uno de superficie.** Copa = iniciación de Van Wagner
   (`I = (0.01·CBH·(460+26·FMC))^1.5`) + velocidad de Cruz 2005, activo/pasivo por `CAC`, y exige
   `CC ≥ 0.39`. `CROWN_FIRE_MODEL` es binario (`elmfire_spread_rate.f90:131-206`). El modelo
   canadiense y otras opciones son de 1.1, no están en el binario.
2. **`FOLIAR_MOISTURE_CONTENT` = 90 % por defecto y no se escribe.** Es el único parámetro de la
   iniciación de copa que no está fijado por una decisión (`elmfire_namelists.f90:123`). De 90 a
   110 % (valor del proveedor) la intensidad mínima de copa sube ~29 %.
3. **Sí hay rásters por celda de humedad viva y foliar** (`MLH/MLW/FMC_FILENAME` con `USE_CONSTANT_*
   = .FALSE.`). El comentario de `namelist_writer.py:51-53` es incorrecto para esta versión. Pisos
   silenciosos: MLH ≥ 30 %, MLW ≥ 60 %.
4. **No hay modelo de humedad del combustible dentro de ELMFIRE** (ni Nelson ni retardo): consume
   m1/m10/m100 ya hechos, que los calcula este repo.
5. **Forma del frente.** L/W usa el viento medio efectivo **en m/s** (`WSMFEFF_LOW_MULT =
   5.07955E-3`) aunque la doc diga mph; a 10 mph da 2.8 en vez de 8. El retroceso sale de la elipse,
   no de `V_s0`. Es una perilla (`WSMFEFF_LOW_MULT`, `MAX_LOW`) que el repo nunca movió; el banco ya
   reproduce el comportamiento actual (`scripts/pruebas_fisicas.py:161`).
6. **Calibración/asimilación: no existe.** `elmfire_calibration.f90` solo carga tablas por pirioma.
   El Monte Carlo del binario perturba **deltas aditivos globales y estáticos** (`ADJ, CBD, CBH, FMC,
   M1, M10, M100, MLH, MLW, WAF, WD, WS`); la perturbación por píxel/temporal de la doc no está
   implementada. Hay una receta de ensamble del proveedor en `runs/hindcasts/templates/`.
7. **WAF:** ráster interno fijo, solo de `cc`, `ch` y del lecho; no ve `cbh`/`cbd`. Ejemplos:
   CC 60 %/CH 20 m → 0.094; CC 80 %/CH 30 m → 0.074. Pendiente y aspecto se redondean a grado entero.
8. **Pavesas:** sin ascenso ni deriva: recta con el viento de lanzamiento, ±4°, ignición solo si
   no hay celda quemada a ≤ 3 celdas. Con `ENABLE_SPOTTING` los parámetros se sortean aun en corrida
   única (ya documentado); el keyword por combustible `SURFACE_FIRE_SPOTTING_PERCENT(:)` se descarta.

## Gotchas nuevos confirmados (agregados a `interface-gotchas.md`)

Raster de humedad viva/foliar existe y `FOLIAR_MOISTURE_CONTENT=90`; pisos MLH/MLW; perturbaciones
Monte Carlo solo globales y CC/CH/FBFM ignorados; discrepancias doc/código (L/W en m/s, retroceso,
fluctuación de dirección como fracción de 360°, keywords inexistentes); `ELMFIRE_Guide.pdf` es la guía
**1.1**; el CFL solo rige desde el 6.º paso.

## Para decidir (opciones sin probar, solo documentadas)

`FOLIAR_MOISTURE_CONTENT`/`FMC_FILENAME`, `CRITICAL_CANOPY_COVER`, `CROWN_FIRE_ADJ`,
`WSMFEFF_LOW_MULT`/`MAX_LOW`, `PHIW_ADJ`/`PHIS_ADJ`, `MLH/MLW_FILENAME`, `USE_DIURNAL_ADJUSTMENT_FACTOR`,
y perturbaciones Monte Carlo con `NUM_ENSEMBLE_MEMBERS`. Tabla completa en §10-12 del documento.

## Pendiente de verificar (no confirmado)

`CRITICAL_SPOTTING_FIRELINE_INTENSITY` es un arreglo `(0:303)` y `namelist_writer.py:72` (igual que la
plantilla del proveedor) le asigna un escalar. Si el namelist solo llena el elemento 0, el umbral de
1000 kW/m no rige para ningún modelo real. Se resuelve con un test de 10 líneas en `gfortran`, sin
ELMFIRE.

## Fuentes que no valen para 2025.0212

`docs/referencias/elmfire/ELMFIRE_Guide.pdf` y `https://elmfire.io/` describen ELMFIRE 1.1. Los PDF de tutoriales
son 2025.0212 pero cortos; el `User Guide` PDF es solo un índice. El texto completo de 2025.0212 está
en `docs/*.rst` del tag.
