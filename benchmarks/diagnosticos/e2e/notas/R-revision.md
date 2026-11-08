# R. Revisión adversarial de `DIAGNOSTICO-PRECISION-E2E.md`

> 2026-10-18. Revisión sin editar el documento ni el repo y sin correr ELMFIRE. Las referencias
> `DIAG:n` son líneas de `docs/resultados/pronostico/precision.md`. Hice un único cálculo
> propio offline, la sensibilidad de F7 con la misma función de `elongacion.py`, en
> `/private/tmp/claude-501/-Users-ichevallier-Projects-university-tesis-igniteinsights/550f7315-60bc-43cc-824e-2a1c8674fa42/scratchpad/R_elong_variantes.py`.
> El resto son cuentas sobre los CSV y las notas.

## Errores (bloqueantes)

**E1. El frente 1(a), tal como está escrito, deja de penalizar toda la sobre-propagación fuera de
VIIRS.** DIAG:113 propone "puntuar sólo dentro de `vistas ∪ cicatriz`". Pero `cicatriz.tif` ya es
`positivo & vistas` (`scripts/benchmark.py:104-105`), así que `vistas ∪ cicatriz = vistas`. Lo que
queda es puntuar sólo dentro de discos de 375 m alrededor de las detecciones. Todo FP del modelo
lejos del fuego real deja de contar y la métrica se acerca al recall. Eso premia justo a las recetas
que sobre-propagan, que es el sesgo dominante (1,35–1,86× en 4/6, F1). Además, el criterio de
aceptación ("si no cambia el orden de la mejor receta", DIAG:117) se evaluaría con una métrica
sesgada a favor de esas recetas. La corrección de D §5 bug 1 debe limitarse a las **islas**, es
decir, las celdas no vistas y no cicatriz *dentro del relleno de la cicatriz final* (el mismo
relleno de D §4, columna "Islas"). Fuera de ese relleno, lo no quemado sigue siendo FP.

**E2. El criterio del frente 1(b) ya tiene resultado conocido.** "P-24 sigue en pie si con (b)
mejora a la cadena en ≥ 5 de 6 incendios a 12 h" (DIAG:118). Pero D §5 bug 2 (`paso7_p24_estricto.py`)
ya lo midió: +0,096 y 6 de 6. No es un criterio registrado antes de correr, sino una confirmación
de algo ya visto, y hay que decirlo así. Además, "quitar de la referencia de crecimiento" (DIAG:115)
es ambiguo. Si el anillo pasa a negativo, el modelo que lo quema recibe FP por quemar celdas que sí
ardieron. Tiene que ser **exclusión** (ni acierto ni error), como en `paso7`.

**E3. La evidencia central del titular no tiene procedencia versionada.** `datos/F7_elongacion.csv`
(elongación 1,40 contra 2,3 y ejes girados) no la genera `scripts/diagnostico_error.py`, que escribe
de F1 a F6. Tampoco la describe `F-error.md`. Sale de `scratchpad/elongacion.py`, que está fuera del
repo, sin test y sin nota de método. Es justo el número que sostiene "forma y dirección" en DIAG:10-14
y DIAG:33. Hay que pasarlo a `scripts/` con su test y describirlo en F antes de citarlo.

**E4. La aritmética del presupuesto no cierra y mezcla lo medido con un residuo.**
- 0,49 − (0,10 a 0,15) − 0 = **0,34 a 0,39**, no "0,30–0,35" (DIAG:42-44).
- La fila "forma y dirección" (DIAG:33) aparece como "magnitud medida", pero es lo que sobra al
  restar. Ahí entra todo lo que no se cuantificó: supresión, semilla, el déficit del día 1 que se
  arrastra y los combustibles.
- El "sesgo corregible de ≈ 0,07 de Dice medio" (DIAG:17-18, DIAG:96) es el techo de un modelo
  *perfecto de perímetro* (D §5 bug 1: 1 − techo, media 0,066). No es cuánto subiría el Dice de
  modelo-v0, que sólo quema una parte de las islas. La palabra correcta es "hasta".

