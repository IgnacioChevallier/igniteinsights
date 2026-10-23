# G · Las Golondrinas 2021 con la meteorología observada (SYNOP El Bolsón)

> 2026-10-19. Diagnóstico: no es una receta nueva ni un candidato a modelo-v1. No toca
> `benchmarks/modelos/`, `benchmarks/particion.json` ni la receta `lw-100-001`. Empaquetador
> `meteo_observada` en `scripts/benchmark.py`. Test: `tests/test_meteo_observada.py`. Protocolos:
> `benchmarks/casos/las-golondrinas-2021/synop-v6-*.json`.

## 0. Pregunta

En el modelo-v0 (`lw-100-001`), `las-golondrinas-2021/calibracion-v6` da Dice 0,012: quema 224 de
10.622 ha en 24 h. La hipótesis es que se trata de un **límite de la entrada meteorológica**. La
pregunta es si ELMFIRE, con viento, temperatura y humedad parecidos a lo observado, llega al orden
de magnitud del incendio (~10.000 ha en una noche).

## 1. Diseño y criterio (registrados antes de correr)

### 1.1 Lo observado y lo que recibió el modelo

SYNOP crudo de El Bolsón Aero (87800), a ~5 km de los focos
(`data/benchmark/cache/synop/87800_2021030418_2021031018.txt`). El 9-mar no tiene ningún dato: todas
las horas son `NIL`. El único reporte de la noche es el de las **10-mar 00Z** (21 ART), con
`23629 10239 20040`: viento desde 360° a 29 kt a 10 m, T 23,9 °C, Td 4,0 °C (HR 27,5 %) y Tmax de la
tarde 32,0 °C. A las 12Z hay calma, cielo cubierto, HR 97 % y 12 mm de lluvia en la noche.

El paquete `calibracion-v6`, ventana 0, en el foco de Las Golondrinas:

| hora (Z) | ws (mph, 20 ft) | wd (desde) | T GFS (°C) | HR GFS | m1 / m10 / m100 (%) |
|---|---:|---:|---:|---:|---|
| 18 | 8,4 | 289° | 23,3 | 20 | 4,5 / 6,5 / 9,5 |
| 21 | 9,0 | 293° | 22,1 | 25 | 5,3 / 7,3 / 10,3 |
| 00 | 6,7 | 304° | 12,4 | 61 | 11,6 / 13,6 / 16,6 |
| 03 | 7,4 | 315° | 10,9 | 78 | 16,5 / 18,5 / 21,5 |
| 06 | 7,2 | 310° | 12,5 | 84 | 18,8 / 20,8 / 23,8 |
| 08 | 2,7 | 289° | 11,3 | 98 | 25,2 / 27,2 / 30,2 |

El GFS está seco hasta las 21Z, pero se humedece unas horas antes que lo observado: a las 00Z marca
12,4 °C y HR 61 %, contra 23,9 °C y 27 % medidos. El viento del GFS es 3–4 veces menor que el medido
durante toda la noche.

### 1.2 Reemplazo

- 29 kt a 10 m equivalen a **29,0 mph a 20 ft** con `wind_height_factor()` (0,870) y `MS_TO_MPH`,
  la misma conversión que aplica `derive_wind` al GFS.
- Con T 23,9 °C y HR 27,5 %, `derive_moisture` (EMC de Nelson) da m1/m10/m100 = 5,5/7,5/10,5 %.
- Cada valor medido es **uniforme en el dominio**, como en la prueba vieja `estacion-v2`. A diferencia
  de esa prueba, la serie está escrita en el JSON del caso (`empaquetado.meteo_observada.serie`) y no
  se lee de Meteostat.
- Todo lo demás es el paquete `calibracion-v6` **byte a byte**: estáticos, combustibles, dosel,
  igniciones, cicatriz y GFS de las horas no reemplazadas.
- Para la humedad se reemplazan T y HR en `t2m_gfs`/`rh_gfs` y m1/m10/m100 se regeneran con
  `weather_builder.derive_moisture`; no se editan los rásters a mano. Los `m*_retardo.tif` no se
  regeneran (necesitarían la serie previa de 120 h) y se sacan del paquete: una receta
  `modelo_humedad: retardo` falla en lugar de correr con la humedad vieja.
- **Duración del evento.** Hay un solo reporte, así que la duración es el supuesto central. Lo
  observado se sostiene desde las 18Z (la ignición) hasta las 00Z, 03Z o 06Z inclusive. ELMFIRE
  interpola linealmente hasta la banda GFS de la hora siguiente. Desde las 07Z vuelve el GFS, que ya
  está húmedo y con poco viento (coincide con la lluvia y la calma que se observaron).
- Sostener la HR de las 00Z desde las 18Z deja las 18–21Z apenas más húmedas que el GFS (m1 5,5 %
  contra 4,5–5,3 %). La Tmax de 32 °C indica que la tarde fue todavía más seca. Las dos fuentes
  subestiman esas horas por igual, así que no se corrige.

### 1.3 Escenarios

Todos con la receta `lw-100-001`, contra la cicatriz completa (`hasta_horizonte: false`).

| protocolo | viento | dirección | humedad | sostenido hasta |
|---|---|---|---|---|
| `synop-v6-s0` | GFS | GFS | GFS | — (control: tiene que dar 224 ha / Dice 0,012) |
| `synop-v6-s1-{00,03,06}z` | 29 mph | GFS | GFS | 00Z / 03Z / 06Z |
| `synop-v6-s1n-03z` | 29 mph | 360° | GFS | 03Z |
| `synop-v6-s2-{00,03,06}z` | GFS | GFS | T 23,9 °C, HR 27,5 % | 00Z / 03Z / 06Z |
| `synop-v6-s3-{00,03,06}z` | 29 mph | GFS | T 23,9 °C, HR 27,5 % | 00Z / 03Z / 06Z |
| `synop-v6-s3n-03z` | 29 mph | 360° | T 23,9 °C, HR 27,5 % | 03Z |

La dirección de S3 es la del GFS. El empuje del GFS (hacia ~110–125°) coincide con el eje de la
cicatriz desde los focos (107–123°). El norte de la estación es viento encauzado en el valle N–S, y
llevado a todo el dominio empujaría el fuego hacia el sur, fuera de ese eje. El norte se corre sólo
como sensibilidad (`s1n`, `s3n`) y no entra en el veredicto.

### 1.4 Criterio (sobre S3 con la dirección del GFS, contra la cicatriz completa)

- Si **S3 llega a sesgo de área ≥ 0,5 con alguna duración ≤ 06Z**, el caso queda como
  **límite de la entrada meteorológica**.
- Si **S3 a 06Z no pasa de sesgo 0,2**, hay **un límite del modelo además del clima** (pavesas,
  interfaz urbano-forestal o combustibles).
- En el medio, se informa sin veredicto fuerte.

Además del criterio se informan, por escenario: el área a 6, 12 y 24 h, Dice, sesgo, precisión y
recall. Un sesgo alto con Dice bajo diría que el área llega pero no en el lugar correcto; eso no
cambia el veredicto, pero se dice explícitamente.

