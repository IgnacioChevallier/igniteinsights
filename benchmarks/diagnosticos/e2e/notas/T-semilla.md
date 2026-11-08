# T · Por qué la semilla de P-24 queda fuera de la cicatriz (D-referencia §5, bug 4)

Script: `scripts/diagnostico_semilla.py` (`uv run python scripts/diagnostico_semilla.py`, ~4 min).
Test: `tests/test_diagnostico_semilla.py`. Tablas: `benchmarks/diagnosticos/e2e/datos/T*.csv`,
`T4_p24_semilla_filtrada.json`. Sólo lectura y sólo calibración: no se corrió ELMFIRE ni Earth Engine
y no se tocó mask-dataset-gen (sólo se leyeron los PRE/POST de sus runs).

## 0. Método

- **Semilla.** Para los 34 reinicios (k ≥ 1) de `*/pronostico-v6` (receta `lw-100-obs-001`; Alerces 2023
  3, Epuyén 6, Alerces 2024 8, Patriada 6, Alerces 2016 4, Cholila 7) se re-arma la semilla con la regla
  de `benchmark._pronostico`: `previo | ignición | reconstrucción(todas las detecciones SP de la caja
  hasta el reinicio)`. **Reproduce el `phi.tif` guardado en 34 de 34 reinicios, con 0 celdas distintas.**
  Ningún caso de pronóstico declara `semilla_inicial.radio_cicatriz_m` (`benchmark.py:704-708`). Tampoco
  hay detecciones anteriores a la ignición en ningún `firms.csv`.
- **Cicatriz.** La final completa (`cargar_cicatriz` sobre el run vigente), no la truncada. "Fuera" =
  semilla ∖ positivo, con la exclusión incluida. La cifra de D (26-61 %) es "fuera y no excluido". Acá
  sale 25-52 % de media por incendio y 12-61 % por reinicio. La exclusión dentro de la semilla es casi
  toda de Cholila (14 puntos); Alerces 2024 tiene 9 ha y el resto, nada.
- **Causas excluyentes**, asignadas en este orden:
  - **a. Detecciones ajenas**: lo que desaparece al sembrar sólo con las detecciones a ≤ r de la
    cicatriz. Es el filtro oráculo `radio_cicatriz_m`, con r = 500, 1000 y 2000 m.
  - **e. Quema real que la cicatriz no marca**: celda excluida (sin observación, cambio no confirmado u
    otro incendio) o con 0,1 ≤ dNBR < 0,3. El dNBR se recomputa de los PRE/POST guardados, sin máscara
    de nubes (es un proxy, con dato en el 44-99 % de la grilla).
  - **b. Margen geométrico**: fuera del núcleo. El núcleo es el casco cóncavo sin el buffer de 187,5 m
    o, en los clústeres de menos de 4 detecciones, el punto mismo (llevan disco de 375 m).
  - **d. Huella del píxel o geolocalización**: dentro del núcleo y dentro del rectángulo scan × track
    real de alguna detección legítima.
  - **c. Relleno del casco**: dentro del núcleo y fuera de toda huella. Son huecos internos que ninguna
    detección cubre.

  Las causas b, c y d se miden contra la semilla ya filtrada (r = 1000 m salvo que se diga otra cosa).
  "Lejos" significa a más de 375 m del borde de la cicatriz.

## 1. Descomposición (oráculo r = 1000 m; ha = media por reinicio)

| Incendio | semilla ha | fuera ha (% semilla) | a | e | b | d | c | lejos, % semilla |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 658 | 303 (46 %) | 0 % | 12 % | 37 % | 49 % | 2 % | 6 % |
| Epuyén 2025 | 2.987 | 1.151 (39 %) | 8 % | 21 % | 20 % | 40 % | 11 % | 13 % |
| Alerces 2024 | 2.178 | 846 (39 %) | 17 % | 14 % | 17 % | 38 % | 15 % | 18 % |
| Patriada 2026 | 7.870 | 4.678 (59 %) | 2 % | 17 % | 10 % | 47 % | 25 % | 28 % |
| Alerces 2016 | 1.724 | 429 (25 %) | 0 % | 21 % | 38 % | 35 % | 6 % | 2 % |
| Cholila 2015 | 7.682 | 3.994 (52 %) | **59 %** | 13 % | 4 % | 14 % | 10 % | 33 % |
| **34 reinicios** | 4.271 | 2.127 (50 %) | **26 %** (547 ha) | 16 % (331) | 10 % (217) | 33 % (692) | 16 % (341) | 25 % |
| sin Cholila | | | 5 % | 17 % | 14 % | 44 % | 20 % | |