**E5. El criterio del frente 3 no se puede evaluar como está escrito.** Pide que "el error del eje
(F7) baje en ≥ 2 de los 3 con eje girado" (DIAG:153). Los tres girados son Alerces 2023, Epuyén y
Alerces 2016 (F7). Alerces 2016 no tiene WRF, que cubre 2023–2026, así que quedan dos y el criterio
pasa a 2 de 2. Además, el eje de F7 está definido sobre la cadena libre al horizonte, mientras que el
frente 3 corre reinicios P-24 de 12 y 24 h. No hay un "eje" definido para ese objeto.

**Errores factuales menores** (corregir, no bloquean):
- "Eje girado 80–100° en 3/6" (DIAG:13, 33). Con el eje módulo 180°, las diferencias son 82°, 85° y
  **78°** (Alerces 2016: |164,7 − 63,1| = 101,6 → 78,4). Con t\* dan 80°, 89° y 77°. Lo correcto es
  "≈ 80°".
- "NNO–SSE (131–168°)" (DIAG:37). 131° es NO–SE.
- "Lo quemado predicho es más redondo" (DIAG:12) vale en 5/6. En Epuyén lo predicho está más
  alargado: 1,57 contra 1,52.
- "Los FN se concentran en el bosque" (DIAG:14, 34) es exposición, no tasa. TU es el 43 % de lo
  observado ((TP+FN) en F3: 8.662 de 20.114 ha) y el 49 % de los FN, con razón de tasa 1,15. F-error
  §3 ya lo advierte y el resumen lo pierde.
- CROWN_RATIO "+5–15 % de ROS" (DIAG:39). La propia tabla de E B1 implica una elasticidad del ROS
  al WAF de 0,5–0,8 (×1,41 de WAF da ×1,19–1,32 de ROS). Entonces ×1,04–1,12 de WAF da **+2 a +9 %**.

## Objeciones fuertes

**O1. "≈ 0 a velocidad" no está identificado. El titular no se sostiene así.**
- **Sólo 4 de 6, todos sobre-propagadores.** En Patriada y Cholila, que se quedan cortos, igualar el
  área no es posible. Si al extender el área se conservara la precisión (0,605 y 0,553, F1), el Dice
  subiría a 0,605 (+0,11) y a 0,553 (+0,04). La media de los seis da ≈ 0, pero el rango va de −0,07 a
  +0,11. Es heterogeneidad, no ausencia de efecto.
- **Truncar en el tiempo no es corregir la velocidad.** Cortar en t\* deja la forma que el modelo ya
  tenía, con el déficit del día 1 incluido, y sólo saca la sobre-propagación tardía. F2 muestra un
  error de velocidad que cambia de signo con el tiempo (+12 a +65 h tarde el día 1, temprano después
  de 48 h). F6 muestra uno que cambia por combustible: 0,49–0,63 en TU, TL y GR contra 0,76–0,88 en
  SH. Un error de velocidad que varía en el espacio y en el tiempo *es* un error de forma.
- **La cadena es libre y depende del camino.** Con sesgo de 0,00–0,22 a 24 h en 4/6 (DIA-1 §7.3),
  todo el crecimiento posterior arranca del lugar equivocado. Que P-24 gane +0,10–0,17 sólo con
  re-sembrar es evidencia directa de que el error temprano de velocidad es de primer orden en la
  forma final.
- **El Dice premia la sobre-propagación cuando la precisión marginal supera Dice/2.** En Alerces 2023,
  lo que el modelo quema entre t\* y H tiene precisión ≈ 0,35, que es mayor que 0,455/2. Que
  Dice@t\* < Dice@H dice eso y nada sobre la velocidad.

Hay que reformular. Igualar el área *con la forma del modelo* no mejora el Dice, pero una parte de
esa forma la produce el propio error de velocidad (día 1 y diferencias por combustible). El test
limpio es F1 por reinicio de P-24 (ver S1).

**O2. F7 está contaminada por el truncado y la exclusión. La rotación del eje no es robusta.** Mi
recálculo, con la misma función:
- **Semilla:** efecto nulo. Los valores son idénticos a dos decimales sin semilla.
- **Recorte de la predicción por la exclusión de la cicatriz no vista:** 0–7 % de lo predicho, pero
  **22 % en Cholila**, donde la elongación predicha pasa de 1,96 a **1,58** sin el recorte. Lo que
  el modelo quemó hacia donde el fuego real fue después queda fuera, y eso sesga el eje predicho
  *en contra* del observado.
