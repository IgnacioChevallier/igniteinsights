# Y · ¿Pavesas condicionadas? Reglas previas y decreto

> 2026-10-23. Sigue a [X](X-pavesas-calibracion.md): `lw-100-pavx10-001`, como escalar global, no
> pasa la puerta. Acá se busca una regla que encienda las pavesas sólo en ciertos incendios o
> ventanas, sin mirar el resultado. §1 se registró antes de calcular ninguna variable nueva: sólo se
> conocían las tablas de X §2, de G §7 y §10, y el chequeo P-24 de `DIA-1-PROPUESTA.md` §7.6.

## 1. Diseño registrado (antes de calcular)

### 1.1 Qué decide una regla

Una regla mira una variable previa y decide, por incendio, `lw-100-001` (sin pavesas) o
`lw-100-pavx10-001` (con pavesas). Como las dos recetas ya corrieron en los 7 casos, el Dice de una
regla por incendio se arma sin ELMFIRE: en cada caso se toma el de la receta que eligió.

Una regla por ventana no se puede armar así: la cadena siembra cada ventana con la predicción de la
anterior. Si alguna aparece, se informa como límite y se acota con el techo por incendio.

### 1.2 Familias candidatas

Todas las variables se miden en un disco de 5 km alrededor de la ignición, igual que el chequeo
exploratorio previo. Ese radio no sale de estos incendios: es el `alcance_m` de la referencia FIRMS
de los casos. Cada regla lleva un único estadístico, fijado acá. El sentido es siempre el físico:
más viento, más seco o más intenso → encender.

**(a) Meteorología pronosticada** (GFS o ERA5; disponible antes de correr, en el paquete).

| regla | variable | umbral | de dónde sale el umbral |
|---|---|---|---|
| a1 | viento a 20 ft: máximo horario de la media en el disco, en todas las ventanas | ≥ 15 mph | Bandera Roja del NWS: varía por oficina entre 15 y 25 mph sostenidos (o ráfagas de 25-35 mph). Se toma el más permisivo |
| a2 | FFWI (Fosberg, 1978) con la m1 del paquete como humedad de equilibrio: máximo horario en el disco | ≥ 50 | SPC/NOAA: valores ≥ 50 «resultan significativos a escala nacional». La escala llega a 100 con 30 mph y humedad 0 |
| a3 | Bandera Roja combinada: alguna hora con viento ≥ 15 mph **y** HR ≤ 25 % (`rh_gfs`) en el disco | se cumple | la combinación más permisiva de los criterios del NWS |

Haines y el índice cálido-seco-ventoso (HDW) necesitan niveles de 850/700 hPa o el perfil de los
primeros 500 m. Los paquetes sólo traen superficie (`t2m_gfs`, `rh_gfs`, `ws`, `wd`): no se
evalúan. No se registra ningún umbral sólo de m1: no se encontró uno de literatura para pavesas que
no venga atado al viento.

**(b) Meteorología observada** (viento de estación). Hoy sólo existe para Las Golondrinas (SYNOP El
Bolsón, G §10). Depende de las series pedidas al INTA y a Bosques de Chubut. Umbral: el mismo de a1.
No se puede evaluar en la calibración: los casos corren con GFS o ERA5.

**(c) Crecimiento observado en P-24** (disponible en el reinicio k si el reinicio k−1 tiene ya 12 h
de observación). Disparo: sesgo del crecimiento a 12 h del reinicio k−1 < 0,5, con ≥ 50 ha
observadas. Se informan además 0,3 y 0,7. Los umbrales son los del chequeo previo: 0,5 es la cota
inferior de la banda sin alarma de la puerta ([0,5, 2]), así que no sale de estos incendios, pero
0,3 y 0,7 son exploratorios. Sin ELMFIRE sólo se puede contar en qué reinicios se enciende y si ahí
el modelo base venía corto (sesgo a 24 h < 1) o ya se pasaba. Se informa el caso sin señal
disponible (k−1 a menos de 12 h): (c-causal) la regla no se dispara; (c-última) usa la última
señal de 12 h ya cerrada.