## 2. Resultados

Corrido el 2026-10-19/20, una corrida de ELMFIRE a la vez, en 20–30 s cada una (S0 tardó 28 s).
Todo contra la cicatriz completa: 10.622 ha observadas.

**Control.** S0 reproduce la iteración del modelo-v0 byte a byte. Los insumos son iguales: el
`elmfire.data` difiere sólo en las rutas y el namelist normalizado es el mismo. También es igual el
TOA. Da 224 ha y Dice 0,012. En los otros paquetes cambian sólo los archivos y las horas
declarados; las bandas que no se tocaron son idénticas a las de la base.

| escenario | sostenido hasta | ha a 6 h | ha a 12 h | ha a 24 h | Dice | sesgo | precisión | recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S0 (GFS) | — | 139 | 185 | 224 | 0,012 | 0,021 | 0,28 | 0,006 |
| S1 viento, dir. GFS | 00Z | 264 | 410 | 509 | 0,055 | 0,048 | 0,60 | 0,029 |
| S1 viento, dir. GFS | 03Z | 264 | 468 | 559 | 0,062 | 0,053 | 0,62 | 0,033 |
| S1 viento, dir. GFS | 06Z | 264 | 493 | 585 | 0,065 | 0,055 | 0,62 | 0,034 |
| S1n viento, desde 360° | 03Z | 382 | 490 | 570 | 0,032 | 0,054 | 0,31 | 0,017 |
| S2 humedad | 00Z | 147 | 202 | 247 | 0,015 | 0,023 | 0,33 | 0,008 |
| S2 humedad | 03Z | 147 | 255 | 311 | 0,021 | 0,029 | 0,37 | 0,011 |
| S2 humedad | 06Z | 147 | 333 | 424 | 0,030 | 0,040 | 0,39 | 0,016 |
| **S3 viento + humedad, dir. GFS** | 00Z | 446 | 865 | 1.061 | 0,117 | 0,100 | 0,64 | 0,064 |
| **S3 viento + humedad, dir. GFS** | 03Z | 446 | 1.533 | 1.866 | 0,205 | 0,176 | 0,69 | 0,121 |
| **S3 viento + humedad, dir. GFS** | 06Z | 446 | 1.963 | 2.404 | 0,243 | **0,227** | 0,66 | 0,149 |
| S3n viento + humedad, desde 360° | 03Z | 392 | 631 | 718 | 0,044 | 0,068 | 0,35 | 0,024 |

El área a 6 h es la misma con las tres duraciones porque las tres sostienen lo observado al menos
hasta las 00Z, que es la hora 6.

**Alcance del frente** (distancia máxima desde el foco más cercano). S0 llega a 1,6 km, S1-06Z a
3,3 km y S3-06Z a 8,7 km: 1,0 km a las 3 h, 5,3 km a las 6 h, 8,0 km a las 9 h y 8,6 km a las 12 h.
La cicatriz se extiende hasta 25,6 km (p95) y 27,6 km (máximo) desde los focos.

### 2.1 Lectura

- **Ni el viento ni la humedad bastan por separado; juntos se potencian.** S1 multiplica el área por
  2,5 y S2 por 1,1–1,9, pero S3 la multiplica por 4,7–10,7, mucho más que la suma de los dos. Con
  29 mph y m1 del GFS (11–25 % desde las 00Z) el fuego no corre. Con el aire seco y el viento del
  GFS (7 mph) tampoco.
- **El fuego va hacia donde está la cicatriz.** La precisión sube de 0,28 a 0,64–0,69 con la
  dirección del GFS. Con el norte uniforme baja a 0,31–0,35: el fuego corre al sur, fuera del eje.
  Eso confirma que la dirección de la estación es local del valle y que la del GFS sirve.
- **La duración importa hasta 03Z y después rinde menos.** De 00Z a 03Z el área de S3 pasa de 1.061
  a 1.866 ha; de 03Z a 06Z, sólo a 2.404 ha. El frente avanza ~1,1 km/h entre las 3 y las 9 h y se
  frena antes de que vuelva el GFS (8,0 → 8,6 km entre las 9 y las 12 h).
- **Arranque lento.** En las primeras 3 h S3 llega a 1,0 km, lo mismo que S0, con 29 mph y m1 de
  5,5 %. Los focos están en TU3 y TL8 bajo plantaciones, y el 80 % de la cicatriz tiene dosel (cc
  medio 59 %). La hipótesis, **no verificada acá**, es que el WAF de dosel cerrado reduce el viento a
  media llama a una fracción del de 20 pies.

## 3. Veredicto (con el criterio de §1.4)

**En el medio, sin veredicto fuerte, más cerca del límite inferior.** El mejor S3 (sostenido hasta
06Z) llega a sesgo 0,227: pasa por poco el umbral de 0,2 y queda lejos de 0,5. Ninguna duración
≤ 06Z llega a 0,5.

Lo que sí se puede decir:

- La meteorología observada **explica una parte real** del déficit. Multiplica el área por ~10, sube
  el Dice de 0,012 a 0,24 y pone el fuego en el lugar correcto (precisión 0,66).
- **No explica el orden de magnitud.** Aun con 12 h de viento de 29 mph y aire seco, más que lo que
  el único reporte respalda, el modelo quema el 23 % del área y recorre un tercio de la distancia
  (8,7 de ~26 km). Para cubrir 26 km en una noche haría falta un frente sostenido de ~3 km/h; el
  modelo da ~1 km/h.
- El resto del déficit es de algo que esta prueba no toca. Los candidatos, sin orden entre ellos:
  - **pavesas**: `lw-100-001` corre sin `&SPOTTING`;
  - **WAF bajo dosel** en las plantaciones;
  - **interfaz urbano-forestal**: 605 viviendas, sin modelo de estructuras;
  - **combustibles** de la cicatriz.

Las Golondrinas sigue siendo un caso límite. Ya no puede atribuirse sólo al GFS: es un límite de la
entrada meteorológica **y** del modelo de propagación tal como está configurado en el modelo-v0.

## 4. Limitaciones

- **Un solo reporte.** La duración del evento es un supuesto, y 06Z es generoso. La humedad
  sostenida desde las 18Z es la de las 21 ART, no la de la tarde: la Tmax fue 32 °C.
- **Viento uniforme en el dominio**, con la rapidez de una estación de fondo de valle y la dirección
  del GFS. No hay ráfagas, ni aceleración en las laderas, ni flujo encauzado.
- **Sin pavesas ni estructuras.** Es la configuración del modelo-v0; activarlas sería otra prueba.
- **Humedad instantánea.** m1/m10/m100 se recalculan con `derive_moisture` (EMC + 0/2/5 %): las
  clases de 10 y 100 h no tienen historia de secado. Al volver al GFS, la humedad salta de 5,5 % a
  ~17–19 % en una hora.
- Es una sola receta (`lw-100-001`). No se ajustó ningún parámetro global: el SYNOP crudo sirve para
  **caracterizar** el límite, no para calibrar (regla de parada del modelo-v0).