- **Truncado de lo observado a `vistas`:** domina. Con la cicatriz final, la elongación y el eje
  observados son:

  | Incendio | Final | Truncada (F7) |
  |---|---|---|
  | Alerces 2023 | 1,62 / 102° | |
  | Epuyén | 1,27 / 4° | 1,52 / 168° |
  | Alerces 2024 | 4,78 / 135° | 2,53 |
  | Patriada | 1,32 / 4° | 2,07 / 131° |
  | Alerces 2016 | 2,29 / 163° | |
  | Cholila | 2,67 / 72° | |

  El agrupamiento en 131–168° "a lo largo de los valles" queda en **2/6**. En Patriada (23 % de
  cobertura) la forma "observada" es la de los discos VIIRS, no la de la cicatriz. Con sólo la
  componente conexa mayor, lo observado de Patriada sube de 2,07 a 2,79.
- **El eje es indefinido cuando la elongación es ≤ 1,2.** En Alerces 2024, con 1,12 predicho, el eje
  salta de 179,8° a 44,6° entre H y t\*.
- **Supresión:** el combate de flancos ("anclar y flanquear") alarga la cicatriz real hacia la
  cabeza, y ELMFIRE sin supresión no lo puede reproducir. Es parte de la diferencia 1,4 contra 2,3,
  no sólo L/W ni dirección del viento.

Lo que sobrevive es que lo predicho es más redondo en la mediana. Con la cicatriz final, la mediana
observada es 1,96 (no 2,3), 4/6. Lo que no sobrevive con n = 6 y sin intervalos es "girado ≈ 80° en
3/6, a lo largo de los valles".

**O3. El techo de 0,85–0,90 mide otro objeto y no se puede restar.**
- **Otro objeto.** MCD64A1 y el umbral se midieron contra la *cicatriz final* (D §4). Lo que se
  puntúa es el *crecimiento truncado a `vistas`*. Para ese objeto, la mayor incertidumbre es la
  convención del radio. D §3 da un área con 375 m de 1,09–1,89× la de 187,5 m, y el radio real de
  la huella es 240–300 m. Con referencias anidadas, Dice = 2/(1+R) = **0,69–0,96, media ≈ 0,84**
  (Cholila 0,69, Alerces 2016 0,72). Esta componente es más grande que las del umbral y MCD64A1, y
  falta en el presupuesto.
- **No es aditivo.** Con errores independientes, el Dice observado ≈ Dice(modelo, verdad) × techo,
  como heurística. Con 0,51 y 0,87 sale ≈ 0,59 contra la verdad, así que la referencia "cuesta"
  ≈ 0,08 a este nivel, no 1 − techo.
- **El umbral se movió en un solo sentido.** Se comparó 0,3 contra 0,44. Key y Benson ubican la
  severidad baja desde 0,1, y D mide 7–82 ha de dNBR 0,1–0,3 dentro del perímetro. MCD64A1 a 463 m
  perdona los bordes.

Corresponde presentar el techo como "orden de magnitud, 0,7–0,9 según la convención", no como una
fila restable.

**O4. La reinterpretación del ensamble GEFS, tal como está escrita, es una racionalización.**
- **No se midió la dispersión de entrada.** `ENSAMBLE-BACKTESTS-CONSOLIDADO` no informa la desviación
  estándar de la dirección ni de la velocidad del viento entre miembros. "Angosto porque comparten la
  escala sinóptica" es una hipótesis.
- **Hay una alternativa medida en el repo: el modelo es insensible al viento bajo dosel.**
  `AUDITORIA-FISICA` loop K (~l. 740-790): con el viento del eje del lago (`rotacion-060-001`) da
  0,271 contra 0,255, y concluye "ni con la dirección del valle el viento le gana a la pendiente"
  con WAF ≈ 0,08. Loop M: la dirección de WindNinja sola baja la media (0,411 contra 0,439) y hunde a
  Cholila (0,513 → 0,331). Una banda GEFS del 4–14 % es exactamente lo esperable si un ±20 % del
  viento a 20 pies, ×0,08 de WAF, casi no mueve φw.
