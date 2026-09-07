# Playground de sensibilidad — casos base sintéticos

> Estado: **implementado y verificado end-to-end** (2026-09-07)
> Depende de: Etapa A (A2 tabla de combustibles propia)
> Sirve a: IGN-20 §8 (sensibilidades S1-S4), y como material didáctico de la tesis

## Objetivo

Una sección del dashboard donde se corren **casos base sintéticos** —terreno plano, una sola
clase de combustible, viento constante— y se observa sobre el mapa cómo propaga el fuego al
variar **un factor por vez**: primero viento norte, después viento noreste, después la misma
condición con otro modelo de combustible, después con pendiente, y así.

## Por qué esto no es un juguete

`IGN-20-CROSSWALK.md` §8 ya compromete cuatro análisis de sensibilidad (S1 a S4). Sin un
banco de pruebas, evaluarlos significa correr el AOI completo variando un parámetro y tratar
de aislar el efecto dentro de un dominio de 7,8 M de celdas con topografía, meteorología
multibanda y un mosaico de combustibles. **El efecto queda enterrado bajo la variabilidad
espacial.**

En un dominio sintético controlado, la comparación es limpia: dos corridas idénticas salvo
en un parámetro, y la diferencia es atribuible a ese parámetro. Es el instrumento que
`IGN-20` §8 necesita, no una función adicional.

Tres usos concretos:

1. **Cuantificar S1** (clase 77 → SH4 vs GS3 vs SH3, 22,5 % del AOI): correr los tres modelos
   bajo condiciones idénticas y medir la diferencia en tasa de propagación y área a 6 h.
2. **Verificar que la tabla de combustibles se comporta como dice el paper.** Scott & Burgan
   publican clase adjetiva de propagación y llama por modelo bajo D2L2. Si nuestra corrida de
   GR2 no da propagación *alta*, hay un error en el pipeline, no en el modelo. Es un test de
   integración contra una referencia externa publicada.
3. **Material de defensa.** Una figura que muestra el mismo combustible con viento a 0°, 45° y
   90° explica la anisotropía del modelo mejor que un párrafo.

## Diseño: reutilizar todo el camino existente

`POST /api/v1/simulations/run` recibe un **`inputs_dir`** y no le importa de dónde salió.
Verificado en `app/api/v1/simulations.py:71-90`: valida que exista el directorio y que tenga
`dem.tif`, y de ahí en adelante escribe el namelist, llama al microservicio y registra la
corrida.

**Entonces el playground no necesita maquinaria de simulación nueva.** Sólo tiene que
sintetizar un directorio de inputs y llamar al endpoint que ya existe.

Esto además hereda gratis: la tabla de combustibles propia (`A2`), la validación de códigos
(`A3`), el escritor de namelist con su validación, las isócronas con `arrival_s`, y el
renderizado del mapa.

### El molde ya está escrito, y es de ELMFIRE

`tutorials/01-constant-wind/01-run.sh` del repositorio de ELMFIRE construye exactamente esto:

```
CELLSIZE=30.0            DOMAINSIZE=12000.0       SIMULATION_TSTOP=19800.0
ws=15.0 mph              wd=0.0 deg               m1/m10/m100 = 3/4/5 %
adj=1.0                  phi=1.0
slp=0 asp=0 dem=0        fbfm40=102               cc/ch/cbh/cbd = 0
LH_MOISTURE_CONTENT=30   LW_MOISTURE_CONTENT=60   A_SRS="EPSG: 32610"
```

Todos los insumos son **rásteres uniformes** sobre un dominio cuadrado de 12 km centrado en
el origen. Nuestro `app/preparation/service.py:282` ya tiene `_write_uniform_raster`.

Detalle que confirma la Etapa A: el tutorial **envía su propio `inputs/fuel_models.csv`**. La
convención que adoptamos en A2 es la del proveedor.

---

## Paso a paso

### P1 · Definición de escenario

Un escenario es un conjunto de escalares. Nada más.

| Grupo | Campos |
|---|---|
| Dominio | `cellsize_m`, `domain_size_m`, `crs` |
| Topografía | `slope_deg`, `aspect_deg`, `elevation_m` |
| Combustible | `fbfm40_code` |
| Dosel | `cc_pct`, `ch_m`, `cbh_m`, `cbd_kg_m3` |
| Meteorología | `wind_speed_mph`, `wind_direction_deg`, `m1_pct`, `m10_pct`, `m100_pct` |
| Combustible vivo | `lh_moisture_pct`, `lw_moisture_pct` |
| Corrida | `tstop_s`, `dtdump_s`, `adj` |
| Ignición | punto central, radio en metros |

