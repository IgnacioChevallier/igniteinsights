# Decisiones de combustible y dosel de modelo-v0

> Estado: **adoptadas técnicamente e implementadas en v6** desde el 2026-10-03; promovidas con
> `modelo-v0` el 2026-10-04. Las asignaciones que quedaban abiertas en el crosswalk se cerraron
> el 2026-10-12 (`IGN-20B-FINAL-CROSSWALK-CCSBAP.md`, al final). El detalle reproducible está en `docs/resultados/AUDITORIA-FISICA.md`.

## Contexto: qué cambió

La auditoría encontró **cinco errores en la interfaz entre el sistema y ELMFIRE**. Los cinco
estaban en todas las simulaciones anteriores, incluidas las del documento del crosswalk
(`docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md`) y la calibración de `docs/historico/RESULTADOS-CSS-BAP.md`:

1. El clima quedaba fijo en la primera hora de cada ventana de 24 h: sin ciclo diurno.
2. El frente avanzaba a la mitad de la velocidad que el propio modelo calculaba.
3. La dirección del viento se interpolaba mal entre horas cuando soplaba del sur.
4. En las celdas con cobertura arbórea pero sin altura, el viento no actuaba.
5. En dominios más altos que anchos, la franja norte leía el clima de otra fila.

Los cinco están corregidos y verificados con el modelo real. Con la interfaz corregida:

- **La receta calibrada no necesita el factor de ajuste de velocidad (ADJ):** la única perilla
  que la región pide es la humedad del combustible vivo, en 100 % (antes: 100 % más un ADJ de
  1,15). El ADJ compensaba los errores.
- Sobre los siete incendios de calibración, el Dice medio es **0,381** (mediana 0,451), sin
  incendios con sesgo de área fuera de [0,5×; 2×], salvo el caso límite de Las Golondrinas. Antes
  de la auditoría, el modelo sin calibrar daba 0,312.
- El resultado es mucho menos sensible a errores en el punto y la hora de ignición.

Las decisiones que siguen son las que ahora más mueven el resultado y que no se pueden resolver
calibrando.

## Resolución (loop L, 2026-10-03)

Se tomaron como propias, buscando el mayor acierto sobre los siete incendios de calibración sin
alarmas de sesgo, con dos agentes de investigación para el CBH (decisión 2) y la antigüedad del
dosel y el rebrote (decisiones 3 y 4). Cada número sale de `scripts/benchmark.py` sobre los
protocolos v5 y sus copias byte a byte con mapas o capas agregadas (`-x1`, `-x2`, `-x3`); el
registro completo está en `docs/resultados/AUDITORIA-FISICA.md`, loop L.

**Receta resultante: `lw100-lit-altoremsh3-perd-gr2-001`** (protocolo `-x3`), sobre `lw-100-001`:

| Cambio | Decisión | Efecto en calibración (media / mediana) |
|---|---|---|
| CBH por tipo de bosque, de literatura; CBD 0,16 en pino | 2 y 5 | 0,381 / 0,451 → 0,414 / 0,495 |
| Estepa sobre 1.300 m → NB9 (vegetación altoandina) | crosswalk | +0,009 sola |
| Remanente de disturbio → SH3 y sin dosel donde Hansen ve pérdida previa | 3 y 4 | +0,017 juntas; Patriada 0,368 → 0,502 |
| El resto de la Estepa (GR3) → GR2 | crosswalk | saca la alarma de Alerces 2023 (2,01 → 1,86) |
| **Todo junto** | | **0,440 / 0,501, sin alarmas** (IoU 0,298, precisión 0,448, recall 0,505) |

| Incendio | `lw-100-001` | Receta nueva |
|---|---|---|
| Alerces 2023 (h54) | 0,496 / 1,83 | 0,528 / 1,86 |
| Epuyén 2025 | 0,500 / 1,75 | 0,501 / 1,41 |
| Alerces 2024 | 0,562 / 1,54 | 0,636 / 1,35 |
| Patriada 2026 | 0,368 / 0,90 | 0,496 / 0,70 |
| Las Golondrinas (límite) | 0,012 / 0,02 | 0,012 / 0,02 |
| Alerces 2016 | 0,451 / 1,33 | 0,389 / 1,69 |
| Cholila 2015 | 0,280 / 0,55 | 0,517 / 0,87 |