**(d) Lo que predice el modelo sin pavesas** (sale de la corrida base `lw-100-001`, antes de
comparar con nada). Sobre las celdas quemadas en toda la cadena (TOA > 0), con `flin_*.tif`:

| regla | variable | umbral | de dónde sale |
|---|---|---|---|
| d1 | fracción de celdas con `flin` ≥ 3.460 kW/m | ≥ 50 % | Andrews y Rothermel (1982), haul chart: ≥ 1.000 Btu/ft/s (11 ft de llama), «copa, pavesas y corridas mayores son comunes» |
| d2 | fracción de celdas con `flin` ≥ 1.000 kW/m | ≥ 50 % | `CRITICAL_SPOTTING_FIRELINE_INTENSITY` de la plantilla de ELMFIRE: la intensidad desde la que lanza pavesas de superficie |
| d3 | fracción de celdas con dosel (cc > 0, cbd > 0) y `flin` ≥ la crítica de Van Wagner (`copa.intensidad_critica(cbh)`) | ≥ 50 % | la condición con la que ELMFIRE lanza pavesas de copa (`elmfire_level_set.f90:773-776`) |

El 50 % es la mediana: «el incendio típico de la corrida está en esa clase». No sale de estos
incendios, pero tampoco de la física; si una regla d pasa sólo con ese corte, se informa la
sensibilidad a 25 % y 75 %. Supuesto a verificar: `flin_*.tif` es la intensidad de superficie (la
que usa el criterio de copa). Si incluye la copa, d3 sobrestima.

**(e) Combustible y terreno del dominio** (sin la cicatriz).

| regla | variable | umbral | de dónde sale |
|---|---|---|---|
| e1 | la celda de ignición es plantación (TL8, `fbfm40` 188) | sí | plantaciones de pino sin podar: copa y pavesas (Paritsis et al., 2018; DECISIONES-MODELO-V0 §5) |
| e2 | hay agua (`fbfm40` 98) en el disco, en el sector de ±45° a sotavento del viento medio de la primera ventana | sí | sin pavesas el fuego no cruza agua (G §6.4) |

Las dos son binarias: no tienen umbral que elegir.

### 1.3 Variables prohibidas

La cicatriz final, el sesgo y el Dice de cualquier corrida de calibración, el área observada final y
todo lo que no exista al momento de pronosticar. El sesgo de la familia (c) es la excepción
declarada: es el de un reinicio anterior, ya cerrado. Aun así usa la cicatriz como referencia; en
tiempo real habría que medirlo contra FIRMS, así que (c) es una cota optimista.

### 1.4 Criterio del decreto (fijado antes de calcular)

- **«No se usan»** si se cumple cualquiera de estas condiciones:
  - el techo por incendio no pasa la puerta;
  - ninguna regla con umbral previo alcanza la puerta en el chequeo sin ELMFIRE;
  - la única regla que la alcanza depende de datos que no existen (familia b).
- **«Probar la regla»** si alguna regla con umbral previo, aplicada a lo ya corrido, cumple la
  puerta completa de X §1.1: media ≥ 0,459, ninguna alarma nueva (sin el caso límite) y validación
  cruzada que no empeore (media fuera de muestra ≥ 0,416). La validación cruzada se hace con la
  lógica de `benchmark.py validar`, sumando la regla como una receta compuesta más.
- **Entre medio** (por ejemplo, una regla por ventana que sólo se puede acotar): se informa sin
  veredicto y se decreta «no se usan por ahora», con la condición que lo reabriría.

### 1.5 Regla de método

Con 6 casos informativos, una variable que los separe hallada por búsqueda es sobreajuste. Sólo
valen los umbrales de §1.2. Si después se informa un umbral elegido mirando los casos, va marcado
«exploratorio» y no puede llevar a un decreto positivo.

