# Resultados de validación — comparación de tres mapas de combustible

> **Histórico.** La evidencia vigente y el protocolo de cierre están en `docs/resultados/`.
>
> **Corte al 2026-09-19.** Este documento reúne los números; el método vive en
> `docs/resultados/IGN-26-VALIDACION.md` (diseño de validación), `docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md` (crosswalk
> de CCS-BAP) e `docs/crosswalk/IGN-20-CROSSWALK.md` (crosswalk de MapBiomas). Si algún número de acá
> discrepa con esos documentos, mandan ellos: son los que se regeneran con cada corrida.
>
> Todo es reproducible: `scripts/build_fuel_maps.py`, `scripts/run_three_maps.py`,
> `scripts/harness_a.py`, `scripts/score_against_observed.py`.

> **Nota del 2026-09-30 (auditoría física, `docs/resultados/AUDITORIA-FISICA.md`).** Todas las corridas de este
> documento tienen dos errores de interfaz con ELMFIRE, ya corregidos: el clima quedaba fijo en
> la primera banda durante toda la corrida (las de 12 h corrían con la tarde de la ignición) y el
> frente avanzaba a la mitad de la velocidad calculada. Las de §4–§8 además son anteriores a la
> corrección de la orientación del terreno. Los números de §2 (distribución de los mapas) no
> dependen de eso. La comparación de §4 y §6.1 del documento de combustibles está re-medida en
> §10; el harness A (§5) no se re-corrió. La comparación de los tres mapas sobre el benchmark
> de 11 incendios se rehace en `docs/resultados/COMPARACION-MAPAS-V5.md`.

## 1. Qué se comparó y por qué

La pregunta de la tesis es si un insumo de cobertura que discrimina especie y estructura
predice mejor la propagación del fuego que un producto global. Se comparan tres mapas de
modelos de combustible Scott & Burgan FBFM40, construidos sobre **la misma grilla, con la
misma regla de agregación y el mismo relleno de huecos**:

| Mapa | Origen | Resolución nativa | Rol |
|---|---|---|---|
| **WorldCover** | ESA WorldCover v200 (2021) | 10 m, global | Baseline. Una sola clase arbórea para todo el bosque andino-patagónico |
| **MapBiomas** | MapBiomas Argentina Colección 2 (2024) | 30 m, nacional | Punto intermedio. Separa arbustal de bosque, no discrimina especie |
| **CCS-BAP** | CIEFAP y MAyDS (2017) | Vectorial, 1 ha, regional | El aporte de la tesis. Discrimina especie y estructura |

En todas las corridas **lo único que cambia es `fbfm40.tif`**. Ignición, meteorología,
topografía, dosel y factor de ajuste son idénticos.

## 2. Qué dicen los mapas antes de simular

Superficie por tipo de combustible sobre el AOI definitivo (2.563 × 3.222 celdas de 30 m):

| Tipo de combustible | WorldCover | MapBiomas | **CCS-BAP** |
|---|---|---|---|
| NB · no combustible | 19,21 % | 26,39 % | 20,99 % |
| GR · pastizal | 34,70 % | 12,49 % | 18,22 % |
| GS · pastizal-arbustal | 0,00 % | 3,34 % | 5,11 % |
| SH · arbustal | **3,75 %** | 22,11 % | **23,25 %** |
| TU · bosque con sotobosque | 0,00 % | 31,00 % | 16,41 % |
| TL · hojarasca de bosque | 42,34 % | 4,68 % | 16,02 % |

El baseline concentra el 42 % del área en un único modelo de hojarasca de conífera (TL3) y
ve un 3,75 % de arbustal, incompatible con la evidencia regional: Mermoz et al. (2005)
documentan que en Patagonia los matorrales propagan más que los bosques. CCS-BAP reparte el
bosque entre TU5, TL6 y TU3 según especie y estructura.

## 3. Configuración de las corridas

Todo lo que sigue se corrigió antes de generar estos números, y cada corrección cambia el
resultado:

| Parámetro | Antes | Ahora | Por qué importa |
|---|---|---|---|
| `SIMULATION_TSTART` | 0 | Desfase real (6.360 s) | Con 0, un fuego que arranca a las 19:46 UTC se simulaba con el clima de la primera hora del pronóstico, en el punto equivocado del ciclo diurno |
| `LH` / `LW` | 60 % sin criterio | 30 % / 110 % medidos | Bianchi & Defossé (2015). El 60 % estaba por debajo de todo lo medido en la región: las corridas previas sobreestimaban el fuego |
| `CROWN_FIRE_MODEL` | Ausente | 1, explícito | ELMFIRE lo prende cuando la clave falta, que no es lo mismo que haberlo decidido |
| Meteorología | 1 banda | 13 a 25 bandas horarias | Sin esto no hay ciclo diurno: ni pico de viento de la tarde ni mínimo de humedad |

**Regla de puntuación, común a todo el documento:** se puntúa **sólo el anillo de
crecimiento**, nunca la unión con la semilla. El 84 % de lo que una corrida reporta como
quemado es la propia semilla de FIRMS, que coincide con lo observado por construcción;
puntuar la unión daría un resultado halagüeño que no mide nada del modelo.

---

## 4. Harness B — contra la cicatriz de Sentinel-2

**Referencia independiente.** Las 196 máscaras del dataset de validación se calculan con
dNBR entre una ventana pre (nov-dic 2023) y una post (feb-mar 2026), umbral 0,30, a 20 m.
FIRMS no sirve como referencia acá porque es lo que construyó la semilla: sería circular.

Incendio del 1-2 de febrero de 2026, 12 h de horizonte, semilla de 17.747 ha. Los tiles
cubren el 46,2 % del dominio, y dentro de esa cobertura la cicatriz observada es de
76.178 ha.

| Mapa | IoU | Recall | Precisión | Acierto | Falso positivo | No predicho |
|---|---|---|---|---|---|---|
| WorldCover | 0,036 | 0,043 | 0,182 | 2.827 ha | 12.697 ha | 62.896 ha |
| MapBiomas | 0,045 | 0,048 | **0,412** | 3.175 ha | 4.537 ha | 62.549 ha |
| **CCS-BAP** | **0,067** | **0,082** | 0,267 | **5.362 ha** | 14.715 ha | 60.362 ha |

Estratificado por porcentaje quemado del tile, que es donde el número informa:

| Banda | Tiles | WorldCover | MapBiomas | **CCS-BAP** |
|---|---|---|---|---|
| 0-10 % | 96 | 0,035 | 0,044 | 0,048 |
| 10-40 % | 62 | 0,029 | 0,043 | 0,053 |
| 40-70 % | 27 | 0,039 | 0,045 | 0,070 |
| **70-100 %** | 11 | 0,047 | 0,051 | **0,101** |

**Lectura.** CCS-BAP casi duplica el IoU del baseline, y en los tiles que contienen el borde
real del fuego la diferencia se agranda a 0,101 contra 0,047.

**Lo que el número no dice.** Los valores absolutos son bajos y **no miden la calidad del
modelo**: la referencia es la cicatriz final de semanas y la corrida es de 12 h, así que el
recall está acotado por construcción. Las ~62.000 ha "no predichas" son sobre todo tiempo de
simulación que no existió. Lo comparable es el orden entre mapas, no la magnitud.

---

## 5. Harness A — contra las detecciones de la ventana siguiente

Diez ventanas de 24 h repartidas en las cinco semanas de actividad del incendio (5 de enero
al 10 de febrero de 2026), tres mapas cada una: **30 corridas**. Cada ventana arranca a las
18:00 UTC, que es cuando cae el ciclo 18z del GFS y la pasada de la tarde de VIIRS.

- **Semilla**: todas las detecciones FIRMS hasta T0.
- **Referencia**: las detecciones nuevas de (T0, T1] que caen fuera de la semilla.
- **Recall cercano**: restringido a la referencia dentro de 5 km de la semilla, que es el
  alcance físico del frente en 24 h. Las detecciones más lejos son **igniciones nuevas**, y
  un modelo de propagación no predice dónde se inicia un foco: contarlas como error mide la
  ignición, no la propagación.

