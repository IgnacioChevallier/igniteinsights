# Riesgos y suposiciones de modelo-v0

> Corte: 2026-10-12. Complementa `ESTADO-RESEARCH.md` §6. Cada punto dice qué supone el modelo,
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
| 2 | Día 1 explosivo | Desde la ignición sub-propaga el primer día 6–21× en cuatro de seis incendios. Desde la primera pasada VIIRS el déficit desaparece en dos y queda en 2–3,5× en otros dos | Medido (P-24 y diagnóstico de copa); límite declarado |
| 3 | Viento de superficie | Dirección del frente errada en 20–100°; en Alerces 2015 el fuego sube la montaña en vez de bordear el lago | Límite de datos |
| 4 | Humedad sin gradiente de altura | La montaña arde tan seca como el valle | Medido; cerrado como límite |
| 5 | Lo ya quemado | La app usaba el mapa de 2017 para cualquier fecha; ahora reasigna las quemas posteriores por edad | Resuelto en la app (LYQ-3) |
| 6 | Ingesta histórica de FIRMS | La app no podía preparar incendios viejos | Resuelto en la app |
| 7 | Transferencia | Prueba con cuatro incendios: Dice 0,191 y dos alarmas | Declarado |

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
| Primeras horas, desde la ignición | 6–21× **por debajo** en cuatro de seis incendios (§2) |
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
- **En Patriada y Alerces 2024 queda un déficit de 2–3,5×, pero sólo en el primer reinicio.**
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
ignición. Con el protocolo P-24 el Dice del crecimiento mejora frente a la cadena de modelo-v0:

- a 12 h, +0,107 de mediana, en 6 de 6 incendios;
- a 24 h, +0,141, en 5 de 6;
- en los dos plazos, ELMFIRE le gana a la extrapolación ingenua en los 6.

Las primeras 2–6 h, antes de la primera detección, quedan como límite: no son pronosticables con
ELMFIRE 2025.0212 configurado como modelo-v0.

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
pasa de 0,029 a 0,020.

**Estaciones disponibles.** El benchmark ya usa, vía Meteostat, El Bolsón (87800), Esquel
(87803, 40 km al E de Los Alerces) y Futaleufú, Chile (85832). Fuentes adicionales identificadas
(2026-10-11):

| Fuente | Estaciones relevantes | Acceso | Prioridad |
|---|---|---|---|
| INTA SIPAS, red de la Dirección de Bosques de Chubut | Las Golondrinas, Epuyén, Corcovado, Río Pico; Trevelin (Central de Incendios); Lago Puelo (Campo Forestal); El Hoyo; El Maitén | Boletines por estación en `sipas.inta.gob.ar` (IDs 64, 63, 62, 65, 67, 68, 5, 6). SIPAS y SIGA no respondían el 2026-10-11. Las series públicas de SIGA son diarias (paquete R `AgRoMeteorologiaINTA/siga`); los datos horarios hay que pedirlos al INTA o a la Dirección de Bosques | **Alta**: Las Golondrinas y Epuyén están sobre dos incendios del benchmark |
| DMC Chile, Futaleufú Ad. (430002) | Viento a 10 m desde 1953, ráfaga desde 1969 | `climatologia.meteochile.gob.cl`; descarga a confirmar | Media: ya está en Meteostat |
| SMN Argentina | Esquel Aero y otras sinópticas | Pedido formal como estudiante (`argentina.gob.ar/smn/institucional/contacto`) | Media: Esquel ya está en Meteostat |
| Weather Underground | Estaciones personales en El Bolsón y Lago Puelo | Historial por estación, sin control de calidad | Baja |

No se encontró ninguna estación dentro del Parque Nacional Los Alerces ni en Cholila. Para
Alerces 2015 y 2016 la estación más útil sigue siendo Trevelin (Central de Incendios), si su
serie cubre esas fechas.

**Qué permitiría reducirlo.** Una serie horaria (o mejor, de 10 minutos) de una estación a menos
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
no participó de la calibración (`PENDING_PARAMETERS.md` §2), pero ya se evaluó en P-24
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

## 8. Suposiciones de entrada sin base local

Detalladas en `PENDING_PARAMETERS.md` §2:

- **m10/m100:** offsets +2/+5 sin fundamento físico propio; el benchmark resultó insensible.
- **CBH de bosque nativo:** valores de literatura, no un inventario regional.
- **Rugosidad:** valor convencional, no medido en el AOI.
- **Reconstrucción de perímetro FIRMS:** no calibrada, pero evaluada en P-24 contra la cicatriz
  real (ver §5).