## 2. Chequeo sin ELMFIRE (2026-10-23)

Scripts descartables, sin código nuevo en el repo (apéndice). Las tablas de calibración salen de
`benchmark._filas`; los insumos y salidas, de
`data/benchmark/trabajo/<caso>/<protocolo>/lw-100-001/v*/`.

### 2.1 Techo por incendio y conjuntos que pasan

Sin redondear, por caso (Dice / sesgo):

| Caso | `lw-100-001` | `lw-100-pavx10-001` | mejor sin alarma |
|---|---|---|---|
| Alerces 2023 (h54) | 0,528 / 1,86 | 0,555 / 2,42 ⚠ | sin |
| Epuyén 2025 | 0,501 / 1,41 | 0,418 / 2,92 ⚠ | sin |
| Alerces 2024 | 0,635 / 1,35 | 0,658 / 1,50 | con |
| Patriada 2026 | 0,496 / 0,70 | 0,574 / 0,85 | con |
| Las Golondrinas (límite) | 0,0116 / 0,021 | 0,0125 / 0,022 | con (+0,001) |
| Alerces 2016 (ERA5) | 0,389 / 1,69 | 0,309 / 2,42 ⚠ | sin |
| Cholila 2015 (ERA5) | 0,513 / 0,87 | 0,630 / 1,49 | con |

**Techo: 0,4702**, sin alarmas. Pasa la puerta por +0,011 y queda +0,031 sobre modelo-v0 (0,4391).
La validación cruzada, con la regla oráculo sumada como receta compuesta, la elige en los 7 pliegues
(0,4702 ≥ 0,416). Se confirma el ≈ 0,470 del encargo.

De los 128 conjuntos posibles de incendios encendidos, **6 pasan la puerta**. Todos cumplen lo mismo:
- encienden Cholila;
- encienden Alerces 2024, Patriada o los dos;
- dejan apagados Alerces 2023, Epuyén y Alerces 2016.

El menor que pasa es {Alerces 2024, Cholila}: 0,4590, en el borde. Las Golondrinas no cambia nada.
Entonces una regla pasa si y sólo si separa {Cholila + Alerces 2024 o Patriada} de {Alerces 2023,
Epuyén, Alerces 2016}. Si los seis casos informativos estuvieran ordenados al azar por una variable,
la probabilidad de que los tres que hay que apagar queden abajo sería 1/20.

### 2.2 (a) Meteorología pronosticada: no se dispara en ningún caso

Disco de 5 km alrededor de la ignición, todas las ventanas de la cadena:

| Caso | viento medio (mph) | viento máx. horario (mph) | FFWI máx. | m1 mín. (%) | HR mín. día 1 (%) |
|---|---:|---:|---:|---:|---:|
| Alerces 2023 | 5,4 | 9,7 | 17,7 | 5,5 | 28 |
| Epuyén | 5,1 | 10,2 | 21,2 | 4,1 | 37 |
| Alerces 2024 | 5,0 | 10,1 | 21,8 | 4,6 | 24 |
| Patriada | 4,0 | 7,7 | 18,9 | 3,7 | 18 |
| Las Golondrinas | 7,0 | 9,3 | 22,3 | 4,6 | 20 |
| Alerces 2016 (ERA5) | 4,4 | 8,3 | 19,3 | 4,2 | 18 |
| Cholila (ERA5) | 3,6 | 8,5 | 16,5 | 6,3 | 34 |

- **a1** (viento ≥ 15 mph): ningún caso. El máximo es 10,2 mph.
- **a2** (FFWI ≥ 50): ningún caso. El máximo es 22,3, menos de la mitad del umbral.
- **a3** (Bandera Roja combinada): ningún caso. Hay HR ≤ 25 % (Patriada, Alerces 2016, Las Golondrinas,
  Alerces 2024), pero nunca a la vez que viento ≥ 15 mph.

