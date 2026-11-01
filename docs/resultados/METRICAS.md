# Métricas de evaluación

> Catálogo único de las métricas con que se evalúa IgniteInsights: qué mide cada una, cómo se
> calcula, qué aporta, qué no dice y su valor vigente. Corte: 2026-11-01. No define métricas
> nuevas: reúne las que están repartidas en `IGN-26-VALIDACION.md`, `DIA-1-PROPUESTA.md` §2.4,
> `MODELO-V0.md`, `P24-PRONOSTICO-GFS.md`, las notas Z y AB y
> `ENSAMBLE-BACKTESTS-CONSOLIDADO.md`. Si una cifra difiere de esas fuentes, mandan ellas y
> `ESTADO-RESEARCH.md`. La implementación es `app/validation/puntuacion.py` y
> `app/validation/pronostico.py`.

## 1. Cómo leer las métricas

Cada métrica compara una **máscara predicha** (celdas que ELMFIRE da por quemadas) con una
**máscara de referencia**, en la grilla de la corrida (30 m). Antes de comparar hay que fijar tres
cosas; casi todos los malentendidos con las cifras vienen de mezclarlas.

**Qué referencia.**

- **Cicatriz dNBR (Sentinel-2).** Es la referencia principal: es independiente del modelo y
  tiene resolución espacial. Pero es la cicatriz *final*, así que se **trunca al horizonte**: sólo
  cuenta la parte de la cicatriz a menos de un píxel VIIRS (375 m) de alguna detección hecha hasta
  ese momento. Lo que ardió después va a la exclusión: no cuenta ni como acierto ni como error.
- **FIRMS (VIIRS 375 m).** Detecciones puntuales con hora. Sirve para el *cuándo* (error de
  llegada) y como referencia secundaria. Como es puntual y con huecos (nubes, horarios de pasada),
  sólo el **recall** contra FIRMS es fiable; la precisión contra FIRMS no se interpreta.

**Qué se puntúa.**

- **Acumulado** (benchmark de cadena): todo lo quemado desde la ignición.
- **Crecimiento** (P-24): sólo lo nuevo después del reinicio. Se descuenta la semilla y además el
  *anillo* ya visto al reiniciar (las celdas a < 375 m de una detección previa fuera de la
  semilla), porque no es crecimiento a pronosticar. Sin ese descuento el ΔDice de P-24 a 12 h
  salía +0,168 en lugar de +0,096 (`DIAGNOSTICO-PRECISION-E2E.md` §4).

**Qué se excluye.** Las celdas sin observación válida (`excluido.tif`), la semilla, el anillo y lo
de la cicatriz todavía no visto. Las islas sin quemar dentro del perímetro que VIIRS no resolvió
siguen contando como negativos, así que **el Dice tiene un techo práctico de ~0,85**
(IGN-26 §Benchmark).

## 2. Métricas de superposición

Todas salen de `puntuacion.metricas` sobre la matriz de confusión:

- **TP**: predicho y quemado.
- **FP**: predicho y no quemado.
- **FN**: quemado y no predicho.

Se reportan también en hectáreas (`tp_ha`, `fp_ha`, `fn_ha`, `predicho_ha`, `observado_ha`).

### 2.1 Dice (F1) — métrica principal

`Dice = 2·TP / (2·TP + FP + FN)`

**Qué mide.** El solapamiento entre predicción y referencia, de 0 (nada en común) a 1 (idénticas).
Es la media armónica de precisión y recall: castiga por igual quemar donde no ardió y no quemar
donde sí ardió.

**Qué aporta.** Un solo número que sólo es alto si el modelo acierta **dónde** y **cuánto** a la
vez. Es la métrica con la que se eligen recetas, se comparan mapas de combustible y se promueve un
modelo.

**Qué no dice.** No distingue entre quedarse corto y pasarse: un Dice de 0,3 puede ser un modelo
que quema la mitad de lo debido o uno que quema el triple. Por eso nunca se reporta solo: va
siempre con el sesgo de área (§2.5). Tampoco separa forma de velocidad (§3.1).

**Valor vigente.**

| Evaluación | Dice |
|---|---|
| modelo-v0, calibración (7 incendios) | media 0,439, mediana 0,501 |
| modelo-v0, prueba (4 incendios) | media 0,191, mediana 0,167 |
| P-24 con pronóstico GFS real, calibración (mediana de 4 incendios) | 0,192 a 12 h, 0,262 a 24 h |
| P-24, prueba (mediana de 4 incendios) | 0,084 a 12 h, 0,145 a 24 h |