### Agregado sobre las diez ventanas

| Mapa | Recall | Recall cercano | Precisión | IoU | Acierto |
|---|---|---|---|---|---|
| WorldCover | 0,162 | 0,222 | 0,033 | 0,028 | 6.445 ha |
| MapBiomas | 0,283 | 0,387 | **0,068** | **0,058** | 11.253 ha |
| **CCS-BAP** | **0,342** | **0,467** | 0,048 | 0,044 | **13.587 ha** |

### El orden se repite ventana por ventana

| Ventana | WorldCover | MapBiomas | **CCS-BAP** |
|---|---|---|---|
| 06-01 | 0,030 | 0,090 | **0,099** |
| 08-01 | 0,181 | 0,432 | **0,488** |
| 09-01 | 0,133 | 0,157 | **0,201** |
| 20-01 | 0,180 | 0,432 | **0,546** |
| 24-01 | 0,142 | 0,355 | **0,458** |
| 25-01 | 0,104 | 0,294 | **0,315** |
| 31-01 | 0,729 | 0,740 | **0,937** |
| 01-02 | 0,438 | 0,494 | **0,671** |
| 06-02 | 0,793 | 0,981 | **1,000** |
| 07-02 | 0,794 | 0,556 | **0,952** |

**CCS-BAP tiene el mayor recall en las diez ventanas** y los dos mapas patagónicos superan
al baseline en nueve de diez. Que el orden se repita ventana por ventana, con semillas y
condiciones meteorológicas distintas cada vez, es lo que convierte el resultado del harness B
en algo más que una corrida afortunada.

---

## 6. La salvedad que limita todo lo anterior: el modelo sobre-propaga

| Ventana | Referencia | Predicho (CCS-BAP) | Veces la referencia |
|---|---|---|---|
| 06-01 | 12.318 ha | 3.135 ha | 0,3× |
| 08-01 | 6.032 ha | 10.286 ha | 1,7× |
| 09-01 | 4.979 ha | 10.102 ha | 2,0× |
| 20-01 | 1.951 ha | 21.900 ha | 11,2× |
| 24-01 | 2.529 ha | 28.859 ha | 11,4× |
| 25-01 | 6.447 ha | 36.177 ha | 5,6× |
| 31-01 | 1.454 ha | 41.700 ha | 28,7× |
| 01-02 | 3.711 ha | 73.280 ha | 19,7× |
| 06-02 | **63 ha** | 28.875 ha | **458×** |
| 07-02 | 260 ha | 27.850 ha | 107× |

Sobre las diez ventanas: 39.743 ha de referencia contra 282.164 ha predichas por CCS-BAP,
196.584 por WorldCover y 166.079 por MapBiomas.

**Un recall alto se consigue quemando de más.** El 6 de febrero CCS-BAP alcanza recall 1,000
prediciendo 28.875 ha contra una referencia de 63 ha: el número es correcto y no significa
nada. A partir del 20 de enero, cuando la semilla ya es grande, las tres corridas se desbocan.

Cuatro consecuencias, en orden de importancia:

1. **Las ventanas interpretables son las tres primeras** (6, 8 y 9 de enero), donde lo
   predicho está entre 0,3 y 2 veces la referencia. También ahí CCS-BAP gana en las tres.
2. **El recall agregado favorece al mapa que más superficie predice.** Por eso MapBiomas
   gana en IoU y precisión mientras CCS-BAP gana en recall: cada uno equilibra distinto las
   dos caras del error. **No hay un ganador único, y corresponde presentarlo así.**
3. **Falta modelar la supresión.** Los incendios reales se combaten; ELMFIRE corre sin
   extinción, así que nada frena una corrida libre de 24 h con una semilla grande. Es la
   explicación más simple de un factor 100 y está sin representar en todo el pipeline.
