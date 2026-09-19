# Resultados de validación — comparación de tres mapas de combustible

> **Corte al 2026-09-19.** Este documento reúne los números; el método vive en
> `IGN-26-VALIDACION.md` (diseño de validación), `IGN-20B-CROSSWALK-CCSBAP.md` (crosswalk
> de CCS-BAP) e `IGN-20-CROSSWALK.md` (crosswalk de MapBiomas). Si algún número de acá
> discrepa con esos documentos, mandan ellos: son los que se regeneran con cada corrida.
>
> Todo es reproducible: `scripts/build_fuel_maps.py`, `scripts/run_three_maps.py`,
> `scripts/harness_a.py`, `scripts/score_against_observed.py`.

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

## 8. Cómo reproducir

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

Los resultados quedan en `data/validation/`, y la sección **Validación** del dashboard los
dibuja: semilla, acierto, predicho sin observación y observado sin predecir, alternando entre
los tres mapas sobre el mismo caso.