Detalle en §5 y §6.

### 2.2 IoU (Jaccard)

`IoU = TP / (TP + FP + FN)`

**Qué mide.** Lo mismo que el Dice en otra escala; las dos son funciones monótonas una de la
otra: `IoU = Dice / (2 − Dice)`. Un Dice de 0,5 es un IoU de 0,33.

**Qué aporta.** Es la métrica estándar en la literatura de segmentación y de comparación de
perímetros. Se reporta para poder comparar con trabajos externos y con el consolidado del
ensamble, que se escribió en IoU. No agrega información que el Dice no tenga.

**Valor vigente.** modelo-v0 en calibración: entre 0,242 (Alerces 2016) y 0,465 (Alerces 2024),
sin contar Las Golondrinas (0,006).

### 2.3 Recall (sensibilidad)

`Recall = TP / (TP + FN)`

**Qué mide.** Qué fracción de lo que ardió el modelo dio por quemado.

**Qué aporta.** Dice si el modelo **llega** a donde llegó el fuego. Para un usuario operativo es
la pregunta de seguridad: "¿lo que me mostró cubre lo que pasó?". Es la única métrica fiable contra
FIRMS.

**Qué no dice.** Se infla trivialmente quemando de más: un modelo que quema todo el dominio tiene
recall 1. En el harness original apareció un caso con recall 1 y área 458 veces la observada
(IGN-26 §6). Por eso no se usa sola para elegir nada.

**Valor vigente.** modelo-v0 en calibración: entre 0,42 (Patriada) y 0,75 (Alerces 2023 y 2024).

### 2.4 Precisión

`Precisión = TP / (TP + FP)`

**Qué mide.** Qué fracción de lo que el modelo dio por quemado ardió de verdad.

**Qué aporta.** La contracara del recall: mide las **falsas alarmas**. Un modelo con precisión
alta y recall bajo quema en el lugar correcto pero se queda corto (velocidad); uno con recall alto
y precisión baja se desborda (falta de supresión, sobrepropagación). Leer las dos juntas dice qué
tipo de error domina.

**Qué no dice.** Contra FIRMS no se interpreta, porque una celda sin detección puede haber ardido
igual (nubes, pasada perdida). Sólo vale contra la cicatriz, y por eso P-24 usa la cicatriz como
referencia principal.

**Valor vigente.** modelo-v0 en calibración: entre 0,31 (Alerces 2016) y 0,61 (Patriada).

### 2.5 Sesgo de área y alarma

`Sesgo = área predicha / área observada`, con **alarma** si queda fuera de **[0,5×, 2×]**.

**Qué mide.** Si el modelo quema de más (> 1) o de menos (< 1), sin importar dónde.

**Qué aporta.** Es la métrica que desambigua el Dice. Además, la alarma funciona como **puerta**:
una receta que mejora el Dice medio a costa de disparar alarmas no se promueve. El ensamble y el
P-24 también se leen con ella.

**Qué no dice.** Nada sobre la ubicación: El Turbio 2025 tiene sesgo 1,08 (área casi exacta) y
Dice 0,122, porque quema el área correcta en el lugar equivocado.

**Valor vigente.**

- modelo-v0 en calibración: sin alarmas, salvo el caso límite Las Golondrinas (0,02).
- modelo-v0 en prueba: dos alarmas, Epuyén 2019 (14,6×, sin supresión) y Puerto Café (0,30).
- El patrón general: a 24 h todos los casos de calibración salvo Cholila queman entre el 2 % y el
  77 % de lo observado; al final del horizonte, cuatro de siete queman de más (1,35–1,86).

## 3. Métricas de tiempo y forma

### 3.1 t\* y Dice a área igualada

**Qué es.** t\* es la hora en que el área predicha alcanza el área observada. El **Dice a área
igualada** es el Dice calculado en esa hora (`puntuacion.area_igualada`).

**Qué aporta.** Separa las dos causas de error que el Dice final mezcla:

- **Forma**: el Dice a área igualada mide si el modelo quema en la dirección correcta, con la
  velocidad neutralizada.
- **Velocidad**: t\* contra el horizonte real. Si t\* es menor que el horizonte, el modelo es más
  rápido que el incendio; si nunca lo alcanza, es más lento.