Las columnas a-e son el % de lo que queda fuera de la cicatriz.

**Sensibilidad de (a) al radio** (ha por reinicio):

| r | Cholila | Epuyén | Alerces 2024 | Patriada | Alerces 2016 y 2023 |
|---|---:|---:|---:|---:|---:|
| 500 m | 2.343 | 208 | 260 | 428 | 9-10 |
| 1000 m | 2.343 | 94 | 143 | 83 | 0 |
| 2000 m | 2.343 | 0 | 0 | 0 | 0 |

En Cholila, (a) no cambia con el radio: las 197 detecciones que se descartan están a más de 2 km de la
cicatriz objetivo. En los otros incendios, lo que se pierde entre 1000 y 2000 m son 2 a 15 detecciones
a 1-2 km de la cicatriz, encadenadas al frente. Ningún radio saca semilla que esté dentro de la
cicatriz.

**Lejos (> 375 m del borde).** Es el 51 % de lo que queda fuera: 1.077 ha por reinicio, un 25 % de la
semilla (2-33 % según el incendio y 0-35 % por reinicio). Por causa, ese "lejos" se reparte así: (a)
51 %, (d) 18 %, (c) 17 %, (b) 10 % y (e) 4 %. Todo (a) cae lejos. De (c) cae lejos el 54 %, de (b) el
48 %, de (d) el 29 % y de (e) el 14 %.

**Geolocalización (T3).** Entre las detecciones legítimas, el centro cae fuera de la cicatriz en el
21-35 % de los casos, con una mediana de 64-104 m. Sólo el 0,7-4,7 % cae a más de media diagonal de su
huella (mediana 320-370 m; scan × track mediano de 0,42-0,49 × 0,46-0,51 km, contra 0,375 nominal). El
error de geolocalización no aparece como causa propia: es la huella del píxel, y por eso (d) las junta.
La huella se modela como un rectángulo alineado a la grilla, aunque la órbita está inclinada unos
10-15°.

## 2. Respuestas

### 2.1 Bug o incertidumbre del píxel

- **Bug: detecciones de otros incendios, (a).** Explica el 26 % del área de afuera (547 ha por
  reinicio), toda a más de 375 m, y es la mitad de todo lo que queda lejos. Es casi entero de
  Cholila: 197 detecciones a más de 2 km de la cicatriz, que son el 59 % de su área de afuera y el 31 %
  de su semilla. El empaquetado de pronóstico siembra con todas las detecciones de la caja. En los
  otros 5 incendios, (a) es 0-17 % con r = 1000 m y 0 % con r = 2000 m. Ahí lo que se descarta son
  detecciones conectadas al frente, que es más probable que sean quema que la cicatriz no marca
  (focos secundarios o baja severidad) que otro incendio.
- **Incertidumbre esperable del píxel de 375 m: (b) + (d).** Es el 43 % del área de afuera (58 % sin
  Cholila), sobre todo a menos de 375 m del borde. Las detecciones legítimas caen donde su huella
  permite.
- **Ni bug ni píxel: (c) y (e).** El relleno del casco, (c), es el 16 % (25 % en Patriada) y la mitad
  cae lejos. Viene de la regla elegida (casco cóncavo sin huecos, ratio 0,4) y es la principal
  sobrestimación que queda una vez corregido el bug. (e), el 16 %, es un faltante de la referencia y no
  un error de la semilla.

### 2.2 Filtro aplicable en tiempo real

La regla probada (`conexas`) toma las detecciones hasta el reinicio y conserva la componente de enlace
simple, con saltos de ≤ s, que contiene alguna detección a ≤ 5 km del punto de ignición. Esa distancia
es `alcance_m`: en Epuyén las primeras detecciones caen a 1,5-3 km del punto. La regla es monótona en
el tiempo y no usa la cicatriz.