## 5. Qué quedó sin resolver

- Cuánto del déficit restante es de pavesas y cuánto de WAF bajo dosel. Separarlo es barato: S3-03Z
  con `&SPOTTING` (los valores de `namelist_writer.SPOTTING_HINDCAST`) y S3-03Z sin dosel en las
  plantaciones son dos corridas más, cada una de menos de un minuto. No se corrieron: el diseño
  registrado no las incluía.
- La serie horaria real de la noche. Sólo la tendría INTA (El Maitén) o una estación privada de
  Lago Puelo (RIESGOS §3, tabla de estaciones).

## 6. Enmienda (2026-10-22): ¿el freno es de tiempo o de lugar?

> Registrada antes de mirar las salidas ni de correr nada. Viene de una pregunta del autor: en el
> mapa de S3-06Z la lengua quemada va por el eje correcto, y prolongada podría cubrir la cicatriz.
> ¿La limitación es la duración de la ventana?

En §2 el frente de S3-06Z pasa de 8,0 km a la hora 9 a 8,6 km a la hora 12, **con lo observado todavía
forzado** (las horas 9–12 son 03Z–06Z). Si fuera sólo una cuestión de tiempo, el frente no tendría
por qué frenarse antes de que vuelva el GFS. Hay dos pruebas.

### 6.1 Qué hay en la cabeza del frente (sin correr: salidas de S3-06Z)

Se recuperan las salidas de `synop-v6-s3-06z` con `benchmark.py materializar` (sin correr
ELMFIRE). El **borde detenido** son las celdas de la cicatriz que siguen sin quemar a la hora 12 y
son vecinas (8-conexas) de una celda quemada, dentro del sector del eje de la cicatriz (rumbo 100–135°
desde el foco más cercano) y a más de 6 km de él, que es donde estaba el frente cuando se frenó. Se
informa la composición del borde detenido (`fbfm40`, `cc`, `ch`, pendiente a favor o en contra del
avance) y la de las celdas que quemaron entre las horas 6 y 9, cuando el frente todavía corría.

Criterio: si **≥ 50 % del borde detenido** pertenece a una sola causa, el freno se le atribuye:

- **combustible**: no quemable (NB*) o un modelo que no quemó entre las horas 6 y 9;
- **dosel**: `cc` ≥ 50 % con un modelo que sí quemó en las horas 6–9 sin dosel;
- **terreno**: pendiente en contra del avance (ladera abajo) ≥ 10°.

Si ninguna causa llega al 50 %, se informa la composición sin atribuirla.

### 6.2 Cota contrafáctica: lo observado sostenido 18 h (`synop-v6-s3-12z`)

Es S3 con viento y humedad, dirección del GFS, sostenido de 18Z a **12Z** y después el GFS. **No es
un escenario plausible**: el SYNOP de las 12Z da calma, HR 97 % y 12 mm de lluvia. Es la cota física
de "si le diéramos más tiempo".

Criterio:

- si el frente de S3-12Z **no pasa de 10 km** y el sesgo queda **< 0,5**, la duración de la ventana
  queda **descartada** como explicación;
- si el frente pasa de **20 km** o el sesgo llega a **≥ 0,5**, el tiempo **sí** limita, pero a costa
  de pedir el doble de duración que la que respaldan las observaciones; eso se informa como una
  velocidad de avance subestimada, no como un problema de la ventana;
- en el medio, se informa sin veredicto.

### 6.3 Resultados

Alcance del frente (distancia máxima desde el foco más cercano) y área, por hora:

| hora | S3-06Z ha | S3-06Z km | S3-12Z ha | S3-12Z km |
|---:|---:|---:|---:|---:|
| 3 | 93 | 1,0 | 93 | 1,0 |
| 6 | 448 | 5,3 | 448 | 5,3 |
| 9 | 1.263 | 8,0 | 1.263 | 8,0 |
| 12 | 1.964 | 8,6 | 1.964 | 8,6 |
| 15 | 2.119 | 8,7 | 2.702 | 8,8 |
| 18 | 2.190 | 8,7 | 4.077 | 12,0 |
| 24 | 2.406 | 8,7 | 4.669 | 12,6 |

S3-12Z, contra la cicatriz completa: **Dice 0,344, sesgo 0,440**, precisión 0,56, recall 0,25. La
corrida de ELMFIRE más la puntuación tardó 2 min.

**Borde detenido de S3-06Z** (hora 12, eje 100–135°, a más de 6 km): 294 celdas (26 ha), comparado
con las 9.051 celdas que quemaron entre las horas 6 y 9:

| | borde detenido | quemó en horas 6–9 |
|---|---|---|
| `fbfm40` | TL6 51 %, NB8 21 %, SH8 12 %, TU5 9 %, NB9 5 % | TU5 51 %, SH4 13 %, TU3 7 %, GR2 7 %, GR1 7 %, TL8 7 %, TL6 4 % |
| `cc` ≥ 50 % | 78 % | 74 % |
| `ch` medio | 20,9 m | 21,4 m |
| ladera abajo ≥ 10° | 12 % | 9 % |

Por el criterio de §6.1: **dosel 70 %**, combustible 26 %, terreno 12 %.

El NB8 (agua) de la cicatriz son 8 ha en el eje, entre 7,0 y 12,9 km de los focos: una franja
angosta, cauce o costa, que cruza el avance. Donde S3-12Z rompe el freno (horas 15–18, 1.376 ha) quema
sobre todo TU5 (47 %). Lo que queda sin quemar a más de 9 km (6.726 ha) es TL6 25 %, SH8 22 %, SH4 17 %
y TU5 15 %.

### 6.4 Lectura y veredicto

- **El freno es de lugar, no de reloj.** En S3-12Z, con lo observado forzado tres horas más, el
  frente sigue clavado entre 8,6 y 8,8 km hasta la hora 15. Sólo después rompe hasta 12 km y vuelve a
  frenarse cuando entra el GFS.
- **Cota de §6.2: en el medio, sin veredicto.** El frente pasa de 10 km (12,6) pero no llega a 20, y
  el sesgo queda en 0,44 < 0,5. Aun con 18 h de viento de 29 mph y aire seco, que contradicen el SYNOP
  de las 12Z, el modelo quema el 44 % del área y recorre la mitad de la distancia. Alargar la ventana
  no cierra el caso.
- **El criterio de §6.1 atribuye el freno al dosel (70 %), pero el control no lo sostiene.** Donde
  el frente corría el dosel era el mismo (cc ≥ 50 % en el 74 %, `ch` 21 m). Lo que cambia es el
  **modelo de superficie**: TU5 donde corría, TL6 y agua donde se frenó. El criterio separaba mal las
  causas: contaba como "dosel" a TL6 bajo dosel porque TL6 quemó algo (4 %) en las horas 6–9. La
  lectura que resiste es **TL6 bajo dosel cerrado, más una franja de agua**: la hojarasca de TL6 con
  el viento reducido por el dosel avanza poco, y el fuego sólo sigue donde encuentra TU5.