Es clave en incendios combatidos, donde un modelo sin supresión acelera, cubre la cicatriz y la
desborda.

**Valor vigente.**

- Alerces 2024: t\* = 97 h sobre 120 h.
- Alerces 2023: 40 h sobre 54 h.
- Epuyén 2019 (prueba): t\* = 37 h sobre 120 h. Su Dice final es 0,128, pero el Dice a área
  igualada es 0,346: la forma es razonable y el error es de velocidad (supresión).
- Patriada 2026 y Cholila 2015 nunca alcanzan el área observada: son lentos.

### 3.2 Error de llegada

`Error = hora de llegada predicha − hora de detección FIRMS`, sobre las celdas con detección
(`puntuacion.error_llegada`). Se reportan la mediana en horas y la fracción de detecciones
**nunca alcanzadas**.

**Qué aporta.** Es la única métrica del *cuándo*. Para un usuario es la pregunta "¿en cuántas
horas llega acá?".

**Cómo se lee.** La detección es una **cota superior** de la llegada real: el satélite pasa
después de que el fuego llegó. Por eso un error negativo moderado es lo esperable, y el signo
importa más que el valor absoluto.

### 3.3 Recall cercano (histórico)

El recall restringido a la referencia que queda a menos de 5 km de la semilla. Era el alcance
razonable de una ventana corta en el harness A. Se conserva para reproducir esas cifras (recall
0,342, cercano 0,467 con `legacy-ccsbap`), pero no forma parte del benchmark vigente.

## 4. Agregación y lectura estadística

- **La unidad es el incendio**, no la ventana ni el reinicio. Los reinicios de un mismo incendio
  están correlacionados: primero se promedia dentro del incendio y después se toma la mediana
  entre incendios, para que Alerces 2024 (8 reinicios) no pese más que Alerces 2023 (3).
- **Media y mediana** van juntas. La media la mueve un solo caso extremo; por ejemplo, Las
  Golondrinas baja la media de calibración de 0,510 a 0,439.
- **ΔDice** es la diferencia contra un comparador sobre la misma referencia. Se informa con
  **cuántos incendios mejoran** (prueba de signos). Con n = 4, ni 4 de 4 es significativo
  (p = 0,0625, una cola); con n = 6, sólo 6 de 6 da p < 0,05. Todo resultado con estos tamaños se
  presenta como **descriptivo**.
- **Partición** (`benchmarks/particion.json`): 7 incendios de **calibración**, que se usan para
  elegir la receta, y 4 de **prueba**, que se miran pero nunca se usan para ajustar.
  - La **validación cruzada** reelige la receta sin el incendio puntuado (dejando uno afuera).
  - La **robustez a la ignición** repite la calibración con 21 perturbaciones del punto de
    ignición.

## 5. Benchmark de cadena (modelo-v0)

**Qué es.** Una corrida larga desde el punto de ignición reportado, encadenando ventanas, sin
supresión, puntuada en el **acumulado** contra la cicatriz truncada al horizonte. El horizonte dura
mientras el área FIRMS siga creciendo, con un tope de 120 h, y se corta antes si el incendio se
funde con otro.

**Qué aporta.** Es el **benchmark de la física**. Prueba si ELMFIRE con estos insumos (mapa de
combustible, dosel, meteorología) reproduce el incendio entero sin ayuda de observaciones. Con él
se calibró la receta y se compararon los mapas de combustible, que son la contribución de la
tesis.

**Qué no dice.** No es lo que hace la app: la app re-siembra en cada pasada (§6). Además arranca
en la ignición reportada, así que carga el déficit de las 2–6 h previas a la primera pasada VIIRS,
que quedan fuera del alcance del producto.

**Valores vigentes** (`MODELO-V0.md`):

| Conjunto | n | Dice medio | Mediana | Alarmas |
|---|---:|---:|---:|---:|
| Calibración | 7 | 0,439 | 0,501 | 0 sin el caso límite |
| Validación cruzada | 7 | 0,416 | 0,496 | — |
| Prueba | 4 | 0,191 | 0,167 | 2 |
| Robustez de ignición | 21 | 0,461 | 0,497 | 2 |

**Sensibilidad al horizonte** (sin correr ELMFIRE, cortando las corridas congeladas):

