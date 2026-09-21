# Estado del proyecto

> Última revisión: **2026-09-19**. Índice de los planes vivos y de lo que queda pendiente.
> Se actualiza cuando cambia un **estado**, no cuando cambia el contenido de un plan.

## Dónde está cada cosa

**Planes vivos (raíz):**


| Documento                      | Qué es                                        | Estado                                                      |
| ------------------------------ | --------------------------------------------- | ----------------------------------------------------------- |
| `ETAPA-A-BASELINE.md`          | Baseline honesto y andamiaje de medición      | A0–A6 hechos · **falta A7**                                 |
| `ETAPA-B-INSUMO-PATAGONICO.md` | Insumo patagónico y crosswalk fundamentado    | B0–B5 hechos · **falta B6**                                 |
| `IGN-20B-CROSSWALK-CCSBAP.md`  | **Crosswalk principal** (CCS-BAP → FBFM40)    | Completo, con paso 4 ejecutado · **pendiente del director** |
| `IGN-20-CROSSWALK.md`          | Crosswalk de MapBiomas, comparador intermedio | Propuesta · pendiente del director                          |
| `IGN-26-VALIDACION.md`         | Diseño de validación (harness A y B)          | Implementado y ejecutado · resultados al 2026-09-19         |
| `PENDING_PARAMETERS.md`        | Valores fijados sin criterio                  | Vivo · §1.1 superado, §1.5 y §1.6 resueltos                 |
| `RESULTADOS.md`                | **Informe de resultados de validación**       | Corte al 2026-09-19                                         |


**Fuera de alcance (**`docs/out-of-scope/`**):** `ETAPA-C-MODELOS-PROPIOS.md`, modelos de
combustible propios. Puerta C0 resuelta en rama *parcial*; no es camino crítico y se conserva
porque el paso 4 del crosswalk (`IGN-20B` §6.2) es su argumento.

**Histórico (**`docs/historico/`**):** la auditoría end-to-end del 2026-08-31, el playground de
sensibilidad y la visualización animada. Terminados o superados; se conservan porque se citan
en la tesis.

**Referencia (**`docs/referencias/`**):** la Publicación Técnica N.º 37 de CIEFAP convertida a texto;
Bianchi & Defossé (2015) y Cóbar-Carranza et al. (2014) en PDF.

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


| #   | Pendiente                                                                                                                                                                                                                                                                                                                                                                                           | Depende de                                    | Tamaño  |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ------- |
| 1   | ~~Preparación completa sobre el AOI definitivo~~ **HECHO 2026-09-16**: el DEM ya se re-ingestó y los mapas se reconstruyeron sobre la grilla de 8,3 M celdas, pero falta regenerar meteorología, `phi` y dosel ahí. Sin eso ELMFIRE sigue corriendo en la grilla reducida, y el anclaje de `SIMULATION_TSTART` queda sin aplicarse, porque los directorios de preparación son anteriores al arreglo | levantar base de datos y API para una ingesta | mediano |
| 2b  | **Modelar o acotar la supresión**, o restringir la validación a ventanas de crecimiento libre: sin extinción, una corrida de 24 h con semilla grande sobre-propaga un factor 100                                                                                                                                                                                                                    | —                                             | mediano |
| 2   | **Correr con la duración real del incendio**, no 12 h: hoy el recall del harness está acotado por construcción porque la referencia es una cicatriz de semanas                                                                                                                                                                                                                                      | meteorología que cubra ese horizonte          | mediano |
| 2b  | **Repetir sobre varias ventanas y más de un incendio**: hoy el resultado es una sola ventana de 12 h sobre un solo fuego                                                                                                                                                                                                                                                                            | 2                                             | mediano |
| 3   | **Aprobación del director** de IGN-20B, con las cuatro decisiones de su §9                                                                                                                                                                                                                                                                                                                          | el director                                   | —       |
| 4   | **A7 — congelar el baseline** y **B6 — comparación final contra lo observado**                                                                                                                                                                                                                                                                                                                      | 2                                             | mediano |
| 5   | **ADJ / IGN-25**: calibrar el factor de ajuste                                                                                                                                                                                                                                                                                                                                                      | 4, y **nunca antes**                          | mediano |
| 6   | Parámetros sin criterio que quedan: humedad de muertos sin historial de secado (§1.2), `m1` sin corrección diurna, timesteps sin prueba de convergencia, `horizon_hours` por defecto sin base                                                                                                                                                                                                       | —                                             | varios  |
| 7   | Datos por parcela de la PT-37, para separar 10 h de 100 h. **No están publicados** (búsqueda del 2026-09-16, `ETAPA-C` §C0). Mientras tanto rige el supuesto *todo el Medio a 10 h*, con sesgo declarado. Mail a Bianchi redactado; **envío pendiente**                                                                                                                                             | CIEFAP                                        | chico   |


El punto 1 desbloquea al 2, y el 2 al 4. Nada de eso depende de terceros.

## Qué NO está pendiente, aunque el nombre sugiera lo contrario

- **CBH/CBD por modelo de combustible**: resuelto en A4, las tablas ya no existen.
- **Conseguir la PT-37**: conseguida. La Etapa C quedó acotada a la rama parcial.
- **Conseguir CCS-BAP**: conseguido, con dos épocas (2013 y 2017) y cinco provincias.
- **El 23 % no combustible del AOI**: verificado con tres productos independientes. No es un
artefacto del insumo.
- **Cablear la fuente de combustible**: hecho. La app sirve el mapa de CCS-BAP.
- **El paso 4 del crosswalk**: ejecutado. Su resultado no invalida las asignaciones; muestra
que el techo pasó a ser el sistema de modelos, no el insumo.
- **La humedad del combustible vivo**: `LW` 110 % medido (Bianchi & Defossé 2015); `LH` 30 %
es convención declarada, porque el paper no mide herbáceas.
- **Buscar la separación 10 h / 100 h en la literatura**: hecho, no existe publicada. El Global
Fuelbed Dataset se evaluó y se descartó (`ETAPA-C` §C0).
- **El DEM del AOI ampliado**: descargado, y los tres mapas reconstruidos sobre esa grilla.
- **Harness A completo** (2026-09-19): 10 ventanas × 3 mapas = 30 corridas. CCS-BAP tiene el
mayor recall en las 10, y los dos mapas patagónicos superan al baseline en 9 de 10. Con una
salvedad que acota la lectura: desde el 20 de enero el modelo sobre-propaga hasta 458× la
referencia, porque no se modela la supresión. Ver `IGN-26-VALIDACION.md`.
- **El harness de validación**: escrito, ejecutado y **con resultado**: el mapa patagónico
predice mejor que el baseline (IoU 0,067 contra 0,036; 0,101 contra 0,047 en los tiles con
más del 70 % quemado). Ver `IGN-26-VALIDACION.md`.
- **La preparación sobre el AOI definitivo**: hecha, con `TSTART` anclado, 13 bandas horarias  
de clima y humedad viva medida.



