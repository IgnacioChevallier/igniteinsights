# Humedad y altura en la lenga: propuesta

> 2026-10-11. Investigación sin corridas de ELMFIRE. No modifica `app/`, recetas ni casos, y no
> reabre modelo-v0. Responde a `RIESGOS_Y_SUPOSICIONES.md` §4 y al loop K de
> `AUDITORIA-FISICA.md`.
>
> **Estado (2026-10-12): cerrado como límite**, por decisión del autor. Lenga achaparrada → SH8
> se mantiene, con la limitación declarada en el crosswalk (§5.5).

## 0. Resumen

**Pregunta.** En Alerces 2015 (caso de prueba) el modelo quema el cinturón de lenga de altura,
que no ardió: es el 56 % del falso positivo. ¿Arde poco porque su combustible está más húmedo de lo
que predicen las correcciones del aire, o porque es menos inflamable que TL6/SH8?

**Respuesta corta.** La evidencia no alcanza para una regla nueva. **Se recomienda cerrar el
punto como límite.**

- **No hay mediciones de humedad de la hojarasca de lenga.** Ninguna fuente mide la humedad del
  combustible fino muerto bajo *N. pumilio* por altura, orientación o cobertura. Lo medido es el
  aire bajo el dosel (Paritsis et al. 2015) y palitos de madera en bosque frente a matorral (Barberá
  et al. 2023, sin acceso al texto completo). Llevado a humedad de equilibrio, el microclima medido
  suma ~1 pp al m1. Para frenar el TL6 a la mitad harían falta ~20 %, y para apagarlo, 25 %.
- **Lo que sí está medido es la probabilidad de quema.** Baja con la altura **dentro de cada tipo
  de vegetación**: es un efecto de la altura, no de la lenga. A igualdad de condiciones, la lenga
  arde **más** que el bosque húmedo de coihue, igual que el pastizal y menos que el matorral
  (Barberá et al. 2025; Mermoz et al. 2005).
- **Análisis regional fuera del benchmark (§3).** 30 eventos MCD64A1 de 2014–2026 en la
  cordillera de Chubut y Río Negro, sin los 11 del benchmark.
  - A igualdad de evento y banda de altura, el **bosque de lenga arde 0,72× lo que sus vecinas**
    (IC95 0,58–0,85). Arde **igual que el coihue/ciprés** (0,97) y menos que el matorral (0,70) y
    la estepa (0,74). La razón **no empeora con la altura** (0,61 a 800–1.000 m, 0,74 sobre 1.200 m).
  - Lo que cae con la altura cae en todas las clases: dentro de la lenga, de 0,51 a 1.000–1.200 m
    a 0,14 sobre 1.600 m; en la estepa altoandina, de 0,52 a 0,15.
  - La **lenga achaparrada** arde 0,41× sus vecinas (IC95 0,27–0,50).
- **En la calibración, la lenga de altura sí ardió.** En los seis incendios de calibración sin el
  caso límite, el TL6 sobre 1.000 m ardió 2.064 ha y el modelo predice 2.165 (sesgo ~1,05). Una
  regla que frene la lenga de altura para arreglar Alerces 2015 sacaría aciertos en Alerces 2024
  y Cholila.

**Decisión: cerrar el punto como límite, sin regla nueva.**

- **Humedad.** No hay un dato medido con el cual fijar un ajuste de humedad bajo dosel de lenga.
  Las correcciones físicas del aire ya se midieron y no alcanzan.
- **Combustible.** El bosque de lenga (TL6) no tiene sesgo en la calibración (0,99) y arde, en la
  región, como el coihue.
- **Lenga achaparrada.** Es la única clase con una señal propia: arde la mitad que sus vecinas en
  la región y el modelo la sobrequema en calibración (sesgo 1,73). Pero un modelo más lento para
  ella **ya se midió** en el loop L (`lw100-x-lach3-001`, SH3) y se rechazó: Cholila cae de 0,280
  a 0,213. Probar ahora TL6, que está entre SH3 y SH8, sería probar otro código en la misma
  dirección contra los mismos siete incendios.

En §4 queda escrito qué dato reabriría el punto y con qué protocolo medirlo.

## 1. Qué hace hoy el modelo

- Bosque de lenga (`TF Le`) → **TL6** (186): hojarasca latifoliada, 1 h 0,110 lb/ft², lecho de
  0,3 pies, Mx 25 %, sin carga viva. Lenga achaparrada (`OFL Le`) → **SH8** (148), por analogía
  con el ñire bajo (`fuels_builder.py`; crosswalk §5.1 y §5.5).
- El m1 es la humedad de equilibrio de Nelson con la T y la HR de ERA5 o GFS en una celda de
  0,25°. En Alerces 2015 vale 5,1 % desde 500 hasta 1.500 m (loop K).