| Corte | 24 h | 48 h | 72 h | 96 h | 120 h (vigente) |
|---|---:|---:|---:|---:|---:|
| Calibración, media / mediana | 0,222 / 0,214 | 0,291 / 0,310 | 0,409 / 0,454 | 0,431 / 0,496 | 0,439 / 0,501 |
| Prueba, media / mediana | 0,159 / 0,139 | 0,185 / 0,173 | 0,215 / 0,230 | 0,196 / 0,193 | 0,191 / 0,167 |

El Dice crece con el horizonte: el modelo es lento el primer día y no se detiene después.

## 6. P-24: pronóstico desde la última pasada

Es la **métrica propuesta para el producto** (`ESTADO-RESEARCH.md`, 2026-10-31), junto a la
cadena y sin reemplazarla. Diseño completo en `DIA-1-PROPUESTA.md` §2.4.

### 6.1 Qué es

En cada pasada VIIRS (detecciones separadas por menos de 2 h forman una pasada; su hora es la de
la última detección) se reinicia ELMFIRE desde lo observado hasta ese momento y se corre 24 h.
Es exactamente lo que hace el dashboard. Cada reinicio `T_k` produce dos plazos, τ = 12 h y
τ = 24 h.

- **Semilla** `S_k`: lo reconstruido de las detecciones hasta `T_k`, acumulado (monótono).
- **Predicción a τ**: `{TOA − T_k ≤ τ} \ S_k`, sólo el crecimiento.
- **Referencia principal**: `cicatriz ∩ vistas(≤ T_k + τ) \ S_k \ anillo`, la cicatriz ya vista
  por VIIRS al plazo. Lo predicho fuera de la cicatriz es falso positivo, así que acá la
  **precisión sí se interpreta**.
- **Referencia secundaria**: las detecciones FIRMS nuevas hasta el plazo; sólo el recall.
- **Receta**: `lw-100-obs-001`, que es modelo-v0 (`lw-100-001`) con semilla `observacion`. Es
  una receta de evaluación, no candidata.
- **Clima**: el último ciclo GFS ya publicado cuando la pasada se ve en FIRMS (pasada + 3 h de
  latencia de FIRMS − 4 h de publicación del GFS; `pronostico.ciclo_disponible`). Es lo que tenía
  quien miraba el panel, sin usar datos posteriores (hindcast).
- **Reinicios que cuentan**: k ≥ 1. El reinicio 0 arranca en la ignición y no es un pronóstico
  desde lo observado.

### 6.2 Métricas por reinicio y plazo

- **Dice del crecimiento**: la métrica principal.
- **Sesgo del crecimiento**, con la alarma [0,5×, 2×].
- **Recall y precisión** contra la cicatriz; recall contra FIRMS.
- **Error de llegada** contra FIRMS.
- **Skill frente a la persistencia**: `(D − D_pers) / (1 − D_pers)`. Es 0 si ELMFIRE iguala a la
  extrapolación ingenua y 1 si es perfecto. En los resultados se informa como ΔDice contra la
  persistencia.

### 6.3 Comparadores

Los dos se puntúan contra la misma referencia que P-24.

1. **La cadena de modelo-v0**: lo que la corrida larga desde la ignición daba por quemado a
   `T_k + τ`, menos `S_k`. Responde **cuánto aporta reiniciar** con lo observado.
2. **La persistencia**: `S_k` dilatada en todas direcciones con el crecimiento del radio
   equivalente entre `T_{k−1}` y `T_k`, escalado a τ (`pronostico.persistencia`). Responde si
   **ELMFIRE le gana a una regla ingenua** ("crece como venía creciendo"). Sin este comparador no
   se puede afirmar que el modelo aporta.

### 6.4 Resultado principal (fijado antes de correr)

La **mediana entre incendios del ΔDice a 24 h** (P-24 menos la cadena), con el signo por incendio.
El de 12 h se informa al lado.

### 6.5 Valores vigentes

**Calibración, pronóstico GFS real** (`P24-PRONOSTICO-GFS.md`, nota Z; 4 incendios, 23 reinicios).
Media por incendio del Dice del crecimiento:

| Incendio | Reinicios | 12 h: P-24 / cadena | 24 h: P-24 / cadena |
|---|---:|---|---|
| Alerces 2023 | 3 | 0,236 / 0,204 | 0,317 / 0,330 |
| Epuyén 2025 | 6 | 0,123 / 0,017 | 0,193 / 0,049 |
| Alerces 2024 | 8 | 0,340 / 0,152 | 0,442 / 0,253 |
| Patriada 2026 | 6 | 0,148 / 0,018 | 0,207 / 0,043 |
| **Mediana** | | **0,192** / 0,085 | **0,262** / 0,151 |