- El incendio real cruzó esa franja en una noche. Sin `&SPOTTING`, ELMFIRE sólo la rodea por donde
  hay continuidad, y eso le lleva 3–6 h. Es el argumento más directo a favor de las **pavesas** como
  mecanismo faltante, pero esta prueba no lo demuestra.

### 6.5 Qué sigue

- **S3-06Z con `&SPOTTING`** (`namelist_writer.SPOTTING_HINDCAST`): si cruza la franja de agua y TL6
  y el sesgo pasa de 0,5, las pavesas explican el resto.
- **El TL6 de la cicatriz** (23 % del área): ver de qué clase de CCS-BAP sale en el crosswalk y si es
  plantación, bosque nativo o matorral bajo dosel. Si es una plantación con sotobosque, el TL6 puede
  ser el artefacto (AUDITORIA-FISICA §7.4).

## 7. Enmienda (2026-10-23): chequeos offline y dos corridas que separan mecanismos

> §7.1 se hizo sin ELMFIRE. §7.2 se registró antes de correr: las recetas, las corridas y los
> criterios quedaron escritos antes de ver ninguna salida.

### 7.1 Chequeos sin correr

**Arranque lento (§2.1): no hay bug de dosel.** En los insumos de S3-03Z, `ch` y `cc` vienen en
Int16 con la escala correcta (`ch` = 10 × m, máximo 43,2 m; `cc` de 0 a 100 %). En el foco de Las
Golondrinas: TU3, cc 10 %, ch 8,8 m. En el de Cerro Radal: TL8, cc 99 %, ch 26,6 m. La salida `vs` de
ELMFIRE está en m/min y coincide con Rothermel a mano (`copa.rothermel` con el WAF de
`copa.waf_elmfire`, 29 mph, m1 5,5 %) donde no hay dosel: GR2 34 contra 41 m/min y GR1 15 contra 11.
Bajo dosel, ELMFIRE va más rápido que la ROS de superficie a mano (TU3 11,6 contra 4,3 m/min de
mediana, por la copa), no más lento.

El «1,0 km en 3 h, igual que S0» es una coincidencia de dos frentes distintos:
- **Golondrinas:** con 29 mph sale tres veces más rápido que S0 (0,58 contra 0,21 km en la primera
  hora). Entre las horas 1 y 3 se estanca a ~4 m/min en SH4 (52 % del primer km a sotavento), con
  cc 37 % y WAF 0,125. La ROS a mano de SH4 ahí es 4,8 m/min. A partir de 1,5 km entra en TU5, la
  copa se enciende y llega a 5,3 km a las 6 h.
- **Cerro Radal:** TL8 con cc 96 % y WAF 0,071, 0,26 km en 3 h, consistente con Rothermel
  (0,8 m/min).

El dosel en el matorral es una decisión del loop L (AUDITORIA-FISICA): sin él, los otros incendios se
pasan. No reabre modelo-v0.

**Número de focos: dos en la caja, confirmados.** La pericia de la Policía Federal (Río Negro, agosto
de 2021) identifica cuatro focos de origen: Las Golondrinas (línea de media tensión sobre coníferas),
Cerro Radal y dos cerca de Cholila, que quedan fuera de la caja (límite sur −42,2°). Bomberos:
«después fueron cientos de focos, pero los puntos de origen fueron claramente dos». Esos «cientos»
son pavesas. Las fuentes que cuentan 5 o 7 focos suman El Maitén, que es **Cuesta del Ternero**
(corregido en §9.3: es **El Boquete**):
activo en FIRMS desde el 8-mar 04:30 UTC a 17-28 km al este, excluido como `otro_incendio_probable`
(`component-001`, 3.255 ha) y a ≥ 3,5 km de cualquier celda de la cicatriz (mediana 7,8 km).

**Velocidad observada del frente (FIRMS del caché, hasta el 20-mar).** El primer día, VIIRS ve la
cicatriz dos veces:
- a la hora 1, a 0,4-1,9 km de los focos;
- a las horas 10-11, **sólo a 22,6-27,5 km**, en la parte sureste (2.932 ha, unida al cuerpo
  principal).

Las franjas de 5-20 km (6.400 ha) no aparecen ese día: ya estaban quemadas o las tapaba el humo. Si
esa parte sureste es el frente de Las Golondrinas (no hay ningún foco documentado ahí), el frente
avanzó al menos **2,2-2,6 km/h** en promedio durante las primeras 10 h. El modelo, con S3, da
~1 km/h.

**El TL6 del borde detenido (§6.5) no es un artefacto.** Sale sólo de (TF, Le), bosque de lenga, y en
la cicatriz está entre 1.047 y 1.474 m (p10-p90; 0 % por debajo de 900 m), con cc 90 % y ch 19 m.
Es lenga real en altura. El incendio la cruzó en una noche: 2.461 ha, el 23 % de la cicatriz.

### 7.2 Corridas y criterio (registrado antes de correr)

Las dos van sobre `synop-v6-s3-03z`, la duración mejor respaldada (§6.5 decía 06Z; se cambia a 03Z
para no sumar el supuesto generoso de duración). Línea base S3-03Z: 1.868 ha, 8,4 km a las 24 h,
Dice 0,205, sesgo 0,176, precisión 0,69.

- **A, pavesas — `lw-100-pavx10-001`.** Es `lw-100-001` con `&SPOTTING` en la variante fuerte del
  loop L (10 % de las celdas en copa y 1 % en superficie lanzan pavesas). La plantilla
  `SPOTTING_HINDCAST` sola no enciende ningún foco (loop L, TOA idéntico), así que correrla no
  separa nada. A diferencia del loop L, no lleva CBH × 0,5: v6 ya tiene el CBH de literatura.
- **B, dosel — `lw-100-sin-dosel-001`.** Es `lw-100-001` sin dosel en todos los grupos (GR, GS, SH,
  TU, TL). Es una cota del WAF: viento abierto en todo el dominio. Efecto lateral conocido: también
  apaga la copa. Se cambia el «sin dosel en las plantaciones» de la propuesta porque TL8 es el 5 % de
  la cicatriz, y el freno es TL6 bajo cc 90 % (§6.4, §7.1).

Criterio, para cada una y contra la cicatriz completa:
- **sesgo ≥ 0,5 con precisión ≥ 0,5**: ese mecanismo explica el resto del déficit con la duración
  respaldada;
- **sesgo 0,3-0,5**, o sesgo ≥ 0,5 con precisión < 0,5: contribuye, sin veredicto (el área llega,
  pero no al lugar correcto);
- **sesgo < 0,3**: no alcanza por sí solo.

Además, para cada corrida se informan el alcance del frente a las horas 3, 6, 9, 12 y 24 (si pasa de
20 km reproduce el avance que vio VIIRS), el Dice y la precisión. Ninguna de las dos puede entrar en
modelo-v0, dé lo que dé: las pavesas fuertes y el matorral sin dosel ya empeoraron otros incendios en
el loop L. Es una caracterización del caso límite.

### 7.3 Resultados

Corrido el 2026-10-23, de a un ELMFIRE (A: 2,7 min; B: 0,7 min). Contra la cicatriz completa
(10.622 ha):