Modelo Pydantic en `app/domain/schemas.py`, junto a `SimulationRunRequest`.

Restricción de diseño: **escalares, no rásteres**. Un escenario con gradientes deja de ser un
caso base controlado y pasa a ser el AOI real. Si más adelante hace falta pendiente variable,
se agrega un campo específico, no un mecanismo genérico.

### P2 · Constructor del directorio sintético

Módulo nuevo: `app/playground/builder.py`.

1. Construir la grilla de referencia: dominio cuadrado centrado en el origen, en un CRS UTM
   métrico. Reusar el CRS de procesamiento (`EPSG:32719`) para que el pipeline sea idéntico
   al real; el origen puede ubicarse dentro del AOI para que el mapa muestre el caso en un
   lugar plausible.
2. Escribir los rásteres float uniformes (`ws`, `wd`, `m1`, `m10`, `m100`, `adj`) reusando
   `_write_uniform_raster`. **Moverlo de `preparation/service.py` a un módulo compartido** —
   lo van a usar los dos.
3. Escribir los rásteres Int16 uniformes (`dem`, `slp`, `asp`, `fbfm40`, `cc`, `ch`, `cbh`,
   `cbd`), respetando el escalado de ELMFIRE: `ch`/`cbh` ×10 m, `cbd` ×100 kg/m³
   (`.claude/skills/elmfire/references/interface-gotchas.md`).
4. **Validar el código de combustible contra la tabla** con
   `fuels_builder.assert_codes_are_defined()`. Un escenario con un código inexistente daría
   un dominio entero no combustible, en silencio.
5. Escribir `phi`: negativo dentro del disco de ignición, positivo afuera. Reusar la lógica
   de `ignition_builder`; el audit (IGN-13) ya decidió campo de distancia con signo y no ±1.
6. Copiar `fuel_models.csv`, igual que hace `preparation/service.py`.

**No escribir el namelist acá.** Lo escribe `POST /simulations/run`, que ya lo hace bien.

### P3 · Endpoint

```
POST /api/v1/playground/run     → construye el directorio y delega en run_simulation
GET  /api/v1/playground/presets → escenarios predefinidos
```

`POST /playground/run` devuelve el mismo `simulation_id` que una corrida real, así que
`GET /simulations/{id}/isochrones` y el resto funcionan sin tocar nada.

Decisión: **los escenarios se persisten como `SimulationRun` normales**, con el escenario
guardado en `elmfire_config`. Son corridas legítimas y quedan trazables. No se crea una tabla
nueva.

### P4 · Escenarios predefinidos

La secuencia importa: cada uno cambia **un** factor respecto del anterior.

| # | Escenario | Cambia respecto de | Muestra |
|---|---|---|---|
| 1 | Pastizal GR2, sin pendiente, sin viento | — | Propagación isótropa; el fuego crece como un círculo |
| 2 | + viento norte 15 mph | 1 | Elongación en la dirección del viento; relación largo/ancho |
| 3 | Viento noreste 15 mph | 2 | Sólo rota el eje: verifica que la dirección se propaga bien |
| 4 | Viento norte 30 mph | 2 | Respuesta **no lineal** a la velocidad |
| 5 | TL3 en vez de GR2, viento norte 15 mph | 2 | El baseline: hojarasca de conífera casi inerte |
| 6 | TU5 en vez de GR2 | 2 | La propuesta de IGN-20 para bosque cerrado |
| 7 | SH4 vs GS3 vs SH3, viento norte 15 mph | 2 | **Sensibilidad S1**, la asignación más incierta |
| 8 | GR2 con pendiente 30° hacia el norte, sin viento | 1 | Efecto de pendiente aislado del viento |
| 9 | GR2 con pendiente 30° norte + viento sur 15 mph | 8 | Viento y pendiente en oposición |
| 10 | GR2 con `m1` 3 % vs 12 % | 2 | Efecto de la humedad del combustible muerto |
| 11 | GR3 con `LH_MOISTURE_CONTENT` 30 % vs 120 % | 2 | **Modelos dinámicos**: curado total vs verde. Con 120 % debe caer a casi cero |
| 12 | TU5 con dosel cerrado vs abierto | 6 | Reducción del viento a media llama por cobertura de copa |