| Plazo | ΔDice contra la cadena | ΔDice contra la persistencia | Pronóstico real − hindcast |
|---|---|---|---|
| 12 h | +0,117, mejora en 4 de 4 | +0,088, 4 de 4 | −0,001 |
| 24 h | +0,153, mejora en 3 de 4 (no en Alerces 2023) | +0,143, 4 de 4 | −0,001 |

- Las tablas por incendio y la columna de persistencia salen de la nota Z (`pronostico-ciclo-v7`).
  Las medianas contra la cadena salen de `pronostico-gfs-v7`, la regla de ciclo del dashboard.
  Son dos mediciones independientes que coinciden con diferencias ≤ 0,005 por incendio.
- Usar el GFS que existía en el momento, en lugar de los análisis posteriores, no cambia el
  resultado: ningún incendio se mueve más de 0,003 a 12 h ni de 0,007 a 24 h.
- Las cifras con 6 incendios (`pronostico-v7`: +0,096 en 6 de 6 a 12 h, +0,131 en 5 de 6 a 24 h)
  son **hindcast**: análisis GFS posteriores al reinicio y ERA5 en Cholila y Alerces 2016.

**Prueba** (nota AB; 4 incendios, nunca usados para ajustar). El Turbio y Puerto Café usan
pronóstico GFS real; Epuyén 2019 y Alerces 2015, ERA5.

| Incendio | 12 h: P-24 / cadena / persistencia | 24 h: P-24 / cadena / persistencia | Sesgo 24 h (mediana) |
|---|---|---|---|
| El Turbio 2025 | 0,085 / 0,000 / 0,123 | 0,144 / 0,020 / 0,129 | 2,54 |
| Puerto Café 2025 | 0,084 / 0,000 / 0,041 | 0,226 / 0,000 / 0,111 | 1,87 |
| Epuyén 2019 | 0,073 / 0,036 / 0,068 | 0,112 / 0,081 / 0,142 | 19,4 |
| Alerces 2015 | 0,093 / 0,018 / 0,068 | 0,146 / 0,031 / 0,086 | 4,69 |
| **Mediana** | **0,084** / 0,009 | **0,145** / 0,026 | |

| Plazo | ΔDice contra la cadena | ΔDice contra la persistencia |
|---|---|---|
| 12 h | +0,079, 4 de 4 | +0,021, 3 de 4 (pierde El Turbio) |
| 24 h | +0,120, 4 de 4 | +0,038, 3 de 4 (pierde Epuyén 2019) |

### 6.6 Cómo leer P-24

- **Reiniciar ayuda siempre** frente a la cadena: 4 de 4 en prueba a ambos plazos.
- **ELMFIRE le gana poco a la persistencia fuera de calibración.** En prueba la ventaja es
  +0,02–0,04 y no está en los cuatro casos. Es el número que más limita lo que se puede prometer.
- **El nivel absoluto es bajo y cae en prueba** (0,262 → 0,145 a 24 h), con la misma brecha entre
  calibración y prueba que tenía la cadena.
- **El sesgo cambia de signo según el momento del incendio.**
  - **Primer reinicio (día 1)**: queda **por debajo** de lo observado, 2–4,5×. A 24 h el sesgo es
    0,44 en Patriada y 0,24 en Alerces 2024. Coincide con fuego de copa que el acople Van Wagner +
    Rothermel de ELMFIRE no enciende (`DIA-1-PROPUESTA.md` §7.3–7.6).
  - **Reinicios tardíos**: **sobrepropagan** decenas de veces, porque el modelo no tiene supresión
    (Epuyén 2019, sesgo mediano 19 a 24 h).
- **El Dice lo decide la forma, no el área**: en P-24 el crecimiento sale errado ×4, pero igualar
  el área no sube el Dice. El crecimiento predicho es casi isótropo y el rumbo está errado en
  ~60°. La explicación completa, declarada como límite, está en `RIESGOS_Y_SUPOSICIONES.md` §9.

## 7. Comparación de mapas de combustible

**Qué es.** El benchmark de cadena (§5), con modelo-v0 fijo y sólo el mapa de combustible
cambiado: CCS-BAP, MapBiomas y WorldCover. Se usan las mismas métricas (Dice, sesgo), más una
prueba de **no inferioridad** contra MapBiomas con margen de 0,130 de Dice.