| corrida | Dice | sesgo | precisión | recall | 3 h | 6 h | 9 h | 12 h | 24 h |
|---|---:|---:|---:|---:|---|---|---|---|---|
| S3-03Z base (`lw-100-001`) | 0,205 | 0,176 | 0,69 | 0,12 | 93 ha · 1,0 km | 448 · 5,3 | 1.263 · 8,0 | 1.534 · 8,2 | 1.868 · 8,4 |
| **A pavesas (`lw-100-pavx10-001`)** | **0,545** | **0,822** | **0,60** | 0,50 | 262 · 6,2 | 1.374 · 14,5 | 4.316 · 24,6 | 6.165 · 29,0 | 9.088 · 31,6 |
| B sin dosel (`lw-100-sin-dosel-001`) | 0,174 | 0,215 | 0,49 | 0,11 | 188 · 1,5 | 698 · 3,6 | 1.493 · 4,6 | 1.805 · 4,7 | 2.282 · 5,5 |

### 7.4 Veredicto (con el criterio de §7.2)

- **A, pavesas: explica el resto del déficit.** Sesgo 0,82 ≥ 0,5 con precisión 0,60 ≥ 0,5, y con la
  duración respaldada (03Z), no con la generosa. El frente pasa los 20 km y llega a 24,6 km a la
  hora 9 y 29 km a la 12: es el avance que vio VIIRS (22,6-27,5 km a las horas 10-11, §7.1). El
  Dice sube de 0,205 a 0,545, el mejor de todo el caso.
- **B, sin dosel: no alcanza.** Sesgo 0,22 < 0,3. El frente llega **menos** lejos que la base (5,5
  contra 8,4 km), porque sin dosel tampoco hay copa, y la copa es lo que hace correr al frente en TU5
  (§7.1). El freno no es el WAF bajo dosel.

Lectura:

- El déficit de Las Golondrinas se descompone así:
  - la entrada meteorológica (el GFS sin el viento prefrontal ni el aire seco) explica un factor
    ~10 del área;
  - las pavesas explican el factor ~4,7 que falta (de 1.868 a 9.088 ha), y el cruce de la franja de
    agua y del TL6 de lenga en altura (§6.4).
- No es un número calibrado. 10 % / 1 % es la variante fuerte del loop L, fijada antes de correr y no
  ajustada a este caso. Es una sola realización, con la semilla fija de ELMFIRE (2024). A las 24 h el
  frente se pasa del máximo de la cicatriz (31,6 contra 27,6 km): el área llega casi entera, pero no
  toda en su lugar (precisión 0,60, contra 0,69 de la base).
- **No reabre modelo-v0.** Con esta misma variante, Alerces 2023 y Epuyén se pasan (loop L), y acá
  hacen falta además el viento y la humedad medidos, que el GFS no tiene. Lo que sí cambia es la
  limitación declarada: en un evento de viento extremo, el mecanismo faltante del modelo-v0 son las
  **pavesas** (apagadas por diseño), no el dosel ni los combustibles. Las 605 viviendas siguen sin
  modelo y quedan como limitación aparte.

> **Adenda (2026-10-23, §10).** El déficit no "se reparte". La celda que faltaba, GFS con pavesas,
> da 231 ha y sesgo 0,022: las pavesas multiplican el área ×1,0 con el GFS y ×4,9 con lo observado.
> Los dos mecanismos son **necesarios a la vez**. La descomposición de arriba (×~10 por la
> meteorología y después ×4,7 por las pavesas) vale sólo en ese orden. Lo mismo registra
> `X-pavesas-calibracion.md` §1.2 con la iteración `calibracion-v6 / lw-100-pavx10-001`.

## 8. Enmienda (2026-10-23): forma contra velocidad sin pavesas

> Registrada antes de correr. La pregunta del autor: si la lengua de S3 va por el eje correcto,
> ¿dejándolo correr más dibujaría la cicatriz? No es una pregunta de predicción, sino de **forma**:
> separar dónde quema el modelo de cuán rápido lo hace. Es la métrica `area_igualada`
> (`app/validation/puntuacion.py`): la **forma** es el Dice en la hora `t*` en que el área predicha
> iguala la observada (10.622 ha), y `t*` comparado con la duración real mide la **velocidad**.
> En S3-12Z, `t*` no se alcanza en 24 h, así que su forma (0,344) todavía no es una forma.
> §7 ya mostró que las pavesas dan la velocidad que vio VIIRS. Esta corrida responde la pregunta
> complementaria: **sin pavesas**, ¿el modelo dibuja el incendio correcto aunque tarde, o el cruce
> de la franja de agua y la lenga también le cambia la forma?

**Corrida `synop-v6-s3-72h`.** Es S3-12Z prolongado a 72 h. Las horas 0–18 son las de S3-12Z,
byte a byte: el control es que el TOA de las primeras 18 h tiene que dar igual. Desde la hora 19
hasta la 72 se sostiene lo observado (29 kt, T 23,9 °C, HR 27,5 %) con la dirección **uniforme en 303°**,
la media circular del GFS en el foco durante las horas 0–12, cuando el fuego corría (289–321°). El
GFS de esas horas no existe en el caché y no hace falta, porque se pisa entero. **El clima de las
horas 13–72 es ficticio**: el SYNOP de las 12Z da calma y lluvia. La corrida mide forma, no
predicción, y no entra en ningún agregado.

**Duración real** que se usa para la velocidad: el incendio corrió desde las 18Z hasta algún momento
entre las 00Z ("605 viviendas en un par de horas") y las 12Z (lluvia), es decir **6–18 h, con 12 h
como valor central**.

Criterio (contra la cicatriz completa):

- **forma en `t*` ≥ 0,5**: el modelo dibuja el incendio correcto y el déficit es de **velocidad**.
  Se informa el factor `t*` / 12 h, con el rango `t*` / 18 h a `t*` / 6 h;
- **forma en `t*` < 0,3**: el freno también **deforma** el incendio, no sólo lo atrasa;
- entre 0,3 y 0,5: se informa sin veredicto;
- si `t*` no llega en 72 h, el déficit de velocidad es mayor que 4× (72/18) y se informa el Dice
  a las 72 h como cota de la forma.

### 8.1 Resultados

Corrido el 2026-10-23, después de §9 (la referencia es válida), con un solo ELMFIRE en el runner.
Contra la cicatriz completa (10.622 ha; excluido 0 ha).

**Control.** El TOA de las horas 0–18 coincide con el de S3-12Z: 45.304 celdas en las dos corridas,
ninguna distinta, y diferencia máxima de llegada de 0 s.