- **Validación cruzada** (dejando un incendio afuera, entre las 28 recetas completas del loop):
  la receta nueva gana en 5 de 7 pliegues; fuera de muestra, **0,424 / 0,501** (la vigente:
  0,381 / 0,451).
- **Lo que no sirvió:** sacar el dosel del matorral (decisión 1, las tres variantes), lenga
  achaparrada → SH3 (Cholila se cae a 0,213), las pavesas (suben Cholila pero hacen pasar a
  Alerces 2023 y Epuyén), LW 95 o 105 %, CBH de TU a 2,5 m, el combustible de la quema de 0–2
  años.
- **En la causa:** el crosswalk y el dosel ya están en `fuels_builder` y `canopy_builder` (y en la
  preparación de la app). Los protocolos `-v6` los traen como insumos, y `lw-100-001` sobre v6 da
  0,439 / 0,501 sin alarmas: reproduce la receta. `benchmarks/particion.json` apunta a v6.
- **Prueba** (cuatro incendios que no se usaron para elegir):

  | Incendio | `lw-100-001` v5 | `lw-100-001` v6 |
  |---|---|---|
  | El Turbio 2025 | 0,296 / 5,73 ⚠ | 0,122 / 1,08 |
  | Puerto Café 2025 | 0,144 / 0,29 ⚠ | 0,207 / 0,30 ⚠ |
  | Epuyén 2019 | 0,114 / 16,5 ⚠ | 0,128 / 14,6 ⚠ |
  | Alerces 2015 | 0,298 / 1,49 | 0,309 / 1,48 |
  | Media / mediana | 0,213 / 0,220 (3 alarmas) | 0,191 / 0,167 (2 alarmas) |

  Mejoran tres de cuatro y desaparece una alarma. La media baja sólo por El Turbio, que antes
  "acertaba" quemando 5,7× el área (ver la decisión 4).
- **Alternativa equivalente:** el resto de la Estepa → GR1 en vez de GR2 empata en calibración
  (0,439 / 0,507 contra 0,440 / 0,501) y rinde más en prueba (0,209 contra 0,193, porque frena a
  Epuyén 2019, un incendio de estepa: sesgo 14,6 → 9,2). Elegirla por eso sería usar la prueba para
  decidir; queda anotada. A favor tiene un argumento físico propio: la estepa de coirón es rala,
  más cerca de GR1 que de GR2.
  - **Revisado en el loop M: se queda GR2.** El argumento de la ralera no alcanza: los dos modelos
    rompen igual la regla de `mex` (15 %), y la altura del lecho favorece a GR2. La PT-37 da
    coirones de hasta 40 cm (A4) y estratos de 0,4–0,5 m (A5), contra 1 pie (~30 cm) de GR2 y 0,4
    pie (~12 cm) de GR1. Sin una carga medida de la estepa subandina, no hay motivo independiente
    de la prueba para un v7.
- **Costo:** Alerces 2016 baja 0,06. Es el único que empeora (sesgo 1,33 → 1,69).
  - El diagnóstico por clase del loop M corrige la causa: no es el coihue con caña (27 ha de falso
    positivo de 1.602). Es el ñire con la copa a 1,5 m (+122 ha) y el arbustal de la quema de 2008,
    que v6 deja sin dosel (+289 ha en SH4).
  - Ninguna palanca lo recupera sin sacárselo a Cholila o a Patriada (`docs/resultados/AUDITORIA-FISICA.md`, loop
    M).

## 1. Ñire bajo, lenga achaparrada y arbustal nativo: ¿con dosel o sin dosel?

**Situación.** El crosswalk asigna ñire bajo y lenga achaparrada a SH8, y el arbustal nativo a
SH4: modelos de **matorral abierto**, con el lecho de combustible expuesto al viento. Pero el
dosel (cobertura de Hansen, altura de ETH) les asigna, dentro de las cicatrices, cobertura de
bosque cerrado: mediana de 78 a 91 % y 13 a 18 m. ELMFIRE combina las dos cosas y les aplica la
reducción de viento de un bosque: al combustible le llega el **8 % del viento a 6 m** en lugar
del 46 % que le llegaría a un matorral abierto.

**Cuánto pesa.**
- En Alerces 2024, dos tercios del matorral quemado es ñire bajo, y el 90 % tiene cobertura
  de Hansen de 50 % o más. En Patriada, el 59 % del arbustal nativo quemado también.