La regla queda en modelo-v0: 0,439, que no pasa. Se confirman los números del chequeo previo. Y aunque
se buscara un umbral, el orden no sirve: Cholila, la que más mejora, tiene el viento medio más bajo
y la m1 más alta. Patriada, que también mejora, es la más seca. Con la HR del GFS se mide en la celda
de 0,25° de la ignición, no en el disco.

### 2.3 (d) Lo que predice el modelo sin pavesas: no se dispara con el umbral registrado

Celdas quemadas en toda la cadena base (TOA > 0 en cada ventana):

| Caso | celdas | d1: `flin` ≥ 3.460 | d2: `flin` ≥ 1.000 | d3: copa de ELMFIRE | `flin` p50 / p90 (kW/m) |
|---|---:|---:|---:|---:|---|
| Alerces 2023 | 21.742 | 1,1 % | 3,0 % | 3,8 % | 121 / 421 |
| Epuyén | 37.975 | 1,3 % | 3,4 % | 4,9 % | 113 / 508 |
| Alerces 2024 | 42.391 | 1,9 % | 4,1 % | 5,2 % | 112 / 530 |
| Patriada | 44.721 | 2,0 % | 4,9 % | 5,2 % | 114 / 533 |
| Las Golondrinas | 2.494 | 0,8 % | 4,9 % | 3,3 % | 57 / 669 |
| Alerces 2016 | 27.823 | 1,1 % | 3,3 % | 5,4 % | 97 / 440 |
| Cholila | 86.014 | 10,6 % | 20,5 % | 21,3 % | 140 / 3.803 |

Con el corte registrado (50 %), **ninguna regla d se dispara**: el máximo es Cholila, con 21 %. Con
25 % o 75 % tampoco. La regla queda en modelo-v0 (0,439).

**Exploratorio: un orden que coincide con el techo.** Si se busca el corte, d1 y d2 separan
exactamente lo que pide §2.1:
- d1 con un corte entre 1,3 % y 1,9 % enciende {Alerces 2024, Patriada, Cholila}: 0,4701;
- d2 con un corte entre 3,4 % y 4,1 % enciende además Las Golondrinas: 0,4702.

Las dos llegan al techo, sin alarmas. El orden se mantiene con cualquier intensidad entre 500 y
10.000 kW/m. En una validación anidada, con el corte elegido sin el caso que queda afuera, d1 da
0,470 y d2 0,467 fuera de muestra. Aun así, no es una regla:

1. **El corte sale de buscarlo.** Lo prohíbe §1.5.
2. **Los márgenes son mínimos.** Epuyén queda a 0,6 puntos de Alerces 2024 en d1 (1,3 % contra
   1,9 %) y a 0,7 en d2. En la validación anidada, Epuyén se apaga por 0,002 contra un corte de 0,015.
3. **La variable del mecanismo no separa.** d3 son las celdas desde las que ELMFIRE lanza pavesas de
   copa, el 10 % de la receta. Ahí Alerces 2016 (5,4 %) queda por encima de Alerces 2024 y Patriada
   (5,2 %).
4. **Sólo vale sobre la cadena entera.** Con la primera ventana, la que importa para decidir
   temprano, Alerces 2016 sube (4,0 % sobre 1.730 kW/m, contra 3,1 % de Alerces 2024) y el orden se
   rompe.
5. **No predice lo que hacen las pavesas.** Con pavesas, el área crece ×2,08 en Epuyén, la de d1
   más baja entre las que importan, y ×1,11 en Alerces 2024. Lo que separa a los casos que mejoran
   sigue siendo si el modelo base ya se pasaba (X §3), y eso es el resultado.
6. **El azar alcanza.** Para una variable, la probabilidad de este orden por azar es 1/20. Se
   miraron al menos tres variables d y tres a.

### 2.4 (e) Combustible y terreno: se disparan, pero encienden casos con alarma