**Qué aporta.** Es la evidencia de la contribución de la tesis: si el mapa regional mejora la
simulación.

**Valores vigentes** (`COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`). En los seis casos sin fuga
temporal:

| Mapa | Dice medio | Incendios donde CCS-BAP gana |
|---|---:|---|
| CCS-BAP | 0,415 | — |
| MapBiomas | 0,378 | 4 de 6, con un empate (p = 0,375) |
| WorldCover | 0,118 | 5 de 6 (p = 0,219) |

- **No inferioridad**: con 95 % de confianza, CCS-BAP no pierde contra MapBiomas más de 0,098 de
  Dice, dentro del margen de 0,130.
- **En prueba se invierte**: CCS-BAP 0,191, WorldCover 0,272, MapBiomas 0,284. Gran parte de esa
  inversión viene de El Turbio.

## 8. Acuerdo del ensamble GEFS

**Qué es.** 31 corridas de ELMFIRE con los insumos del P-24 congelados y sólo la meteorología
cambiada (miembros GEFS). Por celda, el **acuerdo** es la fracción de miembros válidos que la
queman dentro del horizonte (`app/ensemble/agreement.py`). Se publica en tres bandas fijas:
≥ 0,10, ≥ 0,50 y ≥ 0,80. **No es una probabilidad calibrada.**

**Métricas** (`ENSAMBLE-BACKTESTS-CONSOLIDADO.md`; 23 reinicios en 4 incendios). Cada banda se
compara contra **c00**, el miembro de control, con las mismas métricas de §2 sobre la referencia
de P-24:

- **ΔIoU, ΔDice, Δrecall, Δprecisión y Δsesgo** de cada banda contra c00. Responden si alguna
  banda pronostica **mejor** que una corrida sola.
- **Cobertura de cicatriz y de FIRMS** de la envolvente ≥ 0,10, sus **FP en ha** y el **área
  predicha**. Responden cuánto crecimiento real agrega la envolvente y a qué costo en falsas
  alarmas.
- **Observado fuera de ≥ 0,10 (ha)**: lo que ardió y ningún escenario anticipó.
- **Ancho de la banda**: `(área ≥ 0,10 − área ≥ 0,80) / área c00`. Mide cuánta sensibilidad
  meteorológica muestra la capa.

**Valores vigentes.**

- **No mejora predictivamente a c00.** A 24 h, la banda ≥ 0,80 mejora el IoU en 3 de 4 incendios,
  por ≤ 0,003, y empeora en Patriada. La banda ≥ 0,10 empeora el Dice en 3 de 4.
- **La banda es angosta**: ocupa entre el 4 y el 14 % del área de c00.
- **Deja crecimiento afuera**: en Patriada a 24 h quedan 685 ha observadas fuera de ≥ 0,10 (de
  1.475 ha). Por eso la leyenda dice que el fuego puede extenderse fuera de la zona.
- **Veredicto** (2026-10-17): se adopta **con limitaciones**, como comunicación de sensibilidad
  meteorológica. No se usa como mejora del pronóstico ni como envolvente de alcance.

## 9. Qué métrica responde cada pregunta

| Pregunta | Métrica | Dónde |
|---|---|---|
| ¿El modelo quema donde ardió? | Dice (con sesgo al lado) | §2.1, §2.5 |
| ¿Llega a todo lo que ardió? | Recall | §2.3 |
| ¿Cuántas falsas alarmas da? | Precisión, FP ha | §2.4 |
| ¿Quema de más o de menos? | Sesgo de área y su alarma | §2.5 |
| ¿El error es de forma o de velocidad? | t\* y Dice a área igualada | §3.1 |
| ¿Cuándo llega el fuego a un punto? | Error de llegada | §3.2 |
| ¿La física de ELMFIRE con estos insumos reproduce el incendio? | Benchmark de cadena | §5 |
| ¿Qué tan bueno es lo que ve el usuario del dashboard? | P-24 | §6 |
| ¿ELMFIRE aporta sobre una extrapolación ingenua? | P-24 contra persistencia | §6.3, §6.5 |
| ¿El mapa regional mejora la simulación? | Comparación de mapas | §7 |
| ¿Cuánto depende el pronóstico de la meteorología? | Acuerdo del ensamble | §8 |
