# Estado del proyecto

> Última revisión: **2026-09-16**. Índice de los planes vivos y de lo que queda pendiente.
> Se actualiza cuando cambia un **estado**, no cuando cambia el contenido de un plan.

## Dónde está cada cosa

**Planes vivos (raíz):**

| Documento | Qué es | Estado |
|---|---|---|
| `ETAPA-A-BASELINE.md` | Baseline honesto y andamiaje de medición | A0–A6 hechos · **falta A7** |
| `ETAPA-B-INSUMO-PATAGONICO.md` | Insumo patagónico y crosswalk fundamentado | B0–B4 hechos · **faltan B5 y B6** |
| `ETAPA-C-MODELOS-PROPIOS.md` | Modelos de combustible propios | Puerta C0 resuelta: **rama parcial**, no camino crítico |
| `IGN-20B-CROSSWALK-CCSBAP.md` | **Crosswalk principal** (CCS-BAP → FBFM40) | Propuesta · **pendiente del director** |
| `IGN-20-CROSSWALK.md` | Crosswalk de MapBiomas, comparador intermedio | Propuesta · pendiente del director |
| `IGN-26-VALIDACION.md` | Diseño de validación (harness A y B) | **Especificado, no implementado** |
| `PENDING_PARAMETERS.md` | Valores fijados sin criterio | Vivo · §1.1 superado, §1.5 resuelto |

**Histórico (`docs/historico/`):** la auditoría end-to-end del 2026-08-31, el playground de
sensibilidad y la visualización animada. Terminados o superados; se conservan porque se citan
en la tesis.

**Referencia (`docs/referencias/`):** la Publicación Técnica N.º 37 de CIEFAP convertida a texto.

## Qué está hecho

- **Pipeline completo**: ingesta (FIRMS, GFS, Copernicus DEM, WorldCover) → preparación de
  rásters y namelist → ELMFIRE 2025.0212 → isócronas y dashboard.
- **Etapa A (A0–A6)**: AOI resuelto, caché invalidable, tabla de combustibles propia,
  validación de códigos, dosel desde datos reales, clase mayoritaria, humedad viva explícita.
- **Etapa B (B0–B4)**: MapBiomas probado y promovido; **CCS-BAP conseguido** (CIEFAP,
  2026-09-13) y rasterizado; crosswalk propuesto sobre su leyenda; los tres mapas se
  construyen sobre la misma grilla con `scripts/build_fuel_maps.py`.
- **Primera comparación de los tres mapas** con ELMFIRE: el resultado es fuertemente sensible
  al insumo (anillo de 1.989 / 9.328 / 10.537 ha). Ver `IGN-20B-CROSSWALK-CCSBAP.md` §6.1.
- **Playground de sensibilidad** y **visualización animada** (fuego y viento).
- **Fuente de combustible cableada al pipeline** (2026-09-16): `settings.fuels_source`
  —por defecto `ccsbap`— elige el insumo, entra en la clave de caché y su procedencia llega
  hasta la leyenda del dashboard.
- **Paso 4 de Scott & Burgan ejecutado** contra la quema experimental de la PT-37: ningún
  modelo de arbustal de SB40 reproduce a la vez propagación y llama (`IGN-20B` §6.2).
- **Sensibilidad de la humedad viva cuantificada**: factor 2,5 en área quemada entre 30 % y
  120 % (`IGN-20B` §6.3).
- **Dos parámetros implícitos hechos explícitos**: `CROWN_FIRE_MODEL` y `SIMULATION_TSTART`,
  este último anclado a la hora real de ignición.

## Qué queda pendiente

| # | Pendiente | Depende de | Tamaño |
|---|---|---|---|
| 1 | **Re-ingestar Copernicus DEM para el AOI ampliado**. El DEM crudo local sólo cubre el AOI viejo, así que ninguna corrida abarca el footprint completo del incendio | red (la clave está configurada) | mediano |
| 2 | **Harness B** (`IGN-26-VALIDACION.md`): puntuar contra el perímetro observado. El dataset de máscaras está local, 196 tiles | 1, o el número queda sesgado por qué tiles entraron | grande |
| 3 | **Regenerar la comparación de los tres mapas** con `SIMULATION_TSTART` anclado: los números de `IGN-20B` §6.1 se corrieron con `TSTART = 0` | una preparación nueva (base de datos y API arriba) | mediano |
| 4 | **Fijar LH/LW con el valor medido**. El barrido ya dice que importa; falta el número | conseguir Bianchi & Defossé (2015), IJWF 24(3):340 | chico |
| 5 | **Aprobación del director** de IGN-20B, con las tres decisiones de su §9 | el director | — |
| 6 | **A7 — congelar el baseline** y **B6 — comparación final contra lo observado** | 2 | mediano |
| 7 | **ADJ / IGN-25**: calibrar el factor de ajuste | 6, y **nunca antes** | mediano |
| 8 | Parámetros sin criterio que quedan: humedad de muertos sin historial de secado (§1.2), `m1` sin corrección diurna, timesteps sin prueba de convergencia, `horizon_hours` por defecto sin base | — | varios |
| 9 | Datos por parcela de la PT-37, para separar 10 h de 100 h | CIEFAP | — |

Los puntos 1, 2 y 8 se pueden cerrar sin depender de nadie más.

## Qué NO está pendiente, aunque el nombre sugiera lo contrario

- **CBH/CBD por modelo de combustible**: resuelto en A4, las tablas ya no existen.
- **Conseguir la PT-37**: conseguida. La Etapa C quedó acotada a la rama parcial.
- **Conseguir CCS-BAP**: conseguido, con dos épocas (2013 y 2017) y cinco provincias.
- **El 23 % no combustible del AOI**: verificado con tres productos independientes. No es un
  artefacto del insumo.
- **Cablear la fuente de combustible**: hecho. La app sirve el mapa de CCS-BAP.
- **El paso 4 del crosswalk**: ejecutado. Su resultado no invalida las asignaciones; muestra
  que el techo pasó a ser el sistema de modelos, no el insumo.