4. **`ADJ` sigue en 1,0 uniforme**, o sea sin calibrar. Calibrarlo corresponde *después* de
   la comparación de combustibles —antes absorbería el error del combustible y haría
   desaparecer la diferencia que se está midiendo— y este resultado es la evidencia de que
   hace falta.

---

## 7. Conclusiones

**Lo que está demostrado:**

1. **El resultado de ELMFIRE es fuertemente sensible al mapa de combustible.** Con todo lo
   demás congelado, el anillo de crecimiento a 12 h va de 2.342 ha (WorldCover) a 7.576 ha
   (CCS-BAP). Un empate habría invalidado toda la Etapa B.
2. **El mapa patagónico predice mejor que el baseline global**, con dos referencias
   independientes entre sí: IoU 0,067 contra 0,036 frente a la cicatriz de Sentinel-2, y
   mayor recall en las diez ventanas frente a las detecciones de FIRMS.
3. **El orden entre los tres mapas es estable**, no producto de una corrida.

**Lo que no está demostrado:**

1. **Las magnitudes absolutas no son citables.** Están acotadas por el desfase de horizonte
   en el harness B y contaminadas por la sobre-propagación en el harness A.
2. **Es un solo incendio.** Diez ventanas dan estadística sobre la ventana, no sobre el
   evento. Hace falta repetirlo en otro incendio para hablar de generalidad.
3. **No se comparó contra un modelo calibrado.** Con `ADJ` sin ajustar y sin supresión, lo
   que se mide es el efecto del insumo, no la habilidad predictiva del sistema.

**Lo que sigue, en orden:**

1. Modelar o acotar la supresión, o restringir la validación a ventanas de crecimiento libre.
2. Calibrar `ADJ` contra estas mismas ventanas, nunca antes.
3. Correr la duración completa del incendio: 37 días encadenados, estimados en unas 50 h de
   cómputo.
4. Repetir en un segundo incendio.

## 8. Benchmark sobre dos incendios nuevos (2026-09-27)

Método en `docs/resultados/IGN-26-VALIDACION.md` §Benchmark. Resultados versionados en
`benchmarks/iteraciones/`, visibles en la sección Validación del dashboard; la tabla cruzada sale
de `scripts/benchmark.py resumen`.

**Casos.**

- **Los Alerces 2023** (Población Rosales II, `los-alerces-2023/cadena-96h`): 1.067 ha según la
  cicatriz filtrada por evento.
- **Epuyén 2025** (La Rinconada, `epuyen-2025/cadena-96h-lago`): 2.995 ha.

Los dos arrancan de una **ignición puntual** a la hora reportada y corren **96 h en cuatro
ventanas de 24 h**. Cada ventana se siembra con lo que predijo la anterior; el modelo corre solo.
El clima son análisis GFS encadenados. Las referencias son la cicatriz dNBR filtrada por evento
(principal) y las detecciones VIIRS SP de cada ventana (diagnóstico).

**Métricas.**

- **Dice @96h** contra la cicatriz.
- **Sesgo de área** (predicho / observado), con alarma fuera de [0,5×, 2×].
- **Forma**: el Dice a área igualada, en la hora t\* en que lo predicho alcanza la superficie
  observada. Separa dónde quema el modelo de cuán rápido lo hace; las ~96 h reales son la
  referencia para t\*.

### 8.1 CCS-BAP gana en los dos incendios

| Mapa | Alerces Dice / sesgo / forma | Epuyén Dice / sesgo / forma |
|---|---|---|
| **CCS-BAP 2017** | **0,484** / 1,05 / **0,477** | **0,107** / 0,20 / **0,107** |
| MapBiomas (2022 / 2024) | 0,328 / 0,38 / 0,328 | 0,088 / 0,10 / 0,088 |
| WorldCover 2021 | 0,029 / 0,02 / 0,029 | 0,007 / 0,01 / 0,007 |

- **En Alerces CCS-BAP gana con margen**, y con la velocidad correcta: alcanza el área observada
  a las 93 h. WorldCover casi no propaga, porque su 42 % de TL3 lo frena.
- **En Epuyén los tres mapas se quedan muy cortos**, a una quinta parte de la superficie o menos:
  el día 1 el modelo quema 18 ha contra ~2.900 reales (§8.2). Aun así, el orden se repite.