| hora | ha | sesgo | Dice | precisión | recall | frente (km) |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 448 | 0,04 | 0,046 | 0,57 | 0,02 | 5,3 |
| 12 | 1.964 | 0,18 | 0,208 | 0,67 | 0,12 | 8,6 |
| 18 | 4.077 | 0,38 | 0,317 | 0,57 | 0,22 | 12,0 |
| 24 | 7.412 | 0,70 | 0,401 | 0,49 | 0,34 | 17,2 |
| 30 | 12.754 | 1,20 | 0,394 | 0,36 | 0,43 | 20,2 |
| 36 | 16.324 | 1,54 | 0,375 | 0,31 | 0,48 | 22,1 |
| 42 | 20.136 | 1,90 | 0,347 | 0,26 | 0,50 | 24,2 |
| 48 | 23.994 | 2,26 | 0,337 | 0,24 | 0,55 | 25,0 |
| 54 | 27.508 | 2,59 | 0,356 | 0,25 | 0,64 | 27,8 |
| 60 | 31.703 | 2,98 | 0,359 | 0,24 | 0,72 | 35,9 |
| 66 | 35.132 | 3,31 | 0,350 | 0,23 | 0,75 | 37,0 |
| 72 | 38.259 | 3,60 | 0,349 | 0,22 | 0,80 | 37,0 |

**`t*` = 27,2 h y forma (Dice en `t*`) = 0,401.** En `t*` las áreas son iguales, así que precisión y
recall también son 0,40. `benchmark.py tabla` da lo mismo: forma 0,401 y `t*` 27 (redondeado a la
hora). `puntuacion.area_igualada` saca la semilla (1,6 ha) de las llegadas y este cálculo no, pero la
diferencia no se ve en tres decimales.

**Qué compone la forma en `t*`:**

| | |
|---|---|
| Recall por franja de distancia a los focos | 0–5 km 0,92 · 5–10 km 0,76 · 10–15 km 0,30 · **15–30 km 0,00** |
| Falsos positivos (6.365 ha) | 1.844 ha a ≤ 500 m del borde de la cicatriz; a > 500 m, **3.714 ha al sur del eje** (rumbo 114°) y 807 ha al norte; 0 ha más allá del extremo SE |
| En la estepa oficial que la máscara no ve (§9.2) | 664 ha |

### 8.2 Veredicto (con el criterio de §8)

**Entre 0,3 y 0,5: sin veredicto.** La forma en `t*` es 0,401. Como el criterio lo condiciona a una
forma ≥ 0,5, no se informa un factor de velocidad.

Lectura, que no cambia el veredicto:

- **Sin pavesas, el modelo no dibuja este incendio más lento: dibuja otro.** La forma 0,40 está hecha
  entera con los primeros 15 km. Más allá, recall 0. El modelo iguala el área ensanchándose alrededor
  del origen, sobre todo hacia el sur del eje, y no siguiendo el corredor. La cicatriz llega a 27,6 km;
  el frente pasa los 20 km recién a la hora 30, cuando el área ya es 1,2 veces la observada.
- **El Dice nunca supera 0,401** (hora 24). Después baja porque el área crece más rápido que lo
  acertado: a las 72 h, recall 0,80 con sesgo 3,6.
- Con pavesas y la duración respaldada (§7.3), el Dice a 24 h es 0,545, con precisión 0,60 y el
  frente a 24,6 km a la hora 9. Las pavesas no sólo aceleran: también **ponen el fuego en el
  corredor**. El cruce de la franja de agua y de la lenga en altura (§6.4) es lo que, sin pavesas,
  desvía el avance hacia los costados.
- **Salvedad.** Desde la hora 19 el viento es uniforme en 303° y el clima es ficticio (§8). Parte del
  ensanchamiento al sur puede venir de esa dirección fija. Pero la forma en `t*` se decide en las
  primeras 27 h, y las primeras 18 son las de S3-12Z.

## 9. Enmienda (2026-10-23): ¿la cicatriz mide este incendio?

> Sin ELMFIRE. El autor ve algo raro: ~10.600 ha que, según la cronología, ardieron en una noche.
> Hay tres hipótesis: (a) la máscara está sobredimensionada; (b) incluye otro incendio; (c) la
> ventana de 24 h es corta. Si (a) o (b) se confirmaban, las corridas de §8 y §10 no se hacían.
> Scripts de la sesión (no versionados): `lobulo.py`, `oficial.py`, `estepa.py`.

### 9.1 Fuentes

- **Perímetro oficial.** Informe de áreas quemadas MAyDS/SNMF, datos al 23-mar-2021
  (`informe_aq_rio_negro_chubut_07may2021.pdf`, p. 15 y 17). Las Golondrinas: 12.959 ha.
  El Boquete: 8.818 ha (4.511 en Bariloche, 2.518 en Ñorquinco y 1.789 en Cushamen). El polígono
  sale del Mapa 1 (Sentinel-2 del 21-mar más puntos de terreno). Se georreferenció con cinco
  localidades de OSM (El Bolsón, El Hoyo, Lago Puelo, El Maitén, Buenos Aires Chico) y la línea de
  42° S del límite provincial. Residuo: 54–128 m por punto. Se compara con ±300 m de tolerancia.
  El color del polígono extraído da 11.915 ha, un 8 % menos que el oficial: donde el relleno
  semitransparente cae sobre bosque quemado oscuro, no se distingue.
- **Fecha de quema por celda.** MODIS MCD64A1 (`BurnDate`, celdas de 463 m) de febrero a abril de
  2021, bajado de Earth Engine. Se usó el 10-mar como día 69.
- **Detecciones.** El FIRMS del caché (`las-golondrinas-2021_2021-03-06_2021-03-20.csv`): VIIRS
  SNPP y NOAA-20, a ≤ 375 m de la cicatriz.
- **Máscara.** El run `event-filter-001`, con sus tiles PRE/POST, `candidatos_cambio`,
  `otro_incendio_probable`, `componentes.csv` y `hotspots.csv`.

### 9.2 (a) ¿Sobredimensionada? No; es al revés en la estepa

| | ha |
|---|---:|
| Superficie oficial (SNMF, 23-mar) | 12.959 |
| Máscara del run / en la grilla | 10.656 / 10.622 |
| Oficial fuera de la cicatriz (±300 m), a 25–40 km de los focos | 1.899 |
| Oficial fuera de la cicatriz (±300 m), a 0–25 km | 347 |
| Cicatriz fuera del oficial (±300 m), a ≥ 20 km | 123 |
| Cicatriz fuera del oficial (±300 m), a 0–20 km | 2.286 (no interpretable: ahí falla la extracción del relleno) |

- **La máscara es más chica que el oficial, no más grande.** Le faltan unas 2.300 ha. Casi todas
  están en el extremo este, en la estepa entre el lóbulo de Cerro Coihue y la Ruta 40.
- **La causa es el método de la máscara, no un error del run.** En esas 1.899 ha el NBR previo
  tiene mediana −0,07 y el 93 % está por debajo de `pre_nbr_min` = 0,15. El dNBR tiene mediana
  0,02: pasto de estepa que, a los 11+ días de la ventana POST, no deja señal. Sólo el 4 % es
  candidato a cambio. Es el mismo sesgo que El Turbio (sotobosque bajo el umbral, RESULTADOS-CSS-BAP
  §3.2). No es una decisión de este caso y no se corrige acá.