El 11 es el más importante como verificación: Scott & Burgan advierten (p. 4) que un modelo
dinámico en un procesador no dinámico **no propaga**. Este escenario prueba de punta a punta
que ELMFIRE está aplicando la transferencia de carga, algo que hoy sólo verificamos leyendo
el código fuente.

Los presets viven en un archivo de datos versionado, no en el código.

### P5 · Interfaz

Página nueva bajo la navegación existente (`frontend/components/sidebar-nav.tsx`).

1. Lista de presets y un formulario para los parámetros.
2. Mapa reusando `fire-map.tsx` — es el mismo GeoJSON de isócronas.
3. **Comparación lado a lado**: dos escenarios, dos mapas sincronizados en centro y zoom.
   Es la vista que hace útil al playground; un escenario solo no muestra sensibilidad.
4. Panel de métricas por corrida: área quemada a cada hora, distancia máxima desde la
   ignición, relación largo/ancho del elipsoide, intensidad de línea mediana.

La comparación lado a lado es el requisito real. Un solo mapa es una demo; dos mapas con un
parámetro de diferencia es un experimento.

### P6 · Métricas comparables

`GET /simulations/{id}/stats` ya existe. Verificar que expone lo necesario y, si no, agregar:

- Área quemada por hora (ha)
- Distancia máxima de propagación desde la ignición (m) y **tasa implícita** (m/h)
- Relación de aspecto del perímetro
- Percentiles de intensidad de línea

La tasa de propagación es la que se contrasta contra la clase adjetiva publicada por Scott &
Burgan (Tabla 5: muy baja 0-2 ch/h, baja 2-5, moderada 5-20, alta 20-50, muy alta 50-150,
extrema >150). **1 cadena/hora = 20,1 m/h.** Ese contraste convierte el playground en un test
de integración contra una referencia externa.

---

## Resultados de la verificación end-to-end (2026-09-07)

`uv run python scripts/run_playground_presets.py` corre los 15 presets contra el stack
completo y comprueba las expectativas. Todos corrieron; las seis verificaciones pasaron.

| preset | ha | dist m | dir | elong. | ROS m/h | clase |
|---|---:|---:|---:|---:|---:|---|
| 01-gr2-calma | 26,3 | 318 | — | 1,00 | 53 | baja |
| 02-gr2-viento-n15 | 1.591,7 | 4.207 | 180,0° | 1,22 | 701 | alta |
| 03-gr2-viento-ne15 | 1.472,8 | 4.243 | 225,1° | 1,09 | 707 | alta |
| 04-gr2-viento-n30 | 2.632,5 | 6.421 | 180,1° | 1,43 | 1.070 | muy alta |
| 05-tl3-viento-n15 | **4,9** | 209 | 180,0° | 1,01 | 35 | muy baja |
| 06-tu5-viento-n15 | **91,9** | 1.001 | 180,2° | 1,22 | 167 | moderada |
| 07a-sh4 | 1.258,0 | 4.086 | 180,0° | 1,39 | 681 | alta |
| 07b-gs3 | 1.627,6 | 4.452 | 180,0° | 1,29 | 742 | alta |
| 07c-sh3 | **30,8** | 627 | 180,0° | 1,41 | 105 | moderada |
| 08-gr2-pendiente | 520,9 | 2.043 | 180,0° | 1,02 | 341 | moderada |
| 09-gr2-pendiente-vs-viento | 665,8 | 2.368 | **360,0°** | 1,01 | 395 | moderada |
| 10-gr2-humedad-alta | 366,1 | 2.034 | 180,3° | 1,25 | 339 | moderada |
| 11a-gr3-curado | **3.482,9** | 6.505 | 180,0° | 1,28 | 1.084 | muy alta |
| 11b-gr3-verde | **0,7** | 88 | 180,0° | 1,24 | 15 | muy baja |
| 12-tu5-dosel-cerrado | 21,4 | 356 | 180,0° | 1,05 | 59 | baja |

### Lo que quedó demostrado

1. **ELMFIRE aplica la transferencia dinámica de carga.** GR3 curado 3.482,9 ha contra
   GR3 verde 0,7 ha: un factor de ~4.800. Scott & Burgan (2005, p. 4) advierten que un
   modelo dinámico en un procesador no dinámico no propaga; hasta ahora esto sólo estaba
   verificado leyendo el Fortran. Habilita el uso de los modelos GR/GS/TU dinámicos del
   crosswalk de IGN-20.
2. **La convención de viento es correcta y está medida.** `wd=0` (viento del norte) da
   propagación a 180,0°; `wd=45` da 225,1°. En la corrida de 15 mph el frente avanzó
   2.055 m al sur contra 375 m de retroceso al norte, con flancos simétricos de 975 m.
