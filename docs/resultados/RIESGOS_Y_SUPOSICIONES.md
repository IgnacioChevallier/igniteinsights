# Riesgos y suposiciones de modelo-v0

> Corte: 2026-10-12; actualizado el 2026-11-01. Complementa `ESTADO-RESEARCH.md` §6. Cada punto dice qué supone el modelo,
> cómo afecta a los resultados, qué se midió y qué dato permitiría reducirlo. La evidencia
> completa está en `AUDITORIA-FISICA.md`.

Modelo-v0 se congeló con una **regla de parada**: sólo se reabre por un bug físico o por evidencia
externa nueva (datos que hoy no tenemos), no para mejorar un caso de prueba. Los puntos de este
documento se reportan como límites. Ninguno se corrige ajustando perillas con los mismos once
incendios.

## Resumen

| # | Riesgo | Efecto sobre el resultado | Estado |
|---|---|---|---|
| 1 | Sin supresión | Sobre-propaga los incendios combatidos: 5–16× en El Turbio y Epuyén 2019 | Probado y no adoptado |
| 2 | Día 1 explosivo | Desde la primera pasada VIIRS, donde arranca la app, el déficit desaparece en dos incendios y queda en 2–4,5× en otros dos. Las 2–6 h previas (6–21× desde la ignición en cuatro de seis) quedan fuera del alcance del producto | Residuo medido (P-24 y diagnóstico de copa), límite declarado; lo previo a la primera pasada, fuera del alcance |
| 3 | Viento de superficie y pavesas | Dirección del frente errada en 20–100°; en Alerces 2015 el fuego sube la montaña en vez de bordear el lago. Sin pavesas, subestima los eventos de viento extremo | Límite de datos; cerrado (sin viento de estación desde 2026-10-31) |
| 4 | Humedad sin gradiente de altura | La montaña arde tan seca como el valle | Medido; cerrado como límite |
| 5 | Lo ya quemado | La app usaba el mapa de 2017 para cualquier fecha; ahora reasigna las quemas posteriores por edad | Resuelto en la app (LYQ-3) |
| 6 | Ingesta histórica de FIRMS | La app no podía preparar incendios viejos | Resuelto en la app |
| 7 | Transferencia | Prueba con cuatro incendios: Dice 0,191 y dos alarmas. Con P-24, 0,084 / 0,145 a 12 / 24 h, la mitad que en calibración | Declarado |
| 9 | Acierto de P-24 | Dice del crecimiento bajo; en prueba apenas supera a la persistencia (+0,02–0,04). El error es de forma y rumbo (~60°), no de área | Límite declarado (2026-11-01) |

## 1. Supresión

**Suposición.** El fuego se propaga libre: no hay brigadas, medios aéreos, cortafuegos ni líneas
de contención.

**Por qué importa.** El benchmark compara contra la cicatriz real, que es el resultado del fuego
**y** del combate. Un incendio contenido a tiempo aparece en la simulación como sobre-propagación,
aunque la física de la propagación sea correcta. Es el riesgo que más pesa en la lectura de los
resultados:

- **El Turbio (2025) y Epuyén (2019)** sobre-propagan 5–16×. Ninguna perilla física los arregla
  sin romper la calibración.
- **Alerces 2023** se puntúa a 54 h, cuando el área FIRMS deja de crecer. Las 18 h siguientes
  medirían fuego que en la realidad ya estaba contenido; con 72 h el sesgo pasa de 1,55 a 2,72.
- Las métricas de **sesgo** (área simulada / área real) mezclan dos errores: velocidad del modelo y
  efecto del combate. No se pueden separar con los datos disponibles.

**Qué se midió (loop M).** Se implementó el grupo `&SUPPRESSION` de ELMFIRE con la plantilla del
proveedor (ataque ampliado), cubierto por una prueba física (7 de 7 chequeos).

| Receta | Dice medio / mediana (calibración) | Alarmas |
|---|---|---|
| Sin supresión (`lw-100-001`) | 0,439 / 0,501 | 0 |
| Contención 30 %/día | 0,411 / 0,471 | 0 |
| Contención 60 %/día | 0,368 / 0,410 | 1 |

- Sólo mejora Alerces 2024. En el resto saca área donde el fuego sí ardió.
- No contiene a los que más sobre-propagan: El Turbio cae de 0,122 a 0,052 / 0,029 y Epuyén 2019
  apenas baja el sesgo (14,6 → 13,8 / 12,1). La regla de ELMFIRE reduce la contención objetivo
  cuando el incendio crece más de 15.000 acres/día, justo en los casos que la necesitaban.
- Con la plantilla de 120 %/día la cadena de ventanas se corta: un fuego contenido antes del final
  de la ventana no deja ráster de salida.

**Qué mostró el protocolo P-24** (`DIA-1-PROPUESTA.md` §7.2). Al reiniciar el modelo desde el
perímetro observado, el error acumulado desaparece y queda a la vista lo que hace el combate:

- Pasado el primer día, el crecimiento predicho a 24 h supera al observado: 18–30× en Patriada
  desde las 37 h, 10–28× en Epuyén desde las 16 h y 18–26× en Alerces 2016 desde las 13 h.
- En esos reinicios tardíos, una extrapolación ingenua del crecimiento (persistencia) a veces le
  gana a ELMFIRE.

Es la medición más limpia de este riesgo que hay en el repo, pero sigue sin separar el combate de
otras causas de frenado.