- **Qué la falsaría.**
  - (a) La dispersión de entrada de GEFS en dirección es ≥ 20–30° y aun así la banda es angosta: la
    causa es la insensibilidad, no la escala sinóptica.
  - (b) Los rumbos observados de las corridas (F1, centroides por pasada) se alinean mejor con el
    viento GFS a 10 m que con el eje del valle sacado del DEM.
  - (c) Las estaciones (Esquel, Trevelin, El Bolsón) muestran dirección GFS correcta en los días de
    corrida.
  - (d) Un viento con la dirección del valle no cambia el Dice: ya pasó en loop K, y es una
    falsación parcial existente que el documento no menciona.

**O5. Al presupuesto le faltan componentes que ya están medidos.**
- **Mapa de combustible** (`ESTADO-RESEARCH.md:128-129`). Calibración: CCS-BAP 0,510, MapBiomas
  0,430, WorldCover 0,131. Prueba: 0,191, 0,284 y 0,272. Es la palanca medida más grande, sobre todo
  fuera de muestra, y no tiene fila.
- **Semilla P-24 inflada** (D §5 bug 4). Entre el 26 y el 61 % de la semilla cae fuera de la cicatriz
  final, y no aparece en el documento. Una semilla grande tiene un perímetro de arranque más largo y
  además achica el crecimiento observado del denominador. Las dos cosas inflan el "×4" de F5 que
  DIAG:35 atribuye a la supresión y que motiva el frente 5.
- **Orientación** (F3). La tasa de FN en SE y S es 0,68 y 0,61, contra 0,34–0,37 en N, NO y O
  (razón ≈ 1,9). Es la señal de estratificación más fuerte del diagnóstico y no aparece.
- **Dosel.** Con dosel de 80–100 %, la razón de FN es 0,95. TL, con el mismo WAF, tiene 0,89. El
  mecanismo "frente isótropo bajo dosel" (DIAG:45) no se ve en los FN. Apunta a TU (caña, ñire) como
  modelo de combustible, que es el terreno del crosswalk.

**O6. El frente 2 no es físicamente específico, tiene un techo matemático y un sesgo hacia "no".**
- **dNBR ≥ 0,66 no distingue copa de fuego de superficie letal.** Nothofagus de corteza fina
  (coihue, lenga, ñire) muere con fuego de superficie, y la caña consume todo el estrato. DIAG:139-140
  lo reconoce, pero un positivo igual habilita una variante de copa.
- **Tasa base y techo.** La fracción de la cicatriz entera con dNBR ≥ 0,66 ya es 0,44–0,56
  (`scratchpad/D/paso5.json`, relativa a ≥ 0,3: Epuyén 0,44, Alerces 2024 0,52, Alerces 2023 0,56,
  Alerces 2016 0,50), y en bosque será mayor. Así "≥ 0,5" es casi automático. Y "≥ 1,5× los días
  siguientes" es **imposible** si la fracción posterior pasa de 0,67.
- **CFIS predice copa también después en Patriada** (0,92–1,00, DIA-1 §7.4). El criterio exige los
  dos incendios, así que falla en Patriada aunque la copa haya sido el mecanismo del día 1. Mide la
  especificidad del día, no la copa. "Si no, el límite queda reforzado" convierte un resultado
  inconcluso en confirmación. Hacen falta tres salidas: sí, no e indiscriminado.
- **Confusores de medición.**
  - El dNBR absoluto depende del NBR previo: el bosque denso da más dNBR que el ñire o el SH4 a igual
    consumo. Conviene RdNBR o RBR.
  - Los umbrales de Key y Benson son para Landsat TM. Patriada y Alerces 2024 son Sentinel-2.
  - Los PRE/POST locales son medianas sin máscara de nubes (D §4, proxy). Patriada nunca se
    recomputó ("n. m."). Los datos existen en `mask-dataset-gen/dataset/puerto-patriada-2026/runs/baseline-002`,
    pero hay que confirmar que corresponden al run vigente.
  - La ventana PRE de 26 meses, deliberada para la máscara, mezcla hoja y sin hoja en el ñire y la
    lenga caducifolios. Para la máscara está bien; como severidad es un confusor.