3. **El argumento del crosswalk, cuantificado.** En condiciones idénticas TU5 (propuesta
   de IGN-20) quema **91,9 ha** contra **4,9 ha** de TL3 (baseline WorldCover): **19×**.
   Deja de ser una afirmación y pasa a ser una medición.
4. **Sensibilidad S1 acotada.** SH4 1.258 ha, GS3 1.628 ha, SH3 **30,8 ha**. La alternativa
   que el paso 4 de Scott & Burgan hizo rechazar propaga **40× menos** que la elegida.
   El rechazo no era cosmético: sobre el 22,5 % del AOI la diferencia es de dos órdenes.
5. **El dosel reduce la propagación.** TU5 bajo dosel cerrado 21,4 ha contra 91,9 ha a
   cielo abierto: la reducción del viento a media llama está operando.
6. **Pendiente contra viento**: con viento del sur de 15 mph oponiéndose a una pendiente
   de 30° que empuja al sur, gana el viento (dirección resultante 360°, o sea norte).

### Rendimiento

Una corrida de 6 km a 30 m y 3 h tarda **~4,6 s** de punta a punta, incluidos el armado
del directorio, ELMFIRE y el contorneo. La comparación interactiva es viable.

---

## Correcciones hechas durante la implementación

**La métrica de dirección estaba mal planteada.** La primera versión tomaba el azimut a la
celda quemada más lejana. Sobre una grilla discreta el borde de la isócrona es dentado y
`argmax` elige una celda arbitraria entre casi-empates: reportó **204,7°** para una corrida
que, medida sobre el ráster, corre exactamente al sur. Se reemplazó por el azimut al
**centroide del área quemada**, que usa todas las celdas y da 180,0° en ese mismo caso.

**Detección de recorte contra el borde.** Un frente que toca el límite del dominio queda
truncado: área, elongación y dirección subestiman, y la corrida deja de ser comparable con
una que entra entera. Devolver esos números en silencio corrompería cualquier resultado de
sensibilidad. Se agregó `reached_domain_edge`, que se refleja en la interfaz.

**Ambigüedad de `time_of_arrival = 0`.** ELMFIRE escribe `nodata = 0` en ese ráster y las
celdas de ignición también llegan en t=0, de modo que un 0 es ambiguo. Se excluyen ambos,
lo que convierte a todas las métricas en medidas de **propagación más allá del disco de
ignición** — que es justamente lo que una comparación de sensibilidad quiere. El disco son
decenas de celdas contra miles y es idéntico entre escenarios.

**`fitTo` en el mapa.** La vista inicial encuadra todo el AOI, que deja un dominio
sintético de 12 km como un punto. Se agregó un prop opcional que hace `fitBounds` sobre las
isócronas.

---

## Costo y riesgos

Un dominio de 12 km a 30 m son 400×400 = 160.000 celdas, contra los 7,8 M del AOI real:
**~49× más chico**. Las corridas deberían ser de segundos, lo que hace viable la comparación
interactiva.

| Riesgo | Mitigación |
|---|---|
| Cada preset ocupa disco como corrida real | Prefijo propio en el directorio de salidas y limpieza periódica; son chicas |
| El playground diverge del pipeline real y deja de ser representativo | Comparte constructor de rásteres, tabla de combustibles, escritor de namelist y runner. Sólo difieren los insumos |
| Un escenario con un código de combustible inválido | `assert_codes_are_defined()` en P2, ya implementado |
| El usuario interpreta los casos base como predicción | Etiquetar la sección explícitamente como sintética, sin georreferencia real |

## Fuera de alcance

- Pendiente, viento o combustible variables en el espacio: deja de ser un caso base.
- Meteorología transiente. El tutorial 02 de ELMFIRE la cubre; se agrega sólo si hace falta.
- Guardar y compartir escenarios de usuario.

## Fuentes

- ELMFIRE 2025.0212, `tutorials/01-constant-wind/01-run.sh` — molde del dominio sintético.
  <https://github.com/lautenberger/elmfire>
- Scott, J.H.; Burgan, R.E. (2005). RMRS-GTR-153. Tabla 5 (clases adjetivas, p. 9), modelos
  dinámicos (p. 4), escenarios de humedad D2L2 (Tablas 3 y 4, p. 8).
- `IGN-20-CROSSWALK.md` §8 · `ETAPA-A-BASELINE.md` §A2-A3