- Ya se midieron dos correcciones de libro (`app/validation/humedad.py`):
  - `altura-001`: gradiente de −6,5 °C/km con el punto de rocío conservado;
  - `fosberg-001`: tablas de Rothermel (1983) / NFDRS / BehavePlus con sombra para CC ≥ 50 %.

  Ninguna movió el Dice más de ±0,01. En Alerces 2015 el falso positivo pasa de 818 a 817 ha.
- Con `diag-lw100-lenga-nb-001` (TL6 y SH8 no quemables) la subida se frena: 674 ha, Dice 0,323,
  sesgo 0,59. Es una cota, no una corrección.

**Cuánta humedad haría falta.** En Rothermel, el TL6 sin carga viva se frena por el
amortiguamiento de humedad η_M(m1/Mx) y por el calor de preignición Q_ig = 250 + 1.116·m1. La
velocidad relativa a la de m1 = 5,1 % es:

| m1 | 6 % | 9 % | 12 % | 15 % | 20 % | 22 % | 25 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Velocidad relativa | 0,92 | 0,76 | 0,67 | 0,59 | 0,39 | 0,26 | 0 |

Lo que pueden agregar las dos correcciones es una estimación de sus fórmulas, no algo medido en
las iteraciones:

- `altura-001`: con 22 °C y 30 % de HR a la altura de la celda, subir 500 m da −3,3 °C y una HR de
  37 %, o sea +1,2 pp de humedad de equilibrio (Simard).
- `fosberg-001`: la corrección de sombra de sus tablas suma +3–5 pp sobre la expuesta.

Eso lleva el m1 de la montaña a ~6–9 %, un frenado de 8–24 % que no alcanza para un fuego que sube
por pendiente. Es coherente con que el falso positivo de Alerces 2015 no se haya movido. Para que la humedad explique la lenga sin quemar, la
hojarasca tendría que estar en **≥ 20 %** el día del incendio.

## 2. Bibliografía

Para cada fuente: qué midió, dónde, cuándo y con qué valores. **M** marca una medición propia de
la fuente. **S** marca una síntesis o interpretación: dice algo sobre la lenga que la fuente no
midió.

### 2.1 Humedad y microclima bajo *Nothofagus*

| Fuente | Tipo | Qué, dónde, cuándo | Valores |
|---|---|---|---|
| Paritsis, Veblen y Holz (2015) | M | Aire a 1,0–1,5 m (iButton DS1923, cada 4 h) en lenga alta sin quemar (UnFo) y en lenga quemada convertida en matorral (BuFo/Sh), en 8 sitios de 13 incendios de 1983–1998. Chubut, 42°50'–44°20' S, 830–1.240 m. Del 25-ene al 25-mar de 2012 | 10 % de días más cálidos: 20,4 ± 0,5 °C en lenga, 24,4–24,9 en matorral. 10 % más secos: HR 32,3 ± 1,9 % en lenga, 25,2–26,0 % en matorral. Tmax media 22,2 contra 27,4–27,5 °C. HRmin 25,3 contra 18,4–20,9 %. Días con > 25 °C y HR < 25 %: **0 en lenga**, 1,1 por verano en matorral. **No midió la humedad del combustible**: los autores la piden como trabajo futuro |
| Barberá, Paritsis, Ammassari, Morales y Kitzberger (2023) | M | Humedad de combustible muerto (palitos de madera) y de hojas vivas, con microclima del sotobosque, en 10 sitios de bosque y matorral del NO patagónico | Según el resumen y las citas: los bosques "pirófobos" tienen un sotobosque más húmedo y fresco y **más humedad de combustible muerto** que los matorrales. **No pude leer el texto completo** (Elsevier, sin copia abierta): no tengo los valores, ni las especies de bosque, ni las alturas |
| Fierke et al. (2025) | M | Microclima bajo dosel a tres alturas, red de sensores 2022–2024 en el valle del río Manso (Río Negro). Modelo de bosque aleatorio a 30 m, con reducción de escala de ERA5 | Tmax a 2 m: R² 0,88, RMSE 1,5 °C. Tmin: R² 0,73, RMSE 1,8 °C. Muestra que el microclima bajo dosel se aparta de ERA5 y se puede modelar. No mide combustible |
| Fierke et al. (2026) | M | Pares de micrositios (bosque/matorral, baja/alta altura, ladera N/S), verano, cada 15 min, en el río Manso | Las diferencias por altura de la vegetación y por altura sobre el nivel del mar son mayores y más constantes que las de orientación, y **crecen en los días más cálidos**. Sólo el resumen; no mide combustible |
| Bianchi y Defossé (2014) | M | Probabilidad de ignición en laboratorio del combustible fino muerto superficial de **ciprés y ñire**, Esquel | Umbral de 21,5 % (ciprés) y 25,0 % (ñire), equivalente a FFMC 85. **No incluye lenga** |
| Bianchi y Defossé (2015) | M | Humedad foliar viva de especies del bosque andino | 110–220 % en temporada. **Lenga no medida** (ya citado en el crosswalk) |