- **Salvedad: en Epuyén el orden depende de la ignición** (§8.3). La cicatriz tiene 9 % de
  forestación exótica de pino, que el crosswalk lleva a **TL8** (hojarasca, lenta; IGN-20B §5). Es
  un punto concreto para revisar con el director.

### 8.2 La calibración mueve el reloj, no la forma

Barrido sobre `base-001` (CCS-BAP), un factor por receta:

| Receta | Alerces Dice / sesgo / forma / t\* | Epuyén Dice / sesgo / forma / t\* |
|---|---|---|
| base-001 | 0,484 / 1,05 / 0,477 / 93 h | 0,107 / 0,20 / 0,107 / no llega |
| ADJ 0,7 | 0,396 / 0,51 / 0,396 / no llega | — |
| ADJ 1,3 | 0,561 / 1,85 / 0,466 / 67 h | 0,178 / 0,29 / 0,178 / no llega |
| ADJ 1,6 | 0,495 / 2,95 ⚠ / 0,470 / 54 h | 0,326 / 0,61 / 0,326 / no llega |
| ADJ 2,0 | 0,362 / 4,49 ⚠ / 0,458 / 42 h | 0,428 / 1,09 / 0,418 / 92 h |
| viento ×1,6 | 0,519 / 1,37 / 0,470 / 80 h | 0,160 / 0,26 / 0,160 / no llega |
| humedad muerta −4 | 0,509 / 1,53 / 0,443 / 77 h | 0,284 / 0,65 / 0,284 / no llega |
| **humedad muerta −6** | **0,528 / 1,89 / 0,435 / 65 h** | **0,427 / 1,10 / 0,414 / 93 h** |
| ADJ 1,3 + humedad −4 | 0,531 / 2,54 ⚠ / 0,442 / 57 h | 0,438 / 1,17 / 0,416 / 91 h |
| humedad con historial de secado | 0,481 / 1,29 / 0,445 / 85 h | 0,096 / 0,18 / 0,096 / no llega |
| LW 150 / 200 % | 0,442 / 0,371 | — |
| sin fuego de copas | idéntico a base, byte a byte | idéntico a base |

1. **La forma no depende de ADJ, del viento ni de la humedad.** Una vez que el modelo alcanza el
   área, se queda en 0,44–0,48 en Alerces y en 0,41–0,42 en Epuyén. Lo que cambian esas
   perillas es t\*, cuándo llega. **El dónde lo pone el mapa de combustible, y la calibración
   sólo mueve el reloj.**
2. **La mejor receta sin alarma en ninguno de los dos es *humedad muerta −6*.** Dice medio 0,478
   contra 0,295 de base (**+62 %**). Llega al área observada a las 65 h en Alerces y a las 93 h en
   Epuyén.
3. **Epuyén está limitado por la humedad del combustible fino, no por el viento.** Viento ×1,6
   apenas mueve el resultado, y humedad −6 lo cuadruplica. Fue un día de calor extremo. El
   modelo necesita ~20 m/min para cubrir los 5 km que VIIRS ya ve a las 4 h, y con m1 ≈ 7 % y
   7 mph de viento del GFS da 1–3 m/min.
4. **Cada incendio pide su propia velocidad.** Alerces se calibra con la configuración base y
   Epuyén necesita m1 más seco o ADJ ≈ 2. Con −6, Alerces llega a las 65 h y con sesgo 1,89, en el
   borde de la alarma. Un parámetro global compensa un sesgo del clima de entrada que cambia de
   un incendio a otro.
5. **La humedad con historial de secado no es la palanca.** El modelo de retardo
   (τ = 1/10/100 h, 120 h de spin-up) baja mucho m100 (de 16–20 % a ~11 %), pero deja m1 igual y
   no mejora ninguno de los dos casos. El delta uniforme funciona porque baja m1, que sale directo
   de la temperatura y la humedad del GFS de 0,25°. **La corrección de fondo es un clima de
   superficie más fino** (estaciones, o reanálisis con corrección por altura), no un parámetro.
   ERA5-Land por Open-Meteo resultó aún más frío que el GFS en Epuyén: su celda está a 1.181 m.