| Caso | modelo en la ignición | TL8 en el disco | celdas de agua a sotavento |
|---|---|---:|---:|
| Alerces 2023 | SH4 (144) | 0,5 % | 1.559 |
| Epuyén | **TL8 (188)** | 5,5 % | 0 |
| Alerces 2024 | TU5 (165) | 0 % | 0 |
| Patriada | SH4 (144) | 1,0 % | 1.012 |
| Las Golondrinas | TU3 (163) | 10,5 % | 0 |
| Alerces 2016 | TU5 (165) | 0,6 % | 1.374 |
| Cholila | TL6 (186) | 0 % | 38 |

- **e1** (ignición en plantación) enciende sólo Epuyén: 0,427 y una alarma. Con TU5 en lugar de TL8
  (exploratorio), enciende Alerces 2024 y Alerces 2016, con alarma en Alerces 2016.
- **e2** (agua a sotavento) enciende Alerces 2023, Patriada, Alerces 2016 y Cholila: 0,459, pero con
  dos alarmas (Alerces 2023 y Alerces 2016).

### 2.5 (c) Crecimiento observado en P-24: se dispara donde el modelo ya se pasaba

Sobre `benchmarks/iteraciones/*/pronostico-v7/lw-100-obs-001/pronostico.json`. Disparo: sesgo a
12 h del reinicio anterior por debajo del umbral, con ≥ 50 ha observadas. «Corto» quiere decir que
el sesgo propio a 24 h es < 1.

| Señal | umbral | disparos | corto | ya se pasaba |
|---|---:|---:|---:|---:|
| reinicio anterior, disponible o no | 0,3 | 7 | 3 | 4 |
| | 0,5 | 11 | 3 | 8 |
| | 0,7 | 11 | 3 | 8 |
| (c-causal) sólo si ya pasaron 12 h | 0,3 / 0,5 / 0,7 | 1 | 0 | 1 |
| (c-última) última señal de 12 h cerrada | 0,3 / 0,5 / 0,7 | 5 | 1 | 4 |

- Los tres cortos son los del chequeo previo: Alerces 2024 k1 (0,22) y Patriada k1 y k2 (0,45 y
  0,71). Los que ya se pasaban van de 1,08 (Alerces 2016 k1) a 107 (Patriada k4).
- El chequeo previo contó 13 disparos, con 10 que ya se pasaban; acá salen 11, con 8. El rango y la
  conclusión son los mismos. La diferencia no se pudo rastrear sin el script original.
- **La señal casi nunca está a tiempo.** 21 de los 34 reinicios llegan a menos de 12 h del
  anterior. Con la versión causal, la regla se dispara una sola vez (Alerces 2024 k2), y ahí el
  modelo ya se pasaba (1,16). Los tres cortos son reinicios a 2-6 h del anterior, o la señal que
  los dispara es de la primera ventana, que es el déficit del día 1 (cerrado como límite).
- Además usa la cicatriz como referencia: en tiempo real sería FIRMS. Es una cota optimista.

(c) decide por reinicio, no por incendio: no se puede puntuar sin correr ELMFIRE. Pero, aun en su
versión más generosa, se dispara más veces donde el modelo ya se pasaba que donde venía corto.

### 2.6 (b) Meteorología observada

Sólo existe para Las Golondrinas. Ahí las pavesas valen ×4,9 con el SYNOP de El Bolsón (29 kt) y ×1,0
con el GFS (X §3, G §7). Con el viento observado, a1 se dispararía, pero el caso es el límite y no
cuenta para la puerta. Para el resto de los incendios no hay series: dependen de los pedidos al INTA
y a Bosques de Chubut.

### 2.7 Resumen por regla