- Probando el modelo sin dosel en los combustibles de pastizal y matorral (como hace LANDFIRE),
  el Dice sube en Patriada (+0,10) y Alerces 2024 (+0,06) y baja en Alerces 2016 (−0,12) y
  Alerces 2023 (−0,08). La media no cambia.

**Opciones.**
- **(a) Sin dosel.** Son combustible arbustivo expuesto al viento, como dice el modelo asignado.
  El dosel de Hansen/ETH sobre esas clases se ignora.
- **(b) Con dosel.** Son sotobosque bajo un dosel real. Entonces el modelo de superficie
  apropiado sería de la familia TU (bosque con sotobosque), no SH, y la asignación del
  crosswalk cambia.
- **(c) Depende de la clase:** por ejemplo, ñire bajo sin dosel y lenga achaparrada con dosel,
  según la estructura real.

Hoy el sistema hace (b) en el dosel y (a) en el combustible, que es incoherente.

**Decidido (loop L): se mantiene el dosel (b en el dosel, a en el combustible).** Las tres
variantes sin dosel, sobre la receta final y los siete de calibración (perilla `sin_dosel` /
`dosel_coherente`), empeoran o no ganan:

| Variante | Media / mediana | Alarmas | Lo que mueve |
|---|---|---|---|
| Con dosel (`lw-100-001`) | 0,381 / 0,451 | 0 | — |
| (a) Sin dosel en GR/GS/SH | 0,371 / 0,415 | 3 | Alerces 2023, 2024 y 2016 se pasan |
| (c) Sin dosel sólo en SH8 (ñire bajo, lenga achaparrada) | 0,375 / 0,437 | 2 | Alerces 2023 y 2024 se pasan |
| (c) Sin dosel sólo en SH4 (arbustal nativo) | 0,385 / 0,452 | 1 | Patriada +0,084; Alerces 2016 −0,118 (2,41) |

Con el viento de bosque (WAF ~0,08) esos matorrales propagan a la velocidad que piden los
incendios; con el de matorral abierto (~0,46) se pasan. La incoherencia queda declarada como una
corrección empírica del WAF, no de la estructura. Lo que sí cambió es la copa: sobre estas clases
no hay copa en la receta nueva (su CBD sigue siendo el derivado, pero el CBH de literatura no les
toca y su copa casi no se enciende; `lw100-cbh-lit-shsc-001`, sin copa en SH, da lo mismo:
0,413 / 0,493).

## 2. La altura de la base de copa

**Situación.** No hay datos de altura de base de copa (CBH) para la región. El sistema la deriva
de la altura y la cobertura del dosel: CBH = altura × (0,20 + 0,30 × cobertura), o sea 5 a 10 m
en los bosques de la zona. Con esas alturas, el fuego de copas prácticamente no se enciende:
menos del 2 % de las celdas con dosel alcanzan la intensidad crítica.

**Cuánto pesa.** Con la base de copa a un cuarto (2 a 3 m), la copa sí se enciende:
- Cholila pasa de 0,255 a **0,528**, y Alerces 2024 de 0,556 a 0,614.
- Alerces 2016 y 2023 se pasan de área, y Epuyén y Patriada no cambian.

Es, por lejos, el insumo que más mueve el resultado entre los que quedan.

**Qué haría falta.** Un valor con fundamento por tipo de bosque: un inventario forestal, la
relación de Cruz, Alexander y Wakimoto (2003) con datos de estructura, o valores de literatura
para lenga, coihue, ciprés y plantaciones de pino. No se calibra: la tesis no fundamenta el
dosel.

**Decidido (loop L): CBH por tipo de bosque, con valores de literatura** (perilla
`cbh_por_combustible`, sólo donde ya hay copa; `cbd_por_combustible` para el pino). Un agente
relevó la literatura; no hay inventario de CBH para el bosque nativo, así que los valores salen
de la estructura vertical descrita en la zona:

| Clase (FBFM40) | CBH | Fuente | Confiabilidad |
|---|---|---|---|
| Lenga (TL6) | 6 m | hueco de ~6 m sobre el sotobosque (Paritsis, Veblen y Holz 2015, J Veg Sci 26:89) | media-baja |
| Alerce, ciprés de las Guaitecas (TL5) | 4 m | sin dato; como coihue maduro | baja |
| Coihue, ciprés, mixtos (TU5) | 1,5 m | la caña colihue (2–7 m) es una escalera continua y seca (Kitzberger et al. 2016, NZ J Bot 54:247; Bianchi y Defossé 2015) | baja-media |
| Ñire (TU3) | 1,5 m | sin separación vertical entre sotobosque y copa (Tiribelli, Kitzberger y Morales 2018) | media |
| Maitén, radal, mirtáceas (TL2) | 1 m | matorral alto continuo (Mermoz, Kitzberger y Veblen 2005) | media |
| Pino sin podar (TL8) | 1,5 m y CBD 0,16 kg/m³ | medido en plantaciones de ponderosa del NO patagónico (Paritsis et al. 2018, Forests 9:117) | alta |

| Variante (sobre `lw-100-001`) | Media / mediana | Alarmas |
|---|---|---|
| CBH derivado (CH × (0,2 + 0,3 CC)) | 0,381 / 0,451 | 0 |
| CBH × 0,5 | 0,399 / 0,439 | 0 |
| CBH × 0,35 | 0,393 / 0,430 | 1 |
| CBH × 0,25 | 0,396 / 0,429 | 3 |
| **CBH de literatura** | **0,414 / 0,495** | 1 (Alerces 2023, 2,03; sale con GR3 → GR2) |
| De literatura con TU a 2,5 m | 0,410 / 0,491 (en la combinación) | 0, pero Cholila cae a 0,313 |
| De literatura con lenga a 8 m | idéntico a 6 m | — |

La copa se enciende donde la literatura dice que hay escalera (coihue y ciprés con caña, ñire,
pino) y no en la lenga alta. Cholila pasa de 0,280 a 0,508 y Alerces 2024 de 0,562 a 0,581; Alerces
2016 baja de 0,451 a 0,407. Es la decisión que más movió el resultado.

## 3. La antigüedad del dosel

La cobertura arbórea es la de Hansen para el año **2000**: 15 a 26 años antes de los incendios
del benchmark (2015–2026). Donde hubo fuegos o cambios en ese intervalo, el sistema ve un bosque
que ya no está.

**Ejemplo.** En El Turbio 2025, el 83 % de la cicatriz figura como bosque cerrado, donde CCS-BAP
2017 ve el rebrote de la cicatriz de 2015 ("Remanente de disturbio reciente").

**Opciones.** Descontar la pérdida posterior con la capa de pérdida anual de Hansen, o usar un
producto de cobertura más reciente. Cualquiera de las dos es un cambio de insumo que requiere
volver a preparar los datos.

**Decidido (loop L): sin dosel donde Hansen GFC v1.13 `lossyear` marca pérdida antes del año del
incendio** (`scripts/perdida_hansen.py`, vecino más cercano; perilla `dosel_sin_perdida_previa`;
nunca la pérdida del mismo año, que sería ver la propia cicatriz). Lo que midió el agente sobre
los datos:
- Hansen detecta los incendios de la zona: marca pérdida *en el año del fuego* en el 49–88 % de
  cada cicatriz (salvo los de diciembre-enero, que la v1.13 todavía no tiene).
- La pérdida previa pesa en dos casos: El Turbio 2025 (61 % de la cicatriz, casi toda del fuego de
  2015) y Patriada 2026 (10 %); en el resto, 0–3 %.
- **El dosel viejo no viene sólo de Hansen 2000:** ETH 2020 da 14,7 m de mediana dentro de la
  pérdida de 2015 (fustes muertos en pie), así que la regla "CC = 0 si CH < 2 m" nunca se activa en
  las cicatrices. Las alturas anuales de GLAD (GLCLU 2020) ven "árboles de 4 m" sobre el rebrote;
  tampoco sirven. Otros productos evaluados: `docs/resultados/AUDITORIA-FISICA.md`, loop L.

Sola, sube la media a 0,392 (Patriada 0,368 → 0,458), pero sacar el dosel multiplica el viento a
media llama ×5–6: tiene que ir con el combustible por edad (decisión 4). Junto con ella, +0,017
(Patriada 0,502). Alerces 2016 baja (0,451 → 0,427): la quema de Alerces 2015 (685 ha, un año
antes) queda sin dosel y con el combustible del bosque; asignarle combustible de quema reciente
(NB9 o GR1) casi no lo cambia (+0,004), así que no se adoptó.