6. **La receta no se transfiere a Patriada.** Con *humedad −6* y semilla observada
   (`humedad-m6-obs-001`, las diez ventanas del harness A), el recall sube de 0,342 a 0,406
   (cercano: de 0,467 a 0,555), pero la sobre-propagación empeora en todas las ventanas (la del
   6-feb pasa de 458× a 800×) e IoU y precisión bajan (0,044 → 0,038 y 0,048 → 0,040). En un
   incendio combatido con semillas grandes, secar el combustible agranda lo que ya sobraba:
   sin modelar la supresión, ninguna calibración de humedad sirve para los tres casos.
7. **El fuego de copas nunca se activa.** `CROWN_FIRE_MODEL` 0 y 1 dan un TOA idéntico byte a byte
   en Alerces y en Epuyén.

### 8.3 La ignición importa tanto como el mapa

El punto que traía mask-dataset-gen para Epuyén ("semilla aproximada" del filtro de evento,
-42,2921 / -71,4447) **está a 1.400 m, en la montaña**, 490 m fuera de la cicatriz. Las
crónicas ubican el origen "entre el cementerio y la Escuela 9, próximo al lago", en una
plantación de pinos. Hay tres protocolos versionados:

| Protocolo | Ignición | CCS-BAP | MapBiomas | WorldCover |
|---|---|---|---|---|
| `cadena-96h` | punto reportado, fuera de la cicatriz (1.400 m) | 0,118 | 0,166 | 0,033 |
| `cadena-96h-interior` | 210 m dentro de la cicatriz (1.331 m) | 0,135 | **0,225** | 0,181 |
| **`cadena-96h-lago`** | **junto a la localidad Lago Epuyén (348 m, TL8/TU5)** | **0,107** | 0,088 | 0,007 |

Con el punto de montaña, el modelo no tocó una sola detección en tres días. El orden de los
mapas se invierte según dónde se prende el fuego. Con la ignición más consistente con las
crónicas, CCS-BAP gana, y las recetas calibradas responden: *humedad −6* pasa de 0,261 a 0,427.
**La coordenada del filtro de evento de mask-dataset-gen conviene corregirla allá.**

### 8.4 Lo que no está demostrado

- **Dos incendios no alcanzan para fijar parámetros.** El delta de humedad compensa un sesgo del
  clima de entrada, y su valor bueno cambia de un incendio a otro.
- **Ningún incendio real corrió libre.** Los dos se combatieron, así que un Dice @96h alto con
  sesgo alto no es mejor modelo: es un modelo más rápido que llega antes a la cicatriz.
- **La dinámica dentro de cada ventana sigue mal.** El recall contra las detecciones de cada
  ventana queda bajo (0,02–0,2) en todas las recetas. El modelo llega al área final, pero no
  reproduce el día 1 explosivo de Epuyén.
- **En Epuyén el error tiene dirección.** El GFS da viento del oeste (~270°, ~10 mph a 20 pies)
  en la tarde del día 1, y el modelo avanza al este-sureste, donde están sus aciertos. Pero el
  fuego real llegó ~3,5 km más lejos en esa dirección, y el modelo además quema ladera arriba
  hacia el oeste (predicho sin observar a 699 m de altura media, contra la ignición a 348 m). Es
  velocidad insuficiente a favor del viento, con la pendiente dominando donde el viento es débil.
  La convención de dirección está verificada de punta a punta: con `wd = 0` el playground avanza
  al sur.

## 10. Re-medición con la interfaz corregida (2026-09-30)

Las mismas corridas de §4 y de la comparación preliminar, sobre los mismos insumos (misma
semilla, los mismos `fbfm40`), con los cinco errores de interfaz corregidos
(`scripts/corregir_preparacion_legado.py`; detalle en `docs/resultados/AUDITORIA-FISICA.md`, loop J, y §7.4).