- **Selección.**
  - La probabilidad de detección de VIIRS crece con la FRP, así que las celdas "del día 1" están
    enriquecidas en quema intensa por construcción.
  - Lo de los días siguientes tiene más borde y más píxeles mixtos, con menos dNBR. El cociente puede
    salir por geometría.
- **Fuga.** Patriada y Alerces 2024 se eligieron *por* tener residuo, y la variante habilitada se
  evaluaría en sus mismos primeros reinicios: es doble uso. La variante no está especificada, y DIA-1
  §7.6.2 ya llamó a los únicos caminos posibles (FMC por celda, "CBH equivalente") "valores sin
  sentido físico". Un positivo lleva a una perilla [K]. Además, "[E]" es discutible: no son datos
  nuevos, son las mismas escenas que definen la referencia.

**O7. El frente 3 es una perilla si no la precede evidencia.** Sería la quinta fuente o corrección de
viento, después de ERA5 ×1,3, el atlas, el diurno y las rotaciones. Para ser [E] hace falta primero
mostrar, *sin ELMFIRE*, que WRF acierta mejor que GFS la dirección en estaciones durante los días de
corrida. Además, WRF de 4 km tiene una resolución efectiva de ~6–7 Δx (25–30 km), contra valles de
2–5 km de ancho. Es poco probable que encauce mejor que WindNinja a 90 m, que ya falló. El umbral de
+0,02 con 4 incendios está dentro del ruido entre reinicios (IoU 0,05–0,32 en Epuyén) y 3 de 4 da
p = 0,31 en la prueba de signos. Y por O4, con WAF ≈ 0,08 ni la dirección correcta mueve el bosque.

**O8. El criterio del frente 4 es casi tautológico.**
- **La banda sale ≤ 3× por construcción.** El área escala con ROS², así que P90/P50 de área ≈
  exp(2 · 1,2816 · 0,4) = **2,79**.
- **La cobertura no discrimina.** Es trivial en los reinicios tardíos, que sobre-propagan en 25 de
  28, e imposible con el déficit del día 1. Hay que estratificarla.
- **σ de dirección.** WD ±15° no condice con el error medido de 20–100° (RIESGOS §3) ni con |Δθ|
  mediano de 34°.
- **Implementación.** El Monte Carlo de ELMFIRE usa deltas aditivos globales (C §6), así que el
  ln ADJ tiene que ir por miembro en la receta.

**O9. La evidencia del frente 6 mezcla canales.** La sensibilidad de ±25 % por punto es de m1
(muerto), y el frente propone LFMC (vivo, `MLW_FILENAME`). La evidencia que corresponde es la
sensibilidad a LW, que E da como "muy aguda" pero sin cifra en DIAG:188.

## Sugerencias

- **S1. Repetir F1 por reinicio de P-24** (34 reinicios, 0 corridas): Dice a área igualada, precisión y
  ángulo por ventana de 12/24 h. Separa velocidad de forma sin la dependencia del camino de la cadena
  libre, y es el producto operativo real.
- **S2.** Versionar F7 en `scripts/diagnostico_error.py` y agregar:
  - la cicatriz con radio 187,5 y 375 m;
  - la predicción sin recorte por exclusión;
  - la componente mayor;
  - un intervalo por bootstrap del eje;
  - el eje sólo cuando la elongación pase de ~1,3.
- **S3.** Cruzar TU × orientación y combustible × pendiente en F3 antes de atribuir los FN a la
  copa o al viento.
- **S4.** Probar con la FRP de VIIRS (columna de `firms.csv`, 0 corridas) como proxy de intensidad del
  día 1 frente a los días siguientes, en bosque frente a SH4, normalizada por ángulo de escaneo.
  Tiene resolución temporal, que el dNBR no tiene. Sumar Sentinel-2 o partes del día 1 si existen.
- **S5.** Antes del frente 3, comparar GFS y WRF contra estaciones en los días de corrida (dirección y
  rapidez a 10 m) y medir la dispersión de entrada de GEFS. Es barato y decide O4.