## 4. Remanente de disturbio reciente → GS3

El crosswalk asigna el remanente de disturbio a GS3 (pastizal-arbustal), con la regeneración de
ñire post-fuego de la PT-37 como análogo. En El Turbio 2025 el incendio volvió a quemar ese
rebrote diez años después: ardió lento (latente, diez días hasta 2.000 ha, combatido), y el
modelo lo recorre como pastizal-arbustal, con cinco veces el área observada. La asignación
describe bien un disturbio de dos años, pero con un mapa de 2017 envejece.

**A decidir:** ¿con qué modelo pasa el remanente a la clase de su vegetación actual, y a partir
de cuántos años?

**Decidido (loop L): remanente de disturbio reciente → SH3** (matorral leñoso de carga moderada,
clima húmedo), en el crosswalk (variante `ccsbap-altoremsh3`, `scripts/variante_crosswalk.py`).
La literatura sobre rebrote (Tiribelli et al. 2018; Blackhall et al. 2017; Landesmann et al. 2021;
Raffaele et al. 2011) dice que GS3 describe bien los primeros 2–5 años y mal los 10: a esa edad es
matorral rebrotante continuo de 2–3 m (SH3 o SH8; SH9 donde domina la caña). Los mapas son de 2013 y
2017 y los incendios que los usan, de 2015–2026, así que el remanente de los mapas tiene 6–15 años.

| Variante (calibración, con `lw-100-001`) | Media / mediana | Patriada |
|---|---|---|
| GS3 (vigente) | 0,381 / 0,451 | 0,368 / 0,90 |
| GS2 | 0,386 / 0,451 | 0,400 / 0,62 |
| SH3 | 0,385 / 0,451 | 0,394 / 0,52 |
| SH3 + sin dosel en la pérdida previa (decisión 3) | 0,398 / 0,493 | **0,502 / 0,83** |
| SH8 + sin dosel en la pérdida previa | 0,397 / 0,493 | 0,496 / 1,05 |

SH3 y SH8 empatan en calibración (sólo Patriada tiene remanente). En El Turbio (prueba) el remanente
lento saca la sobre-propagación (sesgo 5,7 → ~1,1), pero el Dice baja (0,296 → 0,127–0,165): con
5,7× el área el modelo cubría la cicatriz; con el área correcta quema otro lugar. Ese incendio
ardió latente y combatido diez días: el límite es la supresión, no el combustible.

## 5. Plantaciones de pino → TL8

Las plantaciones ("Forest") se asignan a TL8, hojarasca de pino. En Epuyén 2025 la ignición cae
en una plantación, y el incendio real ardió en copa desde el principio: 1.120 ha en 6 h. Con TL8
y la base de copa derivada, el modelo queda contenido en la plantación el primer día.

**Cuánto pesa.** En la calibración anterior, modelar las plantaciones como TU5 subía el Dice de
Epuyén de 0,291 a 0,344. Con la interfaz corregida casi no cambia nada: 0,500 → 0,503, y a las
24 h quema 176 ha en vez de 172, contra 1.730 observadas. El efecto anterior venía de que el
frente, a media velocidad, quedaba atrapado más tiempo en la plantación.

**A decidir:** con el modelo de superficie solo no se reproduce el primer día. Lo que decide si
una plantación densa sin podar arde como en Epuyén es su base de copa (punto 2). La asignación
TL8 se puede mantener mientras se resuelve eso.

**Decidido (loop L): TL8 se mantiene, con la copa medida en pino** (CBH 1,5 m y CBD 0,16 kg/m³,
Paritsis et al. 2018: plantaciones de ponderosa sin podar del ecotono, que usaron TL8 como modelo
de superficie). Epuyén sube de 0,500 a 0,512, pero el primer día sigue sin salir (167 ha a las
24 h contra 1.730): con TL8 la intensidad superficial no llega a los ~270 kW/m que pide un CBH
de 1,5 m (Van Wagner con humedad foliar de 90 %). Para reproducirlo haría falta un CBH de 0,3–0,5
m (el de una invasión densa de contorta, no el de una plantación), las pavesas o las ráfagas de
valle; ninguna tiene sustento para esa plantación. Queda como límite (el día explosivo).

## 6. El sesgo declarado del arbustal (paso 4 del crosswalk)