**Comparación preliminar** (grilla reducida, semilla 8.095 ha, 12 h, LH 30 % / LW 110 %):

| Mapa | Anillo (antes → corregido) | FLI mediana (antes → corregido) |
|---|---|---|
| WorldCover 2021 | 2.342 → **3.892 ha** | 96,1 → 32,1 kW/m |
| MapBiomas 2024 | 5.849 → **7.268 ha** | 311,1 → 261,5 kW/m |
| CCS-BAP 2017 | 7.576 → **9.262 ha** | 317,0 → 234,8 kW/m |

IoU entre mapas: WorldCover–MapBiomas 0,302, WorldCover–CCS-BAP 0,344, MapBiomas–CCS-BAP 0,574.
El orden WorldCover < MapBiomas < CCS-BAP se sostiene y la diferencia se achica de 3,2× a 2,4×.
Las intensidades bajan porque el clima ahora cambia hora a hora: la primera banda era la más seca
y ventosa de las 12 h.

**Harness B** (§4). La referencia original (las 196 máscaras con la ventana pre de nov–dic 2023)
ya no existe en `mask-dataset-gen`; se puntuó contra `puerto-patriada-2026/runs/baseline-002`
(mismo algoritmo dNBR ≥ 0,30, las mismas 196 celdas, ventana pre nov 2025–ene 2026):

| Mapa | IoU (§4 / corridas viejas contra baseline-002 / **corregidas**) | Recall corregido | Precisión corregida |
|---|---|---|---|
| WorldCover 2021 | 0,036 / 0,035 / **0,010** | 0,010 | 0,205 |
| MapBiomas 2024 | 0,045 / 0,051 / **0,035** | 0,036 | **0,443** |
| CCS-BAP 2017 | 0,067 / 0,069 / **0,046** | **0,052** | 0,286 |

Estrato 70–100 % (11 tiles), corregidas: 0,010 / 0,034 / **0,056**. **El orden de IoU se
sostiene** (CCS-BAP > MapBiomas > WorldCover) y MapBiomas sigue con la mejor precisión. Los
valores bajan porque el anillo corregido es la mitad: la corrida vieja tenía 12 h de la tarde de
la ignición; la corregida atraviesa la noche. El anclaje de `SIMULATION_TSTART` de §3 no tenía
efecto en las corridas viejas.

**No re-corrido:** el harness A (§5) y el benchmark de dos incendios de §8, que se reemplaza por
la comparación sobre el benchmark v5 (`docs/resultados/COMPARACION-MAPAS-V5.md`).

## 9. Cómo reproducir

```bash
# 1. Los tres mapas sobre la misma grilla
uv run python scripts/build_fuel_maps.py

# 2. Las tres corridas de 12 h sobre una preparación existente
uv run python scripts/run_three_maps.py --base data/elmfire/inputs/<prep> --sufijo _aoi
uv run python scripts/compare_fuel_map_runs.py --runs aoi_worldcover aoi_mapbiomas aoi_ccsbap

# 3. Harness B: contra la cicatriz de Sentinel-2
uv run python scripts/score_against_observed.py --run cmp_aoi_ccsbap --caso feb2026_12h --mapa ccsbap

# 4. Harness A: diez ventanas de 24 h (reanudable)
uv run python scripts/harness_a.py
```

Benchmark (§8), con insumos inmutables y trazabilidad por receta:

```bash
uv run python scripts/benchmark.py empaquetar los-alerces-2023/cadena-96h
uv run python scripts/benchmark.py correr     los-alerces-2023/cadena-96h base-001 humedad-m6-001
uv run python scripts/benchmark.py tabla      los-alerces-2023/cadena-96h
uv run python scripts/benchmark.py resumen    # cada receta en cada incendio
uv run python scripts/benchmark.py verificar  los-alerces-2023/cadena-96h base-001
```

Los resultados de los harness originales quedan en `data/validation/`, y la sección **Validación** del dashboard los
dibuja: semilla, acierto, predicho sin observación y observado sin predecir, alternando entre
los tres mapas sobre el mismo caso.