| Regla | umbral | enciende | media | alarmas | fuera de muestra | contra el techo |
|---|---|---|---:|---:|---:|---:|
| ninguna (modelo-v0) | — | — | 0,439 | 0 | 0,416 | −0,031 |
| a1, a2, a3 | previo | ninguno | 0,439 | 0 | 0,416 | −0,031 |
| d1, d2, d3 (50 %) | previo | ninguno | 0,439 | 0 | 0,416 | −0,031 |
| e1 | previo | Epuyén | 0,427 | 1 | 0,416 | −0,043 |
| e2 | previo | A23, Patriada, A16, Cholila | 0,459 | 2 | 0,416 | −0,011 |
| (c) | previo | por reinicio: no se puntúa | — | — | — | — |
| (b) | previo | sólo Las Golondrinas, con datos que no existen en calibración | — | — | — | — |
| d1 ≥ 1,5 % | **exploratorio** | A24, Patriada, Cholila | 0,470 | 0 | 0,470 (anidada) | 0 |
| d2 ≥ 3,75 % | **exploratorio** | A24, Patriada, Golondrinas, Cholila | 0,470 | 0 | 0,467 (anidada) | 0 |
| techo (oráculo) | — | A24, Patriada, Golondrinas, Cholila | 0,470 | 0 | 0,470 | — |

**Ninguna regla con umbral previo alcanza la puerta.** La mejor sin alarmas es no encender nunca:
recupera 0 de los +0,031 del techo.

## 3. Corridas

Ninguna. El chequeo sin ELMFIRE ya decide (§1.4): no hizo falta ELMFIRE ni `materializar`.

## 4. Decreto

**Las pavesas no se usan en modelo-v0 ni como regla condicionada.** Se cumple la segunda condición
de §1.4: ninguna regla con umbral previo alcanza la puerta. Evidencias:

1. El techo por incendio existe (0,470, +0,031) y exige separar {Cholila + Alerces 2024 o Patriada}
   de {Alerces 2023, Epuyén, Alerces 2016} (§2.1).
2. La meteorología pronosticada no llega a ningún umbral de literatura. El viento máximo es 10,2 mph,
   contra 15 mph; el FFWI máximo es 22, contra 50. Y ni siquiera ordena bien los casos: Cholila es la
   más húmeda y la de menos viento (§2.2).
3. El combustible y el terreno, con reglas binarias, encienden casos con alarma (§2.4).
4. La intensidad que predice el modelo base no llega al umbral físico. Su orden coincide con el techo
   sólo si se busca el corte, con márgenes de menos de un punto, y no en la variable del mecanismo
   (§2.3).
5. El crecimiento observado en P-24 se dispara más donde el modelo ya se pasaba. En su versión
   causal, una sola vez y a destiempo (§2.5).
6. La única evidencia fuerte a favor (Las Golondrinas, ×4,9) necesita viento observado, que en
   calibración no existe (§2.6, tercera condición).

**Qué lo reabriría** (cualquiera de las dos):
- **Viento observado** en los incendios de calibración (series del INTA o de Bosques de Chubut) que
  pase 15 mph a 20 ft en alguno distinto de Las Golondrinas. Ahí a1 se evalúa como está registrada,
  con la puerta de X §1.1.
- **Una prueba independiente de d1, con el corte fijado hoy:** fracción de celdas quemadas en la
  cadena base con `flin` ≥ 3.460 kW/m **≥ 1,5 %** → encender. Se registra acá y no se toca. Vale
  sólo sobre incendios que no sean estos 7. La decisión de usar para eso los 4 de prueba, que hoy no
  se abren, es del autor.

## 5. Propuesta de texto (no aplicada)

**`RIESGOS_Y_SUPOSICIONES.md` §3**, como entrada nueva:

> **Pavesas: mecanismo faltante declarado.** modelo-v0 corre sin `&SPOTTING`. Como escalar global
> (`lw-100-pavx10-001`, 10 % de las celdas en copa y 1 % en superficie), las pavesas no pasan la
> puerta: media 0,451, tres alarmas (X). Encenderlas por incendio tendría un techo de 0,470, pero
> ninguna regla con umbral previo lo alcanza: ni la meteorología pronosticada (viento máximo
> 10,2 mph, FFWI máximo 22), ni el combustible, ni la intensidad del modelo base, ni el crecimiento
> observado en P-24 (Y). Efecto esperado: en eventos de viento extremo con cruces de agua o de
> bosque en altura, el modelo subestima. Las Golondrinas lo cuantifica: con viento observado, las
> pavesas multiplican el área por 4,9; con el GFS, por 1,0. Se reabre con viento de estación en los
> incendios de calibración, o con una prueba independiente de la regla d1 registrada en Y §4.

**`MODELO-V0.md`**, en las limitaciones:

> - Sin pavesas. No se usan ni globales (X) ni condicionadas a una regla previa (Y): ninguna
>   variable disponible antes de pronosticar separa los incendios en que ayudan de los que desbordan.

**`ESTADO-RESEARCH.md`**, en el estado actual:

> - **Pavesas condicionadas (Y, 2026-10-23): no se usan.** Techo por incendio 0,470; ninguna regla
>   con umbral previo pasa de 0,439 sin alarmas. Un orden exploratorio por la intensidad del modelo
>   base coincide con el techo, con márgenes de menos de un punto, y queda registrado como hipótesis
>   para incendios nuevos. Reabre: viento observado o esa prueba independiente.

## Referencias

- Andrews, P. L. y Rothermel, R. C. (1982). *Charts for interpreting wildland fire behavior
  characteristics*. USDA FS GTR INT-131. Clase ≥ 1.000 Btu/ft/s, llama ≥ 11 ft, según la
  interpretación del Fireline Handbook reproducida por Stubbs (2005).
- Fosberg, M. A. (1978). Weather in wildland fire management: the fire weather index. Escala y
  fórmula del FFWI; umbral ≥ 50 según la página del SPC/NOAA (`spc.noaa.gov/exper/firecomp/INFO/fosbinfo.html`). †
- NWS: criterios de Bandera Roja por oficina (`weather.gov/bou/RFW_Definitions`; tablas de la GACC
  del sur de California). Varían entre 15 y 25 mph sostenidos, con HR ≤ 15-25 %. †
- Paritsis, J. et al. (2018). Pine plantations and invasion alter fuel structure and potential fire
  behavior in a Patagonian forest-steppe ecotone. *Forests* 9: 117. †
- Fuente de ELMFIRE 2025.0212: `elmfire_level_set.f90:769-866` (lanzamiento de pavesas), vía
  `docs/referencias/ELMFIRE-COMO-FUNCIONA.md` §4.

† Leídas sólo en el resumen o en una fuente secundaria.

## Apéndice: cómo se obtuvieron los números

Sin código nuevo en el repo. Cuatro scripts descartables, de sólo lectura:
- techo y conjuntos: `benchmark._filas` y la lógica de `benchmark.validar`, con la regla como receta
  compuesta;
- familias a, d y e: `ws`, `m1`, `wd`, `fbfm40`, `cc`, `cbd` y `cbh` de los insumos de cada ventana
  (recortados a la grilla del DEM: el clima viene rellenado a una grilla cuadrada), `rh_gfs` del
  paquete, y `time_of_arrival` y `flin` de las salidas;
- validación anidada del corte de d;
- P-24: `pronostico.json`, plazos de 12 y 24 h, referencia `cicatriz`.

## Nota (2026-10-31)

El usuario dio por cancelado el pedido de viento de estación al INTA y a Bosques de Chubut: las
series no llegaron. La primera condición de reapertura de §4 (viento observado en los incendios de
calibración) ya no se puede cumplir y deja de contar. La única que sigue en pie es la prueba
independiente de d1, con el corte de §4 (≥ 1,5 %). El decreto y §1–§4 no cambian. El texto de §5
se aplicó a `RIESGOS_Y_SUPOSICIONES.md` §3, `MODELO-V0.md` y `ESTADO-RESEARCH.md` §6, con la
condición de reapertura ajustada a esta nota.