El documento del crosswalk declara que SH8, SH4 y GS3 subestiman la propagación "5 a 11 veces"
frente a la quema experimental de la PT-37. Esa cifra salió con el frente a la mitad de
velocidad. Corregida:

| Modelo | Propagación con viento sostenido | Con ráfaga | Llama | Observado |
|---|---|---|---|---|
| SH8 (ñire bajo, lenga achaparrada) | 739 m/h | 1.785 m/h | 3,5–5,6 m | 4.800 m/h, 3–4 m |
| SH4 (arbustal nativo) | 888 m/h | 2.445 m/h | 2,2–3,7 m | |
| GS3 (estepa arbustiva, remanente) | 1.098 m/h | 2.896 m/h | 2,8–4,5 m | |

SH8 sigue por debajo, pero 2,7 a 6,5 veces. **SH4 y GS3, con ráfaga, llegan al 51–60 % de la
propagación observada con la llama medida.** La conclusión "ningún modelo de arbustal reproduce
propagación y llama a la vez" ya no vale tal cual: el sesgo existe, pero es la mitad de grande.

**Decidido (loop L): corregido en los documentos.** `docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md`
ya tenía los números nuevos en §6.2, §7 y §9; faltaba el paso 4 de §5.4 (la ficha del ñire bajo),
que todavía decía 437 / 900 m/h y "ningún modelo reproduce las dos variables". Ahora dice 739 /
1.785 m/h (2,7–6,5×) y que SH4 y GS3 con ráfaga llegan al 51–60 %. La asignación SH8 no cambia: se
probó la alternativa para la lenga achaparrada (SH3) y empeora (Cholila 0,280 → 0,213).

## 7. Dos decisiones de método para validar

**Humedad del combustible vivo en 100 %.** Bianchi y Defossé (2015) midieron 110–220 % en
temporada de fuego y ubican en 110 % el umbral por debajo del cual ocurren los grandes
incendios. El sistema usaba 110 % (el borde húmedo); la calibración elige 100 %, el valor más
seco que no hace sobre-propagar a ningún incendio (el intervalo aceptable es 97–110 %).
¿Es defendible 100 % para días de gran incendio?

**Horizonte de Alerces 2023 en 54 h.** La regla es puntuar hasta que el área detectada por
satélite deja de crecer. En Alerces 2023 eso pasa a las 54 h (1.055 ha a las 54 h, 1.056 a las
72 h), pero se puntuaba a las 72 h para usar ventanas de 24 h. Con el modelo a su velocidad real,
esas 18 h extra lo castigan por fuego que el combate detuvo. Se aplicó la regla tal cual (54 h),
y se reportan las dos cifras.

**Decidido (loop L): las dos se mantienen.**
- **LW 100 %** sigue siendo el óptimo también con la receta nueva: LW 95 % da 0,444 / 0,524 pero
  hace pasar a Alerces 2023 (2,03); LW 105 % baja a 0,431 / 0,485. El borde seco se corrió de
  ~97 a algo entre 95 y 100 %, porque la copa ahora acelera a los incendios con caña. Sigue siendo
  consistente con Bianchi y Defossé (2015): la caña colihue, el combustible vivo de los incendios
  que la copa reproduce, nunca supera 110 % en temporada.
- **54 h en Alerces 2023**: con la copa encendida, el modelo sobre-propaga ese incendio más que
  antes, y es el que fija el borde superior de todas las perillas (las alarmas de CBH × 0,35, de
  las pavesas y de LW 95 % son suyas). Cortar donde el área FIRMS deja de crecer es lo correcto;
  sin ese corte, ninguna receta con copa sería admisible.

## Límites que ninguna de estas decisiones resuelve

- **Supresión.** Los incendios combatidos cerca de poblados (El Turbio, Epuyén 2019)
  sobre-propagan 5 a 16 veces. ELMFIRE tiene un módulo de supresión que hoy no se usa.
- **El primer día explosivo.** En cuatro de los siete incendios de calibración el modelo va 8 a
  30 veces por debajo en las primeras 24 h. La copa (punto 2) explica una parte; faltan las
  pavesas y las ráfagas de valle, que el pronóstico de 25 km no resuelve.
- **La dirección del viento de superficie.** El frente real corre en promedio unos 40° más al
  sur que el empuje del viento del pronóstico, en valles que el pronóstico no resuelve.