**Conversión del microclima medido.** Con la ecuación de Simard (1968), base de NFDRS, la humedad
de equilibrio con la Tmax/HRmin media de Paritsis et al. es de **5,2 % en la lenga y 4,0–4,4 % en
el matorral**: **+0,8–1,2 pp**. La tabla A de Fosberg da +1–2 pp. Es del mismo orden que lo que ya
agregan `altura-001` y `fosberg-001`. El aire bajo el dosel de lenga no explica una hojarasca al
20–25 %. Si la hojarasca está así de húmeda, es por algo que estos modelos no tienen, como el agua
del suelo, el rocío o el retraso de la capa compacta, y eso nadie lo midió en lenga.

### 2.2 Inflamabilidad y probabilidad de quema de la lenga frente a otros tipos

| Fuente | Tipo | Qué, dónde, cuándo | Resultado |
|---|---|---|---|
| Mermoz, Kitzberger y Veblen (2005) | M | Incendios 1985–1999 (Landsat) y 1950–1999 (fotos aéreas) en el norte de la Patagonia, por vegetación previa y factores abióticos | El matorral alto se quema proporcionalmente más que los bosques vecinos de coihue y lenga. La extensión del fuego es máxima a altura y precipitación intermedias; arriba la limita "la desecación infrecuente o insuficiente del combustible". Los parches de bosque subalpino "suelen funcionar como cortafuegos naturales, salvo bajo el tiempo de fuego más severo" |
| Barberá, Cingolani, Tiribelli, Mermoz, Morales y Kitzberger (2025)ᵃ | M | 234 incendios ≥ 10 ha, julio 1998 – junio 2022, mapeados a 30 m con Landsat. Región Altoandina y Subantártica argentina, 39,0–44,5° S, 2,92 Mha. Modelos de probabilidad de quema con y sin el tipo de vegetación | La probabilidad de quema **baja con la altura y sube con la pendiente, cualquiera sea el tipo de vegetación**. Sin controlar el ambiente, el bosque subalpino de lenga (sobre ~1.200 m) es el que menos arde. **A igualdad de condiciones, la lenga arde más que el bosque húmedo de coihue, igual que el pastizal y menos que el matorral**. Controlando pendiente y NDVI, la altura tiene un efecto grande dentro de la lenga. Atribuyen el efecto de la altura a la temperatura (combustible más húmedo) y no al cambio de vegetación. **Su registro incluye los incendios del benchmark**: no es independiente de ellos como dato, pero sí como análisis |
| Paritsis et al. (2015) | M | Mismos sitios: volumen de combustible fino en tres estratos | En la lenga sin quemar, el combustible fino es verticalmente discontinuo y escaso cerca del suelo; en el matorral, continuo |
| Tiribelli, Kitzberger y Morales (2018) | M | Combustible fino (método del poste) en 18 matorrales (1–115 años) y 18 bosques (7–216 años) del NO patagónico | En el bosque, la carga sube después del fuego, tiene un pico a los ~30–50 años y baja cuando dominan los árboles altos. La densidad del combustible fino del bosque baja con la edad |
| Blackhall et al. (2017) | M | Clausuras de largo plazo después del incendio de 1999: lenga subalpina contra matorral alto de ñire | A los 16 años, el sitio que era matorral tiene más combustible fino total, más continuidad vertical y horizontal y más temperatura en la combustión de tejidos que el que era bosque de lenga |
| Tiribelli, Paritsis, Barberá y Kitzberger (2024) | M | Severidad de incendios en el gradiente de productividad del NO patagónico | La severidad baja sólo en el 8 % del área quemada: en veranos frescos y húmedos, o en ambientes productivos con combustible discontinuo y húmedo |
| Kitzberger, Raffaele, Heinemann y Mazzarino (2005) | M | Lenga subalpina en Challhuaco (41°13' S), después del incendio de 1996 | Mide regeneración, no inflamabilidad. Después del fuego, la radiación sube y el suelo se seca |
| Veblen et al. (2008); Kitzberger et al. (2016) | S | Síntesis regionales | La lenga es un bosque "pirófobo" con fuegos infrecuentes y de reemplazo. Antes del siglo XX, los grandes fuegos severos también la afectaban |
| Mundo et al. (2017) | M | Cicatrices de fuego en lenga, 16 sitios entre 44° y 50° S | Los fuegos en lenga coinciden con sequías extremas y SAM positivo: la limitación es la humedad del año, no la carga |

ᵃ Las comparaciones entre tipos salen del preprint (Research Square, 2024), leído completo. El
resumen publicado en Fire Ecology dice "forests" donde el preprint dice "wet forests". No pude
leer el texto publicado para confirmar que la figura 6C no cambió.

**No hay ensayos de inflamabilidad de hojarasca de lenga**, ni en el laboratorio ni en el campo
(ignición, velocidad o carga del lecho). Tampoco hay un modelo de combustible medido para el
bosque de lenga ni para la lenga achaparrada: el crosswalk ya lo declara como pérdida (§5.5,
sensibilidad S1 y S2).

### 2.3 Qué dice la bibliografía sobre la pregunta central

1. **Humedad.** Está medido que el aire bajo la lenga es más fresco y húmedo que en el matorral, y
   que los palitos de bosque están más húmedos que los de matorral. No hay ningún número de la
   hojarasca de lenga, ni por altura ni por cobertura. Lo que sí se puede convertir (el aire) da
   ~1 pp, lejos de los ~20 % necesarios.
2. **Inflamabilidad.** Está medido que la lenga tiene menos combustible fino cerca del suelo y
   menos continuidad que el matorral. Pero a igualdad de condiciones **no es la menos inflamable**:
   el coihue arde menos, y el modelo le asigna TU5, más rápido que TL6. Bajar la lenga a un modelo
   más lento que el del coihue iría contra la única comparación controlada que existe.
3. **Altura.** El efecto medido es de la altura, común a todos los tipos. Es lo que intentaron
   `altura-001` y `fosberg-001`, sin efecto, porque el aire sólo explica una parte chica.

## 3. Evidencia regional fuera del benchmark

Script: `scripts/lenga_altura_regional.py` (sólo lectura). Se corre con
`uv run --with scipy --with earthengine-api python scripts/lenga_altura_regional.py`. La caché y
la tabla larga quedan en `data/validation/lenga_altura/`, ignorado por git.

### 3.1 Diseño, fijado antes de mirar los resultados

- **Dominio.** Toda la cobertura de CCS-BAP de Chubut y Río Negro (165 × 606 km), en una grilla
  UTM 19S de 90 m. Es la cordillera argentina entre ~40,6° y ~45,9° S.
- **Vegetación anterior al fuego.**
  - CCS-BAP 2013 para las temporadas 2014–2017 y CCS-BAP 2017 para las 2018–2026. La temporada
    va de julio a junio y se rotula por su junio.
  - Las temporadas 2001–2013 quedan fuera, aunque el pedido decía 2001–2025: el mapa 2013 ve esas
    cicatrices como remanente, y la lenga quemada no figuraría como lenga. Eso sesgaría el
    resultado justo en la dirección de la hipótesis.
  - Las clases son las de CCS-BAP: bosque de lenga (`TF Le`), lenga achaparrada (`OFL Le`),
    coihue/ciprés/mixto, ñire (TF y OFL), otros matorrales OFL, estepa (`OT Herb-Subarb`),
    remanente y otras quemables. Lo no quemable según el crosswalk de modelo-v0 queda fuera.
- **Fuego.** MODIS MCD64A1 v6.1 (celdas de ~463 m), `BurnDate > 0` en la temporada.
- **Exclusión.** Sale entero todo evento cuya envolvente toca la cicatriz dNBR de alguno de los 11
  incendios del benchmark (`benchmarks/particion.json`, el run vigente de cada caso) o queda a
  menos de 2 km de ella. Eso son 336.330 ha de exclusión.
- **Exposición.**
  - La envolvente de un evento es todo lo que está a ≤ 1 km de lo quemado en la temporada. Las
    envolventes conexas son los eventos, y los que tienen < 100 ha quemadas se descartan.
  - Dentro de una envolvente, la lenga y sus vecinas tuvieron la misma ignición, el mismo tiempo y
    el mismo combate. La comparación es entre la fracción quemada de la lenga y la de las otras
    clases quemables **del mismo evento y la misma banda de 200 m** del DEM COP30.
  - Sólo cuentan los estratos con ≥ 25 ha de cada lado. El intervalo sale de un bootstrap por
    eventos (2.000 réplicas).
- **Control a 30 m (previsto, sin resultado).** Iban a entrar las cicatrices dNBR de tres incendios
  de 2015 que no están en el benchmark: Cerro Plataforma, Currumahuida y Desemboque. **Los tres
  quedaron excluidos** porque su envolvente toca Cholila 2015, Epuyén 2019/2025 o Las Golondrinas.
  No hay control a 30 m.

### 3.2 Fracción quemada por clase y altura

Quedan 30 eventos, con 70.556 ha quemadas dentro de CCS-BAP. Las temporadas con más área son
2015, 2021, 2025 y 2026.

| Clase \ banda (m, desde) | 400 | 600 | 800 | 1.000 | 1.200 | 1.400 | 1.600 | 1.800 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Bosque de lenga (TF Le) | — | 0,26 | 0,35 | **0,51** | 0,39 | 0,22 | 0,14 | — |
| Lenga achaparrada (OFL Le) | — | — | (0,47) | 0,44 | 0,24 | 0,20 | 0,20 | — |
| Coihue/ciprés/mixto | 0,41 | 0,49 | 0,54 | 0,60 | 0,49 | (0,62) | — | — |
| Ñire (TF y OFL) | 0,32 | 0,46 | 0,59 | 0,56 | 0,58 | (0,46) | — | — |
| Matorral (otras OFL) | 0,38 | 0,53 | 0,61 | 0,70 | 0,71 | (0,62) | — | — |
| Estepa / altoandina | 0,29 | 0,43 | 0,49 | 0,52 | 0,31 | 0,21 | 0,15 | 0,08 |

Expuesto en lenga: 987, 1.934, 4.445, 5.451, 3.263 y 126 ha desde 600 m. En lenga achaparrada:
15, 178, 678, 1.901 y 586 ha desde 800 m. Entre paréntesis, menos de 100 ha expuestas.

### 3.3 Contraste dentro del evento

| Lenga contra… | Eventos | Estratos | fq lenga | fq vecinas | Razón [IC95] |
|---|---:|---:|---:|---:|---|
| **Bosque de lenga** contra todas las vecinas | 18 | 48 | 0,380 | 0,530 | **0,72** [0,58–0,85] |
| … en 800–1.000 m | 11 | 11 | 0,344 | 0,567 | 0,61 [0,31–0,84] |
| … en 1.000–1.200 m | 12 | 12 | 0,530 | 0,607 | 0,87 [0,57–1,12] |
| … en 1.200–1.400 m | 10 | 10 | 0,387 | 0,529 | 0,73 [0,64–0,84] |
| … en 1.400–1.600 m | 6 | 6 | 0,235 | 0,349 | 0,67 [0,58–1,20] |
| … sólo contra coihue/ciprés/mixto | 11 | 18 | 0,518 | 0,537 | 0,97 |
| … sólo contra ñire | 16 | 30 | 0,450 | 0,518 | 0,87 |
| … sólo contra otros matorrales | 15 | 30 | 0,421 | 0,599 | 0,70 |
| … sólo contra estepa/altoandina | 15 | 34 | 0,383 | 0,515 | 0,74 |
| **Lenga achaparrada** contra todas las vecinas | 10 | 21 | 0,225 | 0,548 | **0,41** [0,27–0,50] |
| … en 1.200–1.400 m | 9 | 9 | 0,247 | 0,540 | 0,46 [0,23–0,64] |
| … sólo contra ñire | 4 | 5 | 0,477 | 0,678 | 0,70 |
| … sólo contra estepa/altoandina | 9 | 19 | 0,235 | 0,453 | 0,52 |

La lenga queda por debajo de sus vecinas en 26 de 48 estratos, y la lenga achaparrada en 12 de 21.
La razón agregada es menor que 1, pero el efecto varía mucho entre eventos.

### 3.4 Lectura

1. **El bosque de lenga no es especial.** Dentro del mismo fuego arde como el coihue y el ciprés,
   algo menos que el ñire y ~30 % menos que el matorral y la estepa. Es el orden de Mermoz et al.
   (2005) y Barberá et al. (2025). El modelo ya lo representa en el orden correcto: TL6 propaga a
   ~0,3× SH8 bajo dosel (§4.2). No hay base regional para hacer el TL6 más lento.
2. **La altura frena a todas las clases.** Sobre 1.200 m la lenga arde cada vez menos, pero la
   estepa altoandina cae igual, y la razón lenga/vecinas no se achica con la altura. Es el efecto
   de la altura que describe Barberá et al. (2025), común a todos los tipos. Una parte es
   geométrica: los fuegos suben y terminan en las crestas, así que las celdas altas de la
   envolvente son borde. **Con estos datos no se puede separar cuánto es humedad y cuánto es
   geometría.**
3. **La lenga achaparrada sí arde menos** que sus vecinas a la misma altura (0,41×) y algo menos
   que el bosque de lenga en 1.200–1.400 m (0,24 contra 0,39). Hoy recibe el mismo SH8 que el ñire
   bajo, pero en la región arde 0,70× lo que el ñire, con sólo 5 estratos.
4. **Alcance.** MODIS mezcla clases dentro de una celda de 463 m, lo que acerca las razones a 1:
   las diferencias reales pueden ser algo mayores. Y "a igualdad de exposición" vale dentro de la
   envolvente de 1 km, no celda a celda.

## 4. La regla

### 4.1 Lo que se consideró y por qué no se propone

**(a) Ajuste de humedad bajo dosel de lenga (Δm1 por altura o cobertura).** No hay valor medido
para fijarlo (§2.1). Lo único medido y convertible es el microclima del aire de Paritsis et al.
(2015), que da +1 pp, y eso ya está dentro de lo que probaron `altura-001` y `fosberg-001`. Para
que la humedad frene el TL6 haría falta llevar el m1 a ≥ 20 %, y ningún dato respalda ese número.
Elegir un Δ que frene la montaña sería ajustarlo contra el benchmark.

**(b) Un modelo más lento para el bosque de lenga de altura.** En la calibración de modelo-v0
(última ventana, seis incendios sin el caso límite, clases CCS-BAP del año anterior al fuego):

| Clase | Acierto | Falso positivo | No predicho | Sesgo |
|---|---:|---:|---:|---:|
| Bosque de lenga (TF Le) | 1.351 ha | 974 ha | 1.007 ha | **0,99** |
| Lenga achaparrada (OFL Le) | 385 ha | 1.376 ha | 634 ha | **1,73** |
| Ñire (TF y OFL) | 2.753 ha | 1.938 ha | 2.052 ha | 0,98 |

El TL6 no sobrequema la lenga en calibración, y en la región la lenga arde como el coihue (§3.4).
Un modelo más lento sacaría los 1.351 ha de acierto de Cholila, Alerces 2024 y Alerces 2016 para
arreglar un caso de prueba.

**(c) Lenga achaparrada → TL6, el modelo del bosque de lenga.** Es la candidata con más respaldo:
la región la ve arder la mitad que sus vecinas, la calibración la sobrequema (sesgo 1,73, con
1.098 de los 1.376 ha de falso positivo en Cholila) y el crosswalk ya declara que SH8 es una
analogía sin carga medida (§5.5). Con el Rothermel de `scripts/pruebas_fisicas.py`, m1 5,1 %,
LW 100 % y pendiente de 29°:

| Velocidad de cabeza | TL6 | SH3 | SH8 |
|---|---:|---:|---:|
| Bajo dosel (CC 80 %, CH 8 m), viento a 20 pies de 5 mph | 82 m/h | 43 m/h | 240 m/h |
| Bajo dosel, 15 mph | 97 m/h | 55 m/h | 303 m/h |
| Sin dosel, 15 mph | 175 m/h | 138 m/h | 815 m/h |

**Pero la misma dirección ya se midió.** El loop L corrió `lw100-x-lach3-001` (lenga achaparrada →
SH3) con el mismo diagnóstico de precisión 0,14. Cholila cayó de 0,280 a 0,213, con un sesgo de
0,22, y la receta se rechazó (`AUDITORIA-FISICA.md` loop L; `DECISIONES-MODELO-V0.md` §6). El
fuego real de Cholila corrió a través de la lenga achaparrada, y frenarla corta el camino hacia el
resto de la cicatriz.

TL6 está entre SH3 y SH8, mucho más cerca de SH3. Proponerlo ahora sería elegir otro código en
la misma dirección después de ver que el primero no pasó, con los mismos siete incendios. Eso es
lo que la regla de parada prohíbe.

El dato regional sí es evidencia externa nueva sobre la clase. Pero choca con un resultado de
calibración ya registrado. La lectura más probable es que la velocidad del SH8 en Cholila
compensa procesos que el modelo no tiene: la explosión de las 30–42 h, la copa y las pavesas
(`RIESGOS_Y_SUPOSICIONES.md` §2). No es que el SH8 esté bien.

### 4.2 Cierre

**Se recomienda cerrar `RIESGOS_Y_SUPOSICIONES.md` §4 como límite**, con este texto:

> La probabilidad de quema baja con la altura en todos los tipos de vegetación, lenga incluida
> (Barberá et al. 2025; análisis regional de este documento). El modelo no lo representa: el m1 sale
> del aire de una celda de 25 km, y las correcciones físicas del aire (gradiente térmico, Fosberg)
> mueven el m1 en el orden de 1–5 pp, cuando harían falta ~20 % en la hojarasca para frenar un TL6. No existe una
> medición de humedad de la hojarasca bajo lenga con la cual reemplazarlas. La lenga achaparrada
> arde en la región la mitad que sus vecinas y el modelo la sobrequema (sesgo 1,73 en calibración),
> pero frenarla rompe Cholila (loop L): queda declarada como interacción con los límites de día 1
> y copa.

### 4.3 Qué lo reabriría, y el protocolo ya escrito

Cuenta como evidencia externa nueva, en los términos de la regla de parada, cualquiera de estas:

1. **Humedad medida de la hojarasca bajo lenga** en días de tiempo de fuego (enero–marzo):
   muestreo gravimétrico o palitos de 10 h en un transecto de altura (~800, 1.100, 1.400 m) bajo
   bosque de lenga y lenga achaparrada, con un par a cielo abierto en cada cota y la T/HR del aire
   en cada punto. Una temporada alcanza.
2. **Umbral de ignición de la hojarasca de lenga** con el método de Bianchi y Defossé (2014), a
   comparar con el 25 % del ñire.
3. **Los datos de Barberá et al. (2023)** por sitio, si los autores los comparten (INIBIOMA).

Si llega (1), la regla queda fijada **antes de medir**, sin parámetros libres:

- **Regla H1.** En las celdas `TF Le` y `OFL Le`, m1 = m1 de `altura-001` + Δ(z). Δ(z) es la
  diferencia media medida entre hojarasca bajo lenga y palito a cielo abierto, interpolada
  linealmente entre las cotas medidas y constante fuera de ellas. m10 y m100 conservan sus
  offsets.
- **Protocolo**, separado de modelo-v0:
  - receta hija de `lw-100-001`, con un único factor declarado (`modelo_humedad`); se corre
    **sólo** sobre los 7 de calibración (`benchmarks/particion.json`);
  - criterio de adopción, fijado ahora: Dice medio de calibración ≥ 0,439 (el de modelo-v0) sin
    ninguna alarma nueva, y ningún incendio de calibración que pierda más de 0,05 de Dice. Con
    Cholila y Alerces 2024 en juego (§4.1 b), el segundo criterio es el que decide;
  - Alerces 2015 y los otros tres de prueba se corren una sola vez, al final, y se informan sin
    volver a elegir;
  - si no pasa, se informa como medido y no adoptado, igual que `altura-001`.

## 5. Riesgos

- **El caso de prueba como motivación.** Toda la pregunta nace de Alerces 2015, que es de prueba.
  Este documento no usó sus métricas para nada. Cualquier regla futura tiene que pasar el
  protocolo de §4.3 sólo con los 7 de calibración.
- **Mirar la calibración por clase es mirar resultados.** La tabla de §4.1 (b) se calculó sobre
  las salidas congeladas de modelo-v0, sin corridas nuevas. Sirve para descartar candidatas, no
  para ajustar ningún valor.
- **El análisis regional.**
  - MODIS a 463 m mezcla clases, y eso acerca las razones a 1.
  - La envolvente de 1 km iguala el tiempo y la ignición, pero no la posición dentro del fuego: la
    lenga suele estar en el borde alto.
  - Son 30 eventos, con 2026 y 2021 pesando mucho.
  - El control a 30 m quedó vacío por la exclusión.
  - CCS-BAP 2017 se usa para fuegos de hasta 2026 (nueve años de desfase).
- **La bibliografía.**
  - El dato más directo, Barberá et al. (2023), no se leyó completo.
  - Las comparaciones entre tipos de Barberá et al. (2025) salen del preprint.
  - Su registro de incendios incluye los del benchmark: sus conclusiones son externas como
    análisis, no como dato.
- **Dependencias del script.** `scipy` y `earthengine-api` no están en el proyecto: se agregan
  sólo para esta corrida con `uv run --with`. El activo `COPERNICUS/DEM/GLO30` está marcado como
  obsoleto en Earth Engine (reemplazo: `GLO30_2024_1`); para fracciones por banda de 200 m la
  diferencia es irrelevante.
- **Cerrar como límite tiene un costo.** Los riesgos §2 (día 1), §3 (viento) y §4 (humedad en
  altura) se suman en la montaña: el modelo seguirá subiendo a la lenga cuando el viento sea flojo
  y el aire de la celda esté seco. Para la app, eso es el peor caso, como ya se declara para la
  supresión.

## 6. Fuentes

- Barberá, I.; Cingolani, A.M.; Tiribelli, F.; Mermoz, M.; Morales, J.M.; Kitzberger, T. (2025).
  *Biotic and physical drivers of fire in northwestern Patagonia.* Fire Ecology 21.
  doi:10.1186/s42408-025-00353-8. Preprint: Research Square, doi:10.21203/rs.3.rs-4351591/v1
  (leído en texto completo).
- Barberá, I.; Paritsis, J.; Ammassari, L.; Morales, J.M.; Kitzberger, T. (2023). *Microclimate and
  species composition shape the contribution of fuel moisture to positive fire-vegetation
  feedbacks.* Agricultural and Forest Meteorology 330: 109289. doi:10.1016/j.agrformet.2022.109289
  (sólo resumen y citas secundarias).
- Bianchi, L.O.; Defossé, G.E. (2014). *Ignition probability of fine dead surface fuels in native
  Patagonian forests of Argentina.* Forest Systems 23(1): 129–138. doi:10.5424/fs/2014231-04632.
- Bianchi, L.O.; Defossé, G.E. (2015). *Live fuel moisture content and leaf ignition of forest
  species in Andean Patagonia, Argentina.* International Journal of Wildland Fire 24(3): 340–348.
- Blackhall, M.; Raffaele, E.; Paritsis, J.; Tiribelli, F.; Morales, J.M.; Kitzberger, T.; Gowda,
  J.H.; Veblen, T.T. (2017). *Effects of biological legacies and herbivory on fuels and
  flammability traits: a long-term experimental study of alternative stable states.* Journal of
  Ecology 105(5): 1309–1322. doi:10.1111/1365-2745.12796.
- Fierke, J.; Putzenlechner, B.; Simon, A.; Gowda, J.H.; Reiter, E.J.; Walentowski, H.; Kappas, M.W.
  (2025). *Modelling microclimatic variability in Andean forests of northern Patagonia.*
  International Journal of Biometeorology 69(6): 1279–1295. doi:10.1007/s00484-025-02891-x (sólo
  resumen).
- Fierke, J.; Gowda, J.H.; Díaz, G.M.; Koal, P.; Walentowski, H.; Kappas, M.W.; Putzenlechner, B.
  (2026). *Contrasting vegetation height and elevation shape near-surface thermal responses more
  strongly than slope orientation during summer in northern Patagonia.* International Journal of
  Biometeorology 70(7). doi:10.1007/s00484-026-03254-w (sólo resumen).
- Giglio, L.; Boschetti, L.; Roy, D.P.; Humber, M.L.; Justice, C.O. (2018). *The Collection 6
  MODIS burned area mapping algorithm and product.* Remote Sensing of Environment 217: 72–85
  (producto MCD64A1, colección 6.1 en Earth Engine: `MODIS/061/MCD64A1`).
- Kitzberger, T.; Raffaele, E.; Heinemann, K.; Mazzarino, M.J. (2005). *Effects of fire severity
  in a north Patagonian subalpine forest.* Journal of Vegetation Science 16(1): 5–12.
- Kitzberger, T.; Perry, G.L.W.; Paritsis, J.; Gowda, J.H.; Tepley, A.J.; Holz, A.; Veblen, T.T.
  (2016). *Fire–vegetation feedbacks and alternative states: common mechanisms of temperate forest
  vulnerability to fire in southern South America and New Zealand.* New Zealand Journal of Botany
  54(2): 247–272. doi:10.1080/0028825X.2016.1151903.
- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). *Landscape influences on occurrence and spread
  of wildfires in Patagonian forests and shrublands.* Ecology 86(10): 2705–2715.
  doi:10.1890/04-1850.