**El sesgo depende de la fase del incendio.** Sesgo = área predicha / área observada:

| Fase | Sesgo |
|---|---|
| Primeras horas, desde la ignición (fuera del alcance de la app) | 6–21× **por debajo** en cuatro de seis incendios (§2) |
| Primer día, desde la primera pasada VIIRS | ≈1 en cuatro incendios; 0,3–0,5 en Patriada y Alerces 2024 (§2) |
| Después del primer día (reinicios de P-24 desde las 12–19 h) | Mediana **4×**. El 71 % de los 28 reinicios se pasa más de 2×; sólo el 7 % queda por debajo de 0,5× |
| Área de la cadena al horizonte (calibración) | Mediana ~1,4: Alerces 2023 1,86, Alerces 2016 1,69, Epuyén 1,41, Alerces 2024 1,35, Cholila 0,87, Patriada 0,70 |

El ~1,4 del horizonte sale de dos errores que se compensan: el modelo pierde el salto inicial y
después corre sin combate. Entre los casos de prueba, Epuyén 2019 se pasa 14,6× y Puerto Café
queda en 0,3×.

**Registros de combate encontrados** (prensa con partes del SPMF; no hay horarios de líneas):

- **Epuyén 2025:** desde el primer día operaron aviones hidrantes, un helicóptero con helibalde,
  brigadas provinciales, el SPLIF y bomberos voluntarios. El flanco izquierdo se informó contenido
  el 21 de enero (día 6) (Diario Jornada, 2025-01-21; ANBariloche, 2025-01-27). Es compatible con
  la sobre-propagación de 2× del primer reinicio y de 10–28× después, pero no la demuestra: no se
  sabe dónde ni cuándo se trabajó la primera noche.
- **Cholila 2015:** los primeros días el fuego avanzaba "de forma incontrolable" en el valle del
  río Tigre, y los aviones no podían operar por el humo (Página/12, 2015-02-24). Su
  sobre-propagación de 2,7× en el primer reinicio **no es supresión**. Es más probable la semilla
  de un solo píxel sobre áreas chicas: 585 ha predichas contra 220 observadas.

Hay un segundo factor que infla el sesgo tardío. La referencia es la cicatriz que VIIRS ya vio, y
VIIRS puede no ver el crecimiento lento, tapado por humo o entre nubes: ese crecimiento queda
excluido de la referencia.

**Consecuencia para la interpretación.** Las salidas de modelo-v0 son **el peor caso sin
combate**: dónde puede llegar el fuego si no se lo frena. Usarlas como pronóstico de la cicatriz
final de un incendio combatido sobreestima el área.

**Qué permitiría reducirlo.** Registros de combate por incendio (líneas construidas, horarios y
zonas de descarga aérea, partes del SNMF o del SPLIF) para (a) excluir de la puntuación los
sectores contenidos o (b) imponer barreras en los insumos. Sin esos registros, la única
alternativa es restringir la validación a ventanas de crecimiento libre.

## 2. Día 1 explosivo

**Alcance (decisión del usuario, 2026-10-31).** La app arranca en la primera detección VIIRS. Las
2–6 h anteriores a la primera pasada quedan **fuera del alcance del producto**: sólo aparecen porque
el benchmark de cadena arranca en el punto de ignición reportado. El límite del día 1 dentro del
alcance es el residuo de P-24 después de la primera pasada: 2–4,5× por debajo en Patriada y
Alerces 2024, compatible con copa (`DIA-1-PROPUESTA.md` §7.3–7.6).

**Suposición.** El viento es horario y uniforme dentro de cada celda del modelo meteorológico; la
propagación es superficial, sin pavesas, y la copa casi nunca se enciende con el CBH derivado.

**Efecto desde la ignición.** Con modelo-v0, el área de las primeras 24 h queda muy por debajo
de la observada en cuatro de los seis incendios de calibración (Las Golondrinas es el caso
límite):

| Incendio | Déficit a 24 h |
|---|---:|
| Epuyén 2025 | 21× |
| Alerces 2016 | 8× |
| Alerces 2024 | 6× |
| Patriada 2026 | 6× |
| Alerces 2023 | ninguno |
| Cholila 2015 | ninguno (se pasa) |

La cifra de 8–30× que circulaba antes salió de los protocolos v4. La calibración compensa ese
retraso más adelante: el modelo llega a un área parecida, pero tarde. A horizontes más cortos,
todos sub-propagan más (loop 9).

**Dónde está el déficit** (protocolo P-24, `DIA-1-PROPUESTA.md` §7.3). Se reinició el modelo
desde el perímetro observado en la primera pasada VIIRS, entre 0,1 y 5,8 h después de la
ignición. Sesgo = crecimiento predicho / observado a 24 h:

| Incendio | Primera pasada | Sesgo desde la ignición | Sesgo desde la primera pasada |
|---|---:|---:|---:|
| Alerces 2016 | 1,8 h | 0,03 | 1,16 |
| Epuyén 2025 | 4,5 h | 0,00 | 2,06 |
| Patriada 2026 | 2,3 h | 0,22 | 0,47 |
| Alerces 2024 | 5,8 h | 0,09 | 0,28 |