- **S6.** Agregar al presupuesto las filas "mapa de combustible" (medida), "convención de `vistas`"
  y "semilla P-24 inflada", y marcar "forma/dirección" como residuo.
- **S7.** Ráfagas: no figuran ni en los frentes ni en los descartados. Corresponde ponerlas como
  límite del día 1 en la cadena: P-24 lo esquiva, y DIA-1 §5.2 exige comparar con estaciones antes.
- **S8.** CROWN_RATIO: el argumento de coherencia es circular. El CBH de 1–1,5 m representa la escalera
  (caña) para Van Wagner, pero el CR de Albini y Baughman se refiere a la profundidad de copa del
  dosel arbóreo. Hay que declararlo como decisión, con el desacuerdo con E §3 (que lo ponía primero),
  y no como "verificado".
- **S9.** Reescribir la respuesta corta: "igualar el área con la forma del modelo no mejora el
  Dice; el error de velocidad es grande, cambia de signo con el tiempo y el combustible, y se
  convierte en error de forma en la cadena libre".

## Ranking alternativo propuesto

| # | Frente | Clase | Corridas | Por qué este lugar |
|---|---|---|---:|---|
| 1 | Frente 1 corregido: islas sólo dentro del relleno de la cicatriz final, anillo como exclusión, más la semilla P-24 inflada (D bug 4) y la sensibilidad al radio de `vistas` | [M] | 0 | Toca todos los números. Sin esto F5, el frente 5 y el techo están contaminados |
| 2 | S1 + S2: F1 por reinicio y F7 robusta | [M], diagnóstico | 0 | Decide si los frentes 3 y 4 apuntan a la dirección, a la velocidad o a la supresión |
| 3 | S5: GFS/WRF contra estaciones y dispersión de entrada de GEFS | [E] si WRF gana | 0 | Puerta del frente 3 y prueba de O4 |
| 4 | Frente 2 rediseñado: FRP primero, RdNBR segundo, controles negativos (Epuyén, Alerces 2016 y 2023), tres salidas y variante fijada ahora o salida limitada a "límite con evidencia" | [E] | 0 | Evidencia que pidió DIA-1 §7.6, sin abrir una perilla |
| 5 | Frente 3 (WRF en P-24), sólo si 3 da positivo, con el criterio de eje corregido | [E] → v1 | 23 | Alto costo y baja probabilidad mientras WAF ≈ 0,08 (loop K) |
| 6 | Frente 4 con criterio estratificado y σ de dirección coherente con lo medido | [P] | 460 | Producto, no reabre nada |
| 7 | Frente 6 (LFMC) | [E cond.] | 7 | Depende de datos que no hay |
| 8 | Frente 5 (sólo reducir) | [P], exploratoria | ~30 | Confundido con la semilla inflada (O5); sólo en incendios futuros |

## Lo que está bien

- La disciplina de alcance se cumple: sólo calibración, prueba no usada, ELMFIRE 2025.0212 sin
  tocar, modelo-v0 intacto, costos con un ELMFIRE por vez y la clasificación [M/B/E/P/K] explícita.
- Las cifras de F1, F2, F4, F5 y F6 citadas coinciden con los CSV. Lo verifiqué: Dice medio 0,5104,
  |Δθ| mediano 33,5°, elongaciones medianas 1,40 y 2,30, FSS +0,09 a +0,17, 25 de 28 y 1,39.
- La verificación de L/W (H) es sólida. Corregir las cifras invertidas FIRMS/oráculo y no tocarlas
  hasta decidir el anillo es lo correcto.
- La falsación offline del ADJ simétrico es honesta, con la regla "sólo reducir" marcada como post
  hoc (riesgo alto, DIAG:183).
- F2 condiciona a las celdas alcanzadas e informa aparte la fracción nunca alcanzada. F6 declara sus
  seis sesgos.
- La semilla no contamina F7 (mi recálculo: idéntico sin semilla).
- Registrar criterios antes de correr es la práctica correcta. Los defectos señalados (E1, E2, E5,
  O6) son de redacción y diseño, no de intención.