- **Lo que está, ardió.** El 89 % de los píxeles de la cicatriz cae en celdas MODIS quemadas en marzo
  (87 %, 91 % y 92 % a 0–10, 10–20 y 20–30 km). El 11 % restante (1.127 ha) es el borde que no llena
  una celda de 463 m: no se concentra en ningún sector.
- `cambio_no_confirmado`: 44,7 ha en cuatro componentes, todos fuera del objetivo y ninguno de más
  de 15 ha. Observación válida ≥ 99,25 % en cada tile. No aparece ningún bloque con cambio sin fuego
  (cosecha u otro disturbio): la confirmación MODIS es pareja en toda la cicatriz.

### 9.3 (b) ¿Otro incendio dentro? No se confirma

El candidato era el lóbulo sureste: 2.462 ha a ≥ 20 km de los focos, al pie de Cerro Coihue.

| Prueba | Resultado |
|---|---|
| Perímetro oficial | 2.339 de 2.462 ha (95 %) dentro del polígono de Las Golondrinas (±300 m). El Boquete es otro polígono, al NE (Cerro de La Mujer–El Maitén), a ≥ 6 km del lóbulo |
| FIRMS antes de la ignición | 12 pasadas del 7-mar 17:57Z al 9-mar 06:42Z, con 6–51 píxeles cada una, **todos** a latitud ≥ −42,004 (El Boquete). Ninguno a ≤ 375 m de la cicatriz |
| Primera detección en el lóbulo | 10-mar 04:43Z (NOAA-20, 15 px, 23,1–27,5 km) y 05:32Z (SNPP, 35 px, 22,6–27,2 km): horas 10,7 y 11,5 |
| Fecha MODIS en el lóbulo (22–30 km) | 83 % el 10-mar, como el cuerpo principal (81 % a 0–10 km). Tres celdas (~100 ha) el 8–9-mar, con incertidumbre de ±1 día |
| Quema entre El Boquete y el lóbulo | Ninguna celda MODIS quemada en la franja −42,04 a −42,09 / −71,30 a −71,15 |
| Conectividad (4-vecinos, dentro de la cicatriz) | 2.428 de 2.462 ha unidas a los focos; con dNBR ≥ 0,3: 2.256 de 2.286; con dNBR ≥ 0,44: 1.946 de 2.009. Recién se corta con dNBR ≥ 0,66 |
| PRE de febrero y POST | Lóbulo con vegetación previa (NBR previo, mediana 0,45) y severidad alta (dNBR, mediana 0,73; ≥ 0,3 en el 93 %). Las 13 celdas MODIS de febrero quedan al NO, fuera de la cicatriz |
| Crónicas | ANB, 9-mar: el incendio "cerca de El Maitén" (El Boquete) llegó casi al aeródromo y "avanzaba" hacia Buenos Aires Chico, a ~4 km del extremo del lóbulo. Ninguna crónica nombra un incendio en Cerro Coihue, El Coihue ni Cerro Pirque en esas fechas. La pericia da dos focos en la caja (§7.1) |

Lo único que la evidencia no excluye es un salto de pavesas de ≥ 6 km desde El Boquete hacia el
sur. Ninguna fuente lo documenta, el SNMF atribuye el lóbulo a Las Golondrinas y el lóbulo está
unido por tierra al cuerpo principal con severidad alta. Se descarta como hipótesis de trabajo.

**Corrección a §7.1.** El incendio activo en FIRMS desde el 7-mar al NE (`component-001`,
3.255 ha, `otro_incendio_probable`) es **El Boquete**, no Cuesta del Ternero. Lo dicen el Mapa 1
del SNMF (polígono entre Cerro de La Mujer y El Maitén) y su fecha de inicio (7-mar; la primera
detección del caché es del 7-mar a las 17:57Z, en −71,32 / −41,98). Cuesta del Ternero ardió el
24-ene, más al norte, y la ventana PRE de febrero lo deja afuera. Las conclusiones de §7.1 no
cambian: el incendio vecino queda a ≥ 3,5 km de la cicatriz. Lo mismo vale para la mención en el
README de `mask-dataset-gen`, que no se edita desde acá.

### 9.4 (c) ¿Ventana corta? No

| Fuente | Qué dice del fin del crecimiento |
|---|---|
| MODIS (píxeles de la cicatriz) | 8.180 ha (77 %) el 10-mar; 865 ha (8 %) el 11-mar, con incertidumbre de ±3 días (el 10-mar estuvo nublado); 369 ha (3,5 %) del 12 al 22-mar, dispersas; 102 ha el 8–9-mar |
| VIIRS | Las detecciones lejanas son de las horas 10,7–11,5. En las pasadas diurnas del 10-mar no hay **ninguna** detección en toda la caja (8/8 nubes y 12 mm en el SYNOP de 12Z). Del 12 al 20-mar hay 1–9 píxeles por pasada, a 6,5–13 km y dentro de la cicatriz: rescoldo y borde (el clúster `thermal-004`, a 12 km, del 14 al 20-mar) |
| Conteo VIIRS del SNMF (los dos incendios) | 541 focos el 9-mar y 415 el 10-mar; después, 3, 2, 14, 4, 1 y 1 |
| Cronología | 605 viviendas "en un par de horas" (§0); calma y lluvia a las 12Z |
| Área FIRMS del README | 162 ha el 9-mar y 1.355 el 10-mar: no sirve, porque el satélite estaba ciego |

Entre el 85 % y el 90 % de la cicatriz ardió antes de la tarde del 10-mar. A lo sumo un 4 % se
puede atribuir a crecimiento posterior. La ventana de 24 h (hasta el 10-mar a las 18Z) cubre el
evento. Esto coincide con §6, que descartó la duración con el modelo.

### 9.5 Veredicto

**La referencia es válida.** (a) no se confirma: la máscara es ~2.300 ha más chica que el oficial,
por la estepa que el umbral de NBR previo no ve. (b) no se confirma: el lóbulo sureste es de este
incendio. (c) se descarta: el incendio ardió en la primera noche. El déficit del modelo-v0 es real
y no un artefacto de la referencia. Las partes de §8 y §10 se corren.

Un efecto lateral para leer las corridas que llegan lejos: si el modelo quema la estepa al este del
lóbulo, esas celdas cuentan como falsos positivos, aunque ardieron. En la práctica pesa poco. La
corrida con pavesas de §7.3 pone ahí 76 de sus 3.455 ha de falsos positivos, y S3-72h en `t*`
pone 664 de 6.365 (§8.1 y §10).

### 9.6 Memo de decisión para el autor

Regla de método: un caso se saca o se corrige **por la validez de la referencia o por un alcance
declarado, nunca por su resultado**. La partición se fijó antes del primer barrido
(RESULTADOS-CSS-BAP §3.2), con Las Golondrinas en calibración como "viento extremo", y la regla
de parada del modelo-v0 rige.