| Regla | (a) en Cholila, ha/reinicio | cicatriz perdida en Cholila | cambia algo en los otros 5 | reinicios que cambian |
|---|---:|---:|---|---:|
| oráculo 1000 m | 2.343 (445 detecciones) | 0 | sí: 2-15 detecciones a 1-2 km | 21 |
| oráculo 2000 m | 2.343 | 0 | no | 5 |
| **conexa, s = 3000 m** | **2.343 (las mismas 445 detecciones)** | **0** | no | **5** |
| conexa, s = 1500 m | 2.358 | 78 ha | Epuyén, 37 ha | 10 |
| conexa, s = 750 m | 2.754 | 1.109 ha | Epuyén y Patriada | 12 |

Con s = 3000 m, la regla de tiempo real es idéntica al oráculo de 2000 m en las 34 semillas y en el
re-puntaje. Con saltos más cortos se parte el frente legítimo en los huecos entre pasadas y se pierde
cicatriz. Lo que el oráculo de 1000 m saca de más (detecciones encadenadas al frente) no se puede
separar sin la cicatriz, y vale poco (§2.3). La regla no ataca (b), (c) ni (d). Para eso habría que
cambiar la reconstrucción misma (casco con huecos o buffer menor), fuera de este alcance.

### 2.3 Sesgo y Dice de P-24 sin el anillo, con la semilla filtrada

El re-puntaje usa `pronostico.puntuar` actual, que ya excluye el anillo; con la semilla actual da
+0,096 / +0,131, como la nota D. Es una **aproximación sin ELMFIRE**: lo que el filtro saca de la semilla
deja de estar quemado, y cada celda de crecimiento se atribuye a la celda de semilla más cercana
(Voronoi). Se conserva sólo si esa celda sigue en la semilla filtrada. La persistencia y la referencia
sí se recomputan exactas.

| Semilla | ΔDice vs cadena 12 / 24 h | ΔDice vs persistencia 12 / 24 h | Dice Cholila 12 / 24 h | sesgo mediano 12 / 24 h |
|---|---|---|---|---|
| actual | +0,096 / +0,131 (6/6, 5/6) | +0,060 / +0,142 | 0,070 / 0,262 | 2,40 / 3,11 |
| conexa 3000 = oráculo 2000 | +0,096 / +0,131 | +0,063 / +0,142 | 0,078 / 0,327 | 2,40 / 2,52 |
| oráculo 1000 | +0,101 / +0,142 | +0,064 / +0,145 | 0,078 / 0,327 | 2,24 / 2,52 |

El sesgo mediano se toma sobre todos los reinicios. Corregir el bug sólo mueve Cholila: el Dice sube
+0,008 a 12 h y +0,065 a 24 h, y el sesgo medio a 24 h baja de 3,66 a 2,12. La mediana entre incendios
no se mueve, porque Cholila no es el incendio mediano. Con el oráculo de 1000 m el Dice de Alerces
2024 a 12 h sube de 0,34 a 0,37.

El oráculo de 500 m (+0,108 / +0,159) no es un filtro de incendios ajenos: recorta detecciones
legítimas a 500-1000 m que dan forma al casco.

**Corrida exacta.** Necesita 5 corridas de ELMFIRE: los 5 reinicios de Cholila cuya semilla cambia. En
los otros incendios la semilla queda idéntica. El cambio va en el empaquetado y no en la física, así que
no hace falta una receta nueva: un protocolo `cholila-2015/pronostico-v7` (v6 + filtro conexo de 3000 m
en `_pronostico`) corrido con `lw-100-obs-001` tal cual. Si la convención exige una receta propia,
sería `lw-100-obs-conexa-001`, con padre `lw-100-obs-001`, sin cambios físicos y documentando el
protocolo. La variante del oráculo de 1000 m necesitaría 21 corridas.

## 3. Límites

- La aproximación de §2.3 no ve que el frente legítimo pueda llegar en 12-24 h a lo que se sacó. Tiende
  a sobrestimar la mejora donde lo sacado está pegado al frente (oráculos de 500 y 1000 m). En Cholila
  lo sacado está a más de 2 km.
- El dNBR de (e) no tiene máscara de nubes, y en Landsat (Cholila, Alerces 2016) la fidelidad del proxy
  es 0,78 (D §4). Por eso (e) es indicativo.
- El casco cóncavo no es monótono: con menos puntos, la semilla filtrada puede salirse de la original
  (≤ 146 ha en Alerces 2024 con 500 m; 0 con 2000 m y con la regla conexa).