- Mundo, I.A.; Villalba, R.; Veblen, T.T.; Kitzberger, T.; Holz, A.; Paritsis, J.; Ripalta, A.
  (2017). *Fire history in southern Patagonia: human and climate influences on fire activity in
  Nothofagus pumilio forests.* Ecosphere 8(9): e01932. doi:10.1002/ecs2.1932.
- Paritsis, J.; Veblen, T.T.; Holz, A. (2015). *Positive fire feedbacks contribute to shifts from
  Nothofagus pumilio forests to fire-prone shrublands in Patagonia.* Journal of Vegetation Science
  26(1): 89–101. doi:10.1111/jvs.12225 (leído en texto completo).
- Rothermel, R.C. (1983). *How to predict the spread and intensity of forest and range fires.*
  USDA Forest Service, GTR INT-143.
- Simard, A.J. (1968). *The moisture content of forest fuels. I. A review of the basic concepts.*
  Canadian Department of Forest and Rural Development, Information Report FF-X-14.
- Tiribelli, F.; Kitzberger, T.; Morales, J.M. (2018). *Changes in vegetation structure and fuel
  characteristics along post-fire succession promote alternative stable states and positive
  fire–vegetation feedbacks.* Journal of Vegetation Science 29(2): 147–156. doi:10.1111/jvs.12620.
- Tiribelli, F.; Paritsis, J.; Barberá, I.; Kitzberger, T. (2024). *Spatial and temporal
  opportunities for forest resilience promoted by burn severity attenuation across a productivity
  gradient in north western Patagonia.* International Journal of Wildland Fire 33(2).
  doi:10.1071/WF23098.
- Veblen, T.T.; Kitzberger, T.; Raffaele, E.; Mermoz, M.; González, M.E.; Sibold, J.S.; Holz, A.
  (2008). *The historical range of variability of fires in the Andean–Patagonian Nothofagus
  forest region.* International Journal of Wildland Fire 17(6): 724–741. doi:10.1071/WF07152.
- Datos: CCS-BAP 2013 y 2017, Chubut y Río Negro (CIEFAP/MAyDS, versión 2019-05-21); Copernicus
  DEM GLO-30; cicatrices dNBR de `mask-dataset-gen`.