- **En Epuyén y Alerces 2016 el salto ocurre antes de la primera detección.** Desde ahí, el
  modelo crece lo observado o más. No hay un déficit de velocidad: hay 2–5 h sin observar.
  Cuánto ardió en esas horas, contando la cicatriz dNBR a menos de medio píxel o de un píxel
  VIIRS de las detecciones de la primera pasada:

  | Incendio | Primera pasada | Observado | Modelo-v0 a esa hora |
  |---|---:|---:|---:|
  | Epuyén 2025 | 4,5 h | 640–1.120 ha | 9 ha |
  | Alerces 2016 | 1,8 h | 230–410 ha | 2 ha |

  Las crónicas dicen 1.120 ha en 6 h en Epuyén. La reconstrucción FIRMS de la app da más (1.964 y
  482 ha), porque dibuja cada píxel aislado como 44 ha y en Epuyén suma dos satélites que pasaron
  con 23 min de diferencia. En Alerces 2016 pesa además la hora de la ignición ("cerca de las
  14 h", con dos focos).
- **En Patriada y Alerces 2024 queda un déficit de 2–4,5×, pero sólo en el primer reinicio.**
  Desde el segundo (13–19 h), los dos ya crecen lo observado o más.
- Reiniciar desde la cicatriz real en vez de desde la reconstrucción FIRMS da casi lo mismo: la
  reconstrucción no es la causa.

**Por qué en el primer reinicio** (`DIA-1-PROPUESTA.md` §7.4). ELMFIRE enciende la copa con Van
Wagner sobre la intensidad superficial de Rothermel, con el viento ya reducido bajo el dosel
(WAF 0,07–0,09). Así no enciende copa en ñire, pino ni matorral alto aunque el CBH sea de
1–1,5 m. Sobre el bosque quemado el día 1:

- Van Wagner da copa en el 0,5–30 %.
- El modelo de iniciación CFIS (Cruz et al. 2004), que usa el viento a 10 m sin reducir, da
  68–100 %. En Alerces 2023, 2024 y Cholila, CFIS además señala justo el día del salto.

Es el sesgo de acople que Cruz y Alexander (2010) documentaron en Norteamérica. Es una
explicación con evidencia externa, no un parámetro para ajustar.

**¿Y el viento?** Viento medio a 10 m durante el primer reinicio, el del modelo contra el de las
estaciones de Meteostat:

| Incendio | Modelo (GFS) | Estación más cercana | Otra estación |
|---|---:|---:|---:|
| Patriada 2026 | 13,7 km/h | El Bolsón: 9,1 km/h | Esquel: 22,1 km/h |
| Alerces 2024 | 11,6 km/h | Esquel: 11,5 km/h | Futaleufú: 21,0 km/h (pico 62) |
| Alerces 2016 (sin déficit) | 9,0 km/h | Esquel: 27,1 km/h | — |

No hay una señal clara.

- En Patriada la estación más cercana tiene menos viento que el modelo.
- Alerces 2016 acierta el crecimiento con un viento modelado tres veces menor que el de Esquel.
- Bajo dosel, más viento casi no llega al combustible (loop 6).

El viento no se descarta: no hay ninguna estación a menos de 10 km de estos incendios, el caché
de Meteostat no trae ráfagas y la iniciación de copa depende justamente del viento en campo
abierto. Pero no es la explicación principal que muestran estos datos.

**Qué se midió antes.**

- Viento de estación en lugar del GFS (Las Golondrinas y Epuyén): el día 1 tampoco aparece.
- CBH bajo (loop F): la copa se enciende, pero acelera todo el incendio, no el salto inicial.
- Pavesas con la plantilla de hindcast: no adoptadas.
- Descartado sin correr nada (`DIA-1-PROPUESTA.md` §1.3 y §5.3): el límite de viento de
  Rothermel no muerde en estos combustibles, y las fluctuaciones de viento de ELMFIRE aportan
  +1–3 % a la velocidad.

**Consecuencia para el uso.** Hay que pronosticar desde la última pasada VIIRS, no desde la
ignición. Con el protocolo P-24 y el pronóstico GFS que se tenía en cada reinicio (último ciclo
publicado; `diagnostico-e2e/notas/Z-p24-pronostico-gfs.md`), el Dice del crecimiento mejora frente
a la cadena de modelo-v0 en los cuatro incendios GFS:

- a 12 h, +0,118 de mediana, en 4 de 4;
- a 24 h, +0,154, en 3 de 4 (no mejora Alerces 2023, que después frenó el combate);
- en los dos plazos, ELMFIRE le gana a la extrapolación ingenua en los 4.

El error de pronóstico del GFS a 5–33 h cuesta −0,001 de mediana frente a los análisis. Las cifras
anteriores (+0,096 en 6 de 6 y +0,131 en 5 de 6) son hindcast: análisis GFS posteriores al reinicio
y ERA5 en Cholila y Alerces 2016. El error del GFS contra el viento real del valle (§3) está en las
dos.

Las primeras 2–6 h, antes de la primera detección, no son pronosticables con ELMFIRE 2025.0212
configurado como modelo-v0, y quedan fuera del alcance del producto, que arranca en esa detección.
Lo que queda como límite es el residuo del primer reinicio en Patriada y Alerces 2024 (sesgo 0,44 y
0,24 a 24 h con el pronóstico real; Z §4).

**Qué permitiría reducirlo.**

- Un modelo de iniciación de copa con viento abierto. ELMFIRE 2025.0212 no lo tiene, y la versión
  está fija.
- Un registro de igniciones secundarias de incendios ajenos al benchmark, para fijar las pavesas.
- Ráfagas medidas en el lugar.

Ninguno de estos datos existe hoy.

## 3. Viento de superficie

**Suposición.** El viento de GFS (0,25°) o ERA5 (0,25°) representa el viento en el valle. Una
celda de ~25 km cubre todo un valle; no resuelve encauzamientos, brisas de lago ni flujos
nocturnos de ladera.

**Efecto.** El frente real corre 20–100° más al sur que el empuje del modelo. Los productos de
reanálisis dan 0,40–0,87× la velocidad de las estaciones. El caso extremo es **Alerces 2015**
(loop K): con viento del ESE a 3–5 mph, frenado al ~8 % bajo el bosque, la pendiente domina y el
modelo sube al Cordón Situación; el fuego real corrió ~6 km al norte de noche, bordeando el lago.
Para reproducirlo haría falta un viento local del sur de al menos 17 mph, que no está en ningún
dato disponible. **Las Golondrinas** es la misma familia de error: la ráfaga nocturna del norte no
está en el GFS.

**Qué se midió.** WindNinja (atlas y flujos diurnos), rotación empírica y viento de la estación El
Bolsón. Ninguno cambia la dirección dominante. Con la estación de El Bolsón, la ráfaga de Las
Golondrinas entra (29 mph), pero dura una hora y el resto de la tarde el viento es flojo: el Dice
pasa de 0,029 a 0,020. **Salvedad (2026-10-18):** en esa ventana sólo 27 de las 145 horas de
Meteostat son SYNOP reales; el resto es relleno, así que "el resto de la tarde flojo" no está
observado. La ráfaga (53,6 km/h a 10 m, 10-03 00Z) sí es real. La prueba no mide el viento de la
estación y no se re-corre.

**SYNOP crudo de El Bolsón contra el GFS del paquete (2026-10-19).** El 9-mar no hay ningún
reporte: todas las horas son `NIL`. La "tarde seca de 28 °C y 19–22 % de HR" de
RESULTADOS-CSS-BAP §2.12 es relleno de Meteostat. Hay dos reportes reales:

| 10-mar | Viento a 10 m | T | HR | Otros | GFS en el foco a esa hora |
|---|---|---:|---:|---|---|
| 00Z (21 ART) | **N, 29 kt** (29 mph a 20 ft) | **23,9 °C** | **27 %** | Tmax de la tarde 32,0 °C | ONO, 6,7 mph; 12,5 °C; 61 %; m1 11,6 % |
| 12Z (09 ART) | Calma | 15,3 °C | 97 % | 8/8 nubes; **12 mm en las 12 h previas** | ONO, 4,4 mph; 11,1 °C; 92 %; m1 22,2 % |

A la hora de la explosión, el GFS tiene el viento 4,3× más débil y el aire 11 °C más frío y
34 puntos más húmedo. Hace entrar el aire frío y húmedo del frente al anochecer, sin el viento
prefrontal del norte que lo precedió. Por eso m1 pasa de 4,5 % a 11,6 % a las 21 ART y a 25 %
de madrugada, y el modelo deja de propagar con la tarde. La lluvia de la noche es lo que frenó el
incendio real: encaja con que VIIRS no viera nada después y con el horizonte de 24 h. La
dirección no es el error que decide: el empuje del GFS (hacia ~110–125°) coincide con el eje de
la cicatriz desde los focos (107–123°). Con un único reporte no se sabe cuánto duró el viento
del norte.

**Corrida con lo observado (2026-10-19, nota G).** 29 mph y T/HR de las 00Z, uniformes y
sostenidos desde la ignición hasta 06Z. El modelo quema 2.404 ha en lugar de 224 (Dice 0,24,
sesgo 0,23, precisión 0,66) y el frente llega a 8,7 de ~26 km. Ni el viento ni la humedad
alcanzan solos. Por el criterio registrado no hay veredicto fuerte: la entrada meteorológica
explica una parte, no el orden de magnitud, y el resto queda para pavesas, WAF bajo dosel o
estructuras (`diagnostico-e2e/notas/G-golondrinas-meteo-observada.md`).
Una enmienda (§6) descarta la duración: sostenido hasta 12Z (18 h, contra la lluvia observada) el
frente queda frenado entre 8,6 y 8,8 km de la hora 9 a la 15 y termina en 12,6 km con sesgo 0,44. El
freno es de lugar: TL6 bajo dosel y una franja de agua que el incendio real cruzó, y que ELMFIRE sin
pavesas sólo rodea.
Una segunda enmienda (§7, 2026-10-23) cierra el caso. No hay bug de dosel: el arranque lento es SH4 y
TL8 bajo dosel, según la decisión del loop L. Los focos de origen en la caja son dos, como dice la
pericia. FIRMS muestra el frente a 22,6-27,5 km a las 10-11 h, al menos 2,2 km/h. Con lo observado
hasta 03Z más pavesas fuertes (10 % / 1 %, la variante del loop L, fijada antes de correr), el modelo
llega a 24,6 km a la hora 9 y quema 9.088 ha (Dice 0,545, sesgo 0,82, precisión 0,60). Sin dosel no
alcanza (sesgo 0,22). **Los dos mecanismos son necesarios a la vez:** con el GFS, las mismas pavesas
no cambian nada (sesgo 0,021 → 0,022), el SYNOP solo da ×8 y los dos juntos ×40
(`diagnostico-e2e/notas/X-pavesas-calibracion.md`). Las pavesas no entran en modelo-v0: sobre los 7
casos de calibración v6 dan media 0,451 con 3 alarmas nuevas (Alerces 2023, Epuyén, Alerces 2016) y
no pasan la puerta. Las 605 viviendas siguen sin modelo.
**Referencia y forma (G §8–§9, 2026-10-23).** La cicatriz es válida. No está sobredimensionada: es
~2.300 ha más chica que el perímetro del SNMF (12.959 ha), por la estepa que `pre_nbr_min` no ve. No
mezcla otro incendio: el lóbulo sureste está dentro del polígono oficial y MODIS lo fecha el 10-mar,
como al cuerpo principal. Y ardió en la primera noche. Sin pavesas, darle 72 h al modelo no recupera
el incendio: en `t*` = 27 h el Dice es 0,40, y no hay nada de la cicatriz más allá de 15 km.

**Pavesas: mecanismo faltante declarado.** modelo-v0 corre sin `&SPOTTING`. Como escalar global
(`lw-100-pavx10-001`, 10 % de las celdas en copa y 1 % en superficie), las pavesas no pasan la
puerta: media 0,451, tres alarmas (X). Encenderlas por incendio tendría un techo de 0,470, pero
ninguna regla con umbral previo lo alcanza: ni la meteorología pronosticada (viento máximo
10,2 mph, FFWI máximo 22), ni el combustible, ni la intensidad del modelo base, ni el crecimiento
observado en P-24 (`diagnostico-e2e/notas/Y-pavesas-condicionadas.md`). Efecto esperado: en
eventos de viento extremo con cruces de agua o de bosque en altura, el modelo subestima. Las
Golondrinas lo cuantifica: con viento observado, las pavesas multiplican el área por 4,9; con el
GFS, por 1,0. Se reabre sólo con una prueba independiente de la regla d1 registrada en Y §4, sobre
incendios que no sean los 7 de calibración. La otra condición, viento de estación en los incendios
de calibración, se cerró el 2026-10-31: las series del INTA y de Bosques de Chubut no llegaron.

**Puerta SMN WRF (frente 4, 2026-10-18).** Se comparó GFS y SMN WRF 4 km contra SYNOP crudo en las
horas de corrida P-24 de los 4 incendios 2023–2026. WRF no pasa: empeora la dirección en Esquel
(26,8° → 30,7°) y Futaleufú (19,1° → 39,1°), y sólo mejora en El Bolsón (81° → 12°, n = 21, horas
diurnas). Eso último es la mejor pista de que la escala de valle importa en Epuyén y Patriada, y
refuerza el pedido de las estaciones de la tabla siguiente (`diagnostico-e2e/notas/W-viento-estaciones.md`).

**Estaciones disponibles.** El benchmark ya usa, vía Meteostat, El Bolsón (87800), Esquel
(87803, 40 km al E de Los Alerces) y Futaleufú, Chile (85832). Fuentes adicionales identificadas
(2026-10-11):

| Fuente | Estaciones relevantes | Acceso | Prioridad |
|---|---|---|---|
| INTA SIPAS, red de la Dirección de Bosques de Chubut | Las Golondrinas, Epuyén, Corcovado, Río Pico; Trevelin (Central de Incendios); Lago Puelo (Campo Forestal); El Hoyo; El Maitén | Boletines por estación en `sipas.inta.gob.ar` (IDs 64, 63, 62, 65, 67, 68, 5, 6). Consultado el 2026-10-19: lo público son **boletines diarios** (viento medio, dirección dominante y ráfaga máxima en km/h); la exportación a Excel da error 500 y no hay serie horaria. Las Golondrinas y Epuyén (dir. bosques) terminan en 2016-10 y 2017. Trevelin C. Incendios no tiene boletines. Río Percey, Futaleufú, Huemul y Bustillo no registran dirección. **Alerces 2015** (20–26 mar): todas las estaciones casi en calma (Trevelin Agroforestal 0,2–2 km/h, NNE, ráfagas ≤ 26 km/h; Corcovado SE con ráfaga de 32 km/h el 24): ninguna muestra el viento del sur de ≥ 27 km/h (17 mph) que haría falta, aunque un flujo de lago dentro del parque no se vería desde ahí. **Las Golondrinas 2021**: sólo El Maitén y Cushamen (estepa, al E), con NW–NNW y ráfagas de 40–58 km/h el 9 y 10 de marzo; corrobora un evento ventoso regional, pero no la hora ni el valle | **Alta** si el INTA (EEA Esquel) entrega la serie horaria de Trevelin Agroforestal (22–24 mar 2015) y de El Maitén (9–10 mar 2021); lo público no alcanza |
| INTA SIGA (EEA, red propia) | Trevelin – EEA Esquel (id 690; −43,12, −71,55; desde 2021-05); P. Golondrinas – EEA Bariloche (id 281; −42,00, −71,52; desde 2011-10) | Consultado el 2026-10-19. Datos **cada 10 min** por `siga.inta.gob.ar/CdnaUV0iiERRpFQE.php?param_type=datosestaciones&param_value=<id>/<D-M-AAAA>%2000:00:00/<D-M-AAAA>%2023:59:59` (pide `Referer` y `User-Agent` de navegador). Viento a **2 m en km/h**, dirección en rumbo de 16 puntos. **Golondrinas no tiene anemómetro** (sólo T, HR, lluvia, suelo) y no tiene datos de 2020-02 a 2021-10, así que no cubre Las Golondrinas 2021. Trevelin queda a 23–36 km de Alerces 2023 y 2024 (no cubre 2015/2016): tarde con viento W (~75 %) y SO (~18 %) | Media: Trevelin es una estación nueva para Alerces; Golondrinas sólo aporta HR y T para Epuyén y Patriada |
| DMC Chile, Futaleufú Ad. (430002) | Viento a 10 m desde 1953, ráfaga desde 1969 | `climatologia.meteochile.gob.cl`; descarga a confirmar | Media: ya está en Meteostat |
| SMN Argentina | Esquel Aero y otras sinópticas | Pedido formal como estudiante (`argentina.gob.ar/smn/institucional/contacto`) | Media: Esquel ya está en Meteostat |
| Weather Underground | Estaciones personales en El Bolsón y Lago Puelo | Historial por estación, sin control de calidad | Baja |

No se encontró ninguna estación dentro del Parque Nacional Los Alerces ni en Cholila. Para
Alerces 2015 y 2016 la estación más útil es Trevelin (Agroforestal), que en SIPAS sólo tiene datos
diarios; Trevelin (Central de Incendios) no tiene boletines públicos.

**Pedido cancelado (2026-10-31).** Las series horarias pedidas al INTA (EEA Esquel) y a Bosques de
Chubut no llegaron, y el pedido se dio por cancelado. El viento de superficie queda como límite
declarado y cerrado: ya no es condición de reapertura de nada (pavesas, contraste ERA5/WindNinja,
Alerces 2015). La tabla anterior se conserva como registro de lo que se buscó.

**Qué permitiría reducirlo** (fuera del alcance de la tesis). Una serie horaria (o mejor, de 10 minutos) de una estación a menos
de 10 km del incendio durante el evento. Con eso se mide el error del reanálisis en vez de
suponerlo. Si la estación muestra viento del sur en Alerces 2015, es evidencia externa nueva en
los términos de la regla de parada.

## 4. Humedad de combustibles sin gradiente de altura

**Suposición.** La humedad del combustible muerto (m1, m10, m100) se calcula con la temperatura y
la humedad del aire del modelo meteorológico. Con celdas de ~25 km, el valor es el mismo a 500 m
que a 1.500 m.

**Efecto.** En la realidad, más arriba hace más frío, la humedad relativa es mayor y el
combustible está más húmedo; el bosque de lenga de altura suele quedar fuera de los incendios de
verano. El modelo lo quema tan seco como la costa. En Alerces 2015 el cinturón de lenga es el
56 % del falso positivo.

**Qué se midió.** Dos correcciones de libro (`app/validation/humedad.py`), ninguna ajustada:

- `altura-001`: lleva la temperatura a la altura de cada celda con el gradiente estándar
  (−6,5 °C/km) y conserva el punto de rocío, así que la humedad relativa también sube.
- `fosberg-001`: las tablas de Rothermel (1983) / Fosberg que usan NFDRS y BehavePlus, con
  corrección por altura, orientación, sombra y hora.

Las dos mueven el Dice ±0,01. En Alerces 2015, `altura-001` sube el m1 de la montaña pero el
falso positivo pasa de 818 a 817 ha: el aire más fresco no alcanza para frenar el fuego en la
hojarasca de lenga.

Después se buscó bibliografía y se hizo un análisis regional fuera del benchmark
(`HUMEDAD-ALTURA-PROPUESTA.md`):

- **No existe ninguna medición de humedad de hojarasca bajo lenga.** El aire medido bajo lenga
  (Paritsis et al. 2015) es 5 °C más fresco y 4–7 pp más húmedo que en el matorral, lo que suma
  ~1 pp al m1. Para que la humedad frene un TL6 a la mitad haría falta un m1 de ~20 % en la
  hojarasca.
- **El efecto de la altura es común a todos los tipos de vegetación** (Barberá et al. 2025). En los
  incendios de 2014–2026 de la cordillera de Chubut y Río Negro, fuera del benchmark, la fracción
  quemada cae con la altura igual en la lenga que en la estepa altoandina. Dentro del mismo
  incendio y la misma banda, el bosque de lenga arde como el coihue y el ciprés.
- **En calibración, el bosque de lenga no está sobrequemado:** sesgo 0,99 en los seis incendios sin
  el caso límite.
- **La lenga achaparrada sí se sobrequema** (sesgo 1,73), y en la región arde la mitad que sus
  vecinas. Pero el modelo más lento que se midió para ella (SH3, loop L) rompe Cholila. SH8 se
  mantiene como la mejor asignación medida en el benchmark, con la limitación declarada en el
  crosswalk (§5.5).

**Por qué no se corrige.**

1. La corrección física disponible, la humedad del aire llevada a cada celda, ya se aplicó sin
   ajuste y se midió.
2. Lo que falta, la hojarasca más húmeda bajo el dosel, no tiene dato con qué fijarlo. Derivarlo
   de los incendios del benchmark violaría la regla de parada.
3. El combustible del bosque de lenga no está sesgado en calibración, y la alternativa medida
   para la lenga achaparrada empeora la calibración.
4. Aun con la lenga no quemable (`diag-lw100-lenga-nb-001`), Alerces 2015 sigue sin predecir los
   ~600 ha al norte. El error dominante de ese caso es el viento (§3).
5. Alerces 2015 es un caso de prueba y no puede usarse para elegir nada.

**Consecuencia.** Con viento flojo y aire seco en la celda, el modelo sube a la lenga de altura.
Igual que con la supresión (§1), esas salidas son el peor caso.

**Qué lo reabriría** (evidencia externa nueva):

- humedad de hojarasca medida bajo lenga en un transecto de altura (~800, 1.100 y 1.400 m),
  durante una temporada de fuego;
- un umbral de ignición de la hojarasca de lenga;
- los datos por sitio de Barberá et al. (2023).

La regla y el criterio de adopción para ese caso ya están fijados en `HUMEDAD-ALTURA-PROPUESTA.md`
§4.3.

## 5. Lo ya quemado

Hay dos escalas.

**Dentro del mismo incendio.** ELMFIRE no vuelve a quemar una celda ya quemada. En el benchmark,
cada incendio arranca de un punto de ignición y cada ventana arranca del perímetro simulado por la
anterior. En la app, la simulación arranca del perímetro reconstruido con las detecciones FIRMS
(`ignition_builder.py`): lo que ya ardió hasta ese momento entra como quemado. Esa reconstrucción
no participó de la calibración (`PENDING_PARAMETERS.md` §3), pero ya se evaluó en P-24
(`DIA-1-PROPUESTA.md` §7.3): arrancar desde ella o desde la cicatriz real da pronósticos casi
iguales. La reconstrucción sólo infla las semillas chicas, porque un píxel aislado se dibuja como
44 ha.

**Incendios anteriores.** El combustible de una zona quemada años antes no es el del bosque
original.

- En el benchmark se usa el mapa CCS-BAP del último año anterior al incendio (2013 o 2017). Donde
  Hansen registra pérdida de bosque anterior al incendio, se quita el dosel. Asignar además un
  combustible de matorral a esa pérdida se probó en el loop M y no se adoptó: Patriada se frena de
  más.
- **En la app.** La app usa CCS-BAP 2017 para cualquier fecha, así que no ve las quemas de 2018 en
  adelante. Desde el 2026-10-12 (`LO-YA-QUEMADO-PROPUESTA.md` §11) se combinan dos fuentes:
  - Hansen GFC v1.13, que llega hasta 2025;
  - los años con quema de otras fuentes: dNBR ∪ MCD64A1, en `settings.otras_quemas_path`, con
    MCD64A1 hasta 2026-07.

  Con eso, la preparación reasigna el combustible de las quemas posteriores al mapa:
  - de 1–5 años, a GR1;
  - el bosque de 6–15 años, a SH3;
  - el matorral y el pastizal conservan su clase después de los 5 años.

  En bosque sólo cuenta Hansen mientras haya publicado ese año. El dosel sigue saliendo de Hansen.
  Para una simulación de 2026 cambian 43.574 ha del AOI.

**Qué se midió.**

- **Prueba de la premisa con MCD64A1** (2006–2026, sin los incendios de prueba):
  - las cicatrices de 1–2 años no vuelven a arder más que el resto (0,83 / 1,31);
  - las de 3–5 años casi no vuelven a arder (0,20; sin 2026, 0,29);
  - las de 6–15 años arden más que el resto (3,88; sin 2026, 1,41).
- **Protocolo de no regresión LYQ-3** sobre los siete de calibración: 0,439 / 0,501, igual que
  modelo-v0; el peor caso es Alerces 2023, con −0,006.
- **LYQ-2 no pasó:** la capa decidía el bosque por la cobertura de 2000 y reasignaba plantaciones.

**Lo que queda.**

- MCD64A1 trabaja en celdas de 500 m.
- La quema forestal de 2026 conserva el dosel hasta que Hansen publique ese año.
- La capa se regenera cada temporada (`scripts/exportar_mcd64a1.py`, `scripts/anio_quema.py`).
- El benchmark sólo garantiza que la regla no rompe la calibración.

## 6. Ingesta histórica de FIRMS en la app

**Antes.** La app traía las detecciones de FIRMS sólo de los productos casi en tiempo real (NRT),
que cubren los últimos meses. Un incendio de hace más de unos meses quedaba sin ignición.

**Resuelto el 2026-10-12** (`LO-YA-QUEMADO-PROPUESTA.md` §8).

- `run_firms_ingestion` pide juntas las fuentes NRT y las de archivo (SP).
- `drop_nrt_covered_by_sp` descarta las filas NRT de los días que SP ya cubre para el mismo
  satélite.
- Según `data_availability`, SP llega hasta el mes anterior a ~3 meses y NRT empieza al día
  siguiente, así que no se solapan.
- NOAA-21 no tiene producto SP y entra siempre por NRT.

## 7. Transferencia

**Suposición.** Siete incendios de calibración representan los regímenes de fuego del área.

**Efecto.** En los cuatro de prueba el Dice baja a 0,191 (mediana 0,167), con dos alarmas.
Modelo-v0 es una línea de base auditable para Los Alerces y alrededores, no una afirmación de
generalización. El resultado de prueba es descriptivo: no se usó para volver a elegir la receta.

Con el protocolo P-24 (2026-10-31, `diagnostico-e2e/notas/AB-p24-prueba.md`), la mediana del Dice del
crecimiento en prueba es 0,084 a 12 h y 0,145 a 24 h. Le gana a la cadena en los cuatro casos, pero
el nivel es la mitad que en los cuatro incendios GFS de calibración (0,192 y 0,262), y a la
persistencia le gana sólo en 3 de 4. La brecha entre calibración y prueba de la cadena sigue en P-24.

## 8. Suposiciones de entrada sin base local

Todas cerradas como límites declarados el 2026-10-31; detalladas en `PENDING_PARAMETERS.md` §3:

- **m10/m100:** offsets +2/+5 sin fundamento físico propio; el benchmark resultó insensible.
  Cerrado como límite declarado el 2026-10-31: no se buscan mediciones.
- **CBH de bosque nativo:** valores de literatura, no un inventario regional. Su rango plausible
  mueve la iniciación de copa del día 1 sólo en TU5 (coihue y ciprés con caña, sobre el umbral) y en
  el ñire debajo de ~1 m; en lenga, TL2 y alerce no cambia nada
  (`diagnostico-e2e/notas/AE-cbh-z0-sensibilidad.md`). Cerrado como límite declarado el
  2026-10-31: sólo lo reabre una medición de la altura de la escalera en esas dos clases.
- **Rugosidad:** valor convencional (reproduce el factor 0,87 de 10 m a 20 ft), no medido en el
  AOI. En 0,03–0,5 m, la propagación superficial cambia ×0,97–1,04; la copa, por el umbral de TU5
  (nota AE). Cerrado como límite declarado el 2026-10-31: sólo lo reabre una medición del cociente
  20 ft / 10 m en terreno abierto del AOI.
- **Reconstrucción de perímetro FIRMS:** no calibrada, pero evaluada en P-24 contra la cicatriz
  real (ver §5). Cerrada como límite declarado el 2026-10-31.

## 9. Acierto de P-24: el error es de forma, no de área

**Suposición.** Reiniciar ELMFIRE en cada pasada VIIRS, con el pronóstico GFS disponible, alcanza
para pronosticar hacia dónde crece el incendio en las 12–24 h siguientes.

**Efecto.** El Dice del crecimiento es bajo:

- mediana 0,192 / 0,262 a 12 / 24 h en los cuatro incendios GFS de calibración;
- 0,084 / 0,145 en los cuatro de prueba.

Le gana a la cadena en todos los casos de prueba, pero a la **persistencia** (dilatar lo observado
al ritmo en que venía creciendo) le gana poco fuera de calibración: +0,021 a 12 h y +0,038 a 24 h,
en 3 de 4 (`diagnostico-e2e/notas/AB-p24-prueba.md`). Es el límite que más acota lo que el producto
puede prometer: indica tendencia y zonas expuestas, no el perímetro.

**Por qué** (`DIAGNOSTICO-PRECISION-E2E.md`, "Respuesta corta" y §1; las causas no son aditivas):

1. **Forma y rumbo: el residuo dominante.** El crecimiento predicho rodea toda la semilla
   (elongación 1,5), mientras que el observado avanza hacia un lado (2,9–3,2). El rumbo está errado
   en 58–67° de mediana. Por eso igualar el área no sube el Dice (−0,013 a 12 h, −0,003 a 24 h).
2. **El viento de entrada** (§3) es la causa más probable del rumbo. Contra estaciones, el GFS que
   recibe P-24 se desvía −13° en Futaleufú, +23° en Esquel y +81° en El Bolsón, con 0,52–0,80× de
   la rapidez; σ circular 30–41°. Bajo dosel, con un WAF de ~0,08, ni la dirección correcta del
   valle movería el frente (loop K). SMN WRF no mejora al GFS (frente 4) y el viento de estación
   quedó cancelado.
3. **Área errada ×4 en las dos direcciones.** El primer reinicio queda 2–4,5× corto (§2: copa que el
   acople Van Wagner + Rothermel no enciende). Los reinicios tardíos sobre-propagan porque no hay
   supresión (§1): 25 de 28 reinicios k ≥ 2.
4. **La semilla.** El 26–61 % del área sembrada cae fuera de la cicatriz (píxel de 375 m, relleno
   del casco y detecciones de otros incendios). El 70 % del crecimiento predicho brota de esa parte
   y ahí está casi todo el exceso de flanco (`diagnostico-e2e/notas/I-isotropia.md`, `T-semilla.md`).
5. **La métrica es exigente.** Se puntúa sólo el crecimiento, una franja angosta pegada a la
   semilla. Un desplazamiento de pocos cientos de metros la pierde. El techo de la referencia es
   ~0,7–0,9, no 1, pero eso no explica la brecha: corregir las islas no vistas mueve el Dice de
   modelo-v0 en +0,001.

**Qué no lo explica.** La meteorología del pronóstico frente al análisis (|ΔDice| ≤ 0,003 por
incendio, `P24-PRONOSTICO-GFS.md`) ni la referencia (punto 5). El ensamble GEFS tampoco permite
decir que la meteorología *no* domine: está sub-dispersado de entrada (3–11° contra 30–41° de error
del GFS en estaciones).

**Qué se midió.** Todo lo de §1–§3 (supresión, pavesas, WindNinja, rotación empírica, viento de
estación, SMN WRF), el abrigo bajo el dosel (no es la causa del flanco, nota I), el ADJ secuencial
(falsado offline en su forma simétrica) y el filtro de conexión de la semilla (no mueve la mediana).
Ninguno corrige el rumbo.

**Qué lo reduciría.** Un viento de superficie que resuelva el valle (dato que hoy no existe, §3), o
asimilar entre pasadas la velocidad y el rumbo observados del crecimiento (`DIA-1-PROPUESTA.md` §3;
sería otro producto, no modelo-v0). Ninguno está en el alcance actual: queda como **límite
declarado** (2026-11-01). No se reabre con estos once incendios.