| Opción | Qué implica | Documentos que habría que tocar |
|---|---|---|
| **1. Dejarlo en calibración como caso límite declarado y reportar la media con y sin él** (situación actual) | Nada cambia: 0,439 con él y 0,510 sin él, exento de la restricción de alarmas (decisión 12). La nota G pasa a respaldar que la referencia es válida | Ninguno es obligatorio. Opcional: una línea en RIESGOS §3 y en la fila de MODELO-V0 que remita a §9 |
| 2. Sacarlo de la media como "fuera de alcance: evento dominado por pavesas" y reportarlo aparte | "Dominado por pavesas" es una **conclusión de §7**, sacada del resultado del modelo. Declarar ese alcance ahora sería sacarlo por su resultado. Para que sea un alcance, haría falta un criterio previo y sin el modelo (por ejemplo, viento observado ≥ X durante la corrida principal) aplicado a todos los casos, incluida la prueba. También reabre la selección de receta: con otro conjunto de calibración, la regla de parada habría que volver a evaluarla, aunque Las Golondrinas da ~0 con todas las recetas | `benchmarks/particion.json` (sacarlo de `calibracion.gfs`), MODELO-V0 (tabla y media), ESTADO-RESEARCH §3 (tabla de evidencia congelada), RIESGOS §3 |
| 3. Corregir la referencia (por ejemplo, recortar el lóbulo sureste) | **No corresponde.** Ni (a) ni (b) se confirmaron. La única corrección que respalda la evidencia va al revés: sumar ~1.900 ha de estepa, lo que empeora apenas el caso. Además es una propiedad del método (`pre_nbr_min`) y habría que aplicarla en `mask-dataset-gen` a todos los incendios con estepa, no sólo a éste | `mask-dataset-gen` (run nuevo), re-empaquetado del caso, `particion.json` |

**Recomendación: la opción 1.** La referencia pasó las tres pruebas, así que no hay motivo de
validez para tocarla. El único alcance declarado antes del barrido es "viento extremo", y ya está
cubierto por `limites`. Sacarlo de la media sería la decisión por el resultado que la regla
prohíbe. La media con y sin el caso ya informa lo que el lector necesita.

## 10. Enmienda (2026-10-23): la celda que falta del 2×2 de pavesas

> Diseño y criterio registrados antes de correr.

§7.4 dice que el déficit "se reparte": un factor ~10 por el GFS y ~4,7 por las pavesas. Eso supone
efectos separables, y falta la celda **GFS con pavesas**. Un indicio en contra: en el loop L,
`calibracion-v5 / lw100-cbh050-pavx10-001` dio Dice 0,020 y sesgo 0,026, casi lo mismo que sin
pavesas. Pero era v5 y con CBH × 0,5, así que no es la celda exacta.

**Corrida.** `synop-v6-s0` (= `calibracion-v6` byte a byte, §2) × `lw-100-pavx10-001`, contra la
cicatriz completa. En `benchmarks/iteraciones/las-golondrinas-2021/calibracion-v6/` ya existe una
iteración `lw-100-pavx10-001` (de otra sesión, 2026-10-23). Tiene los mismos insumos y no se miró
antes de registrar esto. Se usa como **control de reproducibilidad**: la celda nueva tiene que dar
el mismo TOA. Si no coincide, se informa y no se interpreta la celda.

Criterio:

- **sesgo ≥ 0,5 con precisión ≥ 0,5**: las pavesas solas alcanzan y la entrada meteorológica no es
  necesaria. Cambia la lectura de §3 y §7;
- **sesgo < 0,1**: los dos mecanismos son **necesarios a la vez**, y §7.4 tiene que dejar de decir
  que "se reparten";
- en el medio, sin veredicto.

Se informa el 2×2 completo, {GFS, observado hasta 03Z} × {sin, con pavesas}: área, Dice, sesgo,
precisión y alcance del frente a las 9 y a las 24 h. Las otras tres celdas ya están corridas:
`synop-v6-s0 / lw-100-001`, `synop-v6-s3-03z / lw-100-001` y `synop-v6-s3-03z / lw-100-pavx10-001`.
Como dato aparte, que no entra en el criterio, se informa cuánto de lo predicho cae en la estepa
oficial que la máscara no ve (§9.2).

### 10.1 Resultados

Corrido el 2026-10-23, después de la de §8. Contra la cicatriz completa. El área es la del TOA a
24 h (incluye la semilla), como en §7.3. Dice, sesgo, precisión y recall son los de `metricas.json`
(`cicatriz` → `acumulado`).

**Control de reproducibilidad.** `synop-v6-s0 / lw-100-pavx10-001` y la iteración previa
`calibracion-v6 / lw-100-pavx10-001` dan el mismo TOA: ninguna celda distinta y diferencia de
llegada de 0 s. Con pavesas y la semilla fija, ELMFIRE es determinista.

| meteorología | pavesas | ha a 24 h | Dice | sesgo | precisión | recall | frente a 9 h | frente a 24 h |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GFS (`synop-v6-s0`) | no | 226 | 0,012 | 0,021 | 0,28 | 0,01 | 1,4 km | 1,6 km |
| GFS (`synop-v6-s0`) | **sí** | **231** | **0,012** | **0,022** | 0,29 | 0,01 | 1,4 km | 1,6 km |
| observada hasta 03Z (`synop-v6-s3-03z`) | no | 1.868 | 0,205 | 0,176 | 0,69 | 0,12 | 8,0 km | 8,4 km |
| observada hasta 03Z (`synop-v6-s3-03z`) | sí | 9.088 | 0,545 | 0,822 | 0,60 | 0,50 | 24,6 km | 31,6 km |

Factores del área a 24 h:

| | sin pavesas → con pavesas |
|---|---:|
| con el GFS | ×1,0 |
| con lo observado | ×4,9 |
| **GFS sin pavesas → observado con pavesas** | **×40** |
| si los efectos fueran separables (×8,3 del clima × ×1,0 de las pavesas con el GFS) | ×8,5 |

Lo predicho en la estepa oficial que la máscara no ve (§9.2): 10, 10, 11 y 76 ha. No cambia
ninguna precisión en más de 0,01.

### 10.2 Veredicto (con el criterio de §10)

**Sesgo 0,022 < 0,1: los dos mecanismos son necesarios a la vez.** Con el GFS, las pavesas no
cambian nada: mismo frente, +5 ha. Con la meteorología observada, multiplican el área ×4,9. Hay
interacción, no suma: el efecto conjunto (×40) es casi cinco veces el que darían los efectos por
separado (×8,5). §7.4 recibió una adenda y conserva su texto.

Hipótesis, **no verificada acá**: la variante fuerte lanza pavesas desde el 10 % de las celdas en
copa y el 1 % en superficie. Con el GFS el fuego no pasa de 1,6 km: apenas toca el TU5 donde, con
lo observado, se encendía la copa (§7.1). Así casi no hay celdas que lancen. El viento y el aire seco hacen falta para que haya fuego de
copa que lance pavesas, y las pavesas hacen falta para cruzar el agua y la lenga. Coincide con
`X-pavesas-calibracion.md` §1.2. Allí, además, `lw-100-pavx10-001` no pasa la puerta del modelo:
media 0,451 < 0,459 y tres alarmas nuevas (Alerces 2023 2,42; Epuyén 2,92; Alerces 2016 2,42).
