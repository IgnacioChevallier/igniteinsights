// ============================================================
//  Correspondencia CCS-BAP → Scott & Burgan FBFM40
//  Compilar: typst compile crosswalk/main.typ
// ============================================================

#let version = "1.0"
#let fecha = "10 de noviembre de 2026"

#set document(
  title: "Tabla de correspondencia de combustibles patagónicos a Scott & Burgan FBFM40",
  author: ("Ignacio Chevallier Boutell", "Manuel Salas Seeber"),
)

// --- Paleta ---
#let prism-blue = rgb("#244B66")
#let prism-light = rgb("#EDF3F6")
#let prism-rule = rgb("#9EB3C0")

// --- Página ---
#set page(
  paper: "a4",
  margin: (top: 24mm, bottom: 25mm, left: 25mm, right: 25mm),
  header-ascent: 9mm,
  header: context {
    set text(size: 8.5pt)
    set par(justify: false, spacing: 0em)
    block(
      width: 100%,
      stroke: (bottom: 0.4pt),
      inset: (bottom: 6pt),
    )[
      #grid(
        columns: (1fr, 1fr),
        align(left)[Ignite Insights],
        align(right)[Versión #version · #fecha],
      )
    ]
  },
  numbering: "1",
)

// --- Texto ---
#set text(font: ("Libertinus Serif", "New Computer Modern"), size: 11pt, lang: "es")
#set par(justify: true, leading: 0.65em, spacing: 0.55em, linebreaks: "optimized")
#show link: set text(fill: prism-blue)
#set list(indent: 1.7em, spacing: 0.8em, body-indent: 0.6em)
#set enum(indent: 1.7em, spacing: 0.8em, body-indent: 0.6em)

// --- Títulos ---
#set heading(numbering: "1.1", supplement: none)
#show heading: it => block(
  above: if it.level == 1 { 1.7em } else { 1.3em },
  below: if it.level == 1 { 0.7em } else { 0.55em },
  {
    set text(
      size: if it.level == 1 { 1.30em } else { 1.10em },
      weight: "bold",
      fill: prism-blue,
    )
    set par(justify: false, spacing: 0em)
    if it.numbering != none {
      let nums = counter(heading).at(it.location())
      let num = if it.level == 1 {
        numbering("1.", nums.at(0))
      } else {
        numbering("1.1", ..nums.slice(0, 2)) + "."
      }
      [#num#h(0.5em)]
    }
    it.body
  },
)

// --- Figuras ---
#show figure.caption: set text(size: 9.5pt)
#set figure(gap: 0.9em)

// Celda de figura botánica: imagen centrada + rótulo (A., B., …)
#let ph(path, label, h: 38mm) = block(above: 0pt, below: 0pt)[
  #image(path, height: h)
  #v(0.45em)
  #text(size: 9.5pt, label)
]

// --- Separación de tablas ---
#show table: set block(above: 0.85em, below: 0.85em)

#let term-def(term, body) = block(
  above: 1em,
  below: 1em,
  [#strong[#term] #linebreak() #body],
)

// ============================================================
//  Portada y contenido
// ============================================================
// Portada alineada con la del informe (informe/docx-to-typ/ignite-option-3/template.typ).
#let brand = rgb("#0B4A3F")
#let muted = rgb("#5D6663")
#page(header: none, numbering: none)[
  #set par(leading: 0.72em, spacing: 1.02em)
  #grid(
    columns: (1fr, auto),
    align: (left + horizon, right + horizon),
    image("images/logo-austral-ingenieria.png", width: 67mm),
    image("images/logo-ignite.png", width: 15mm),
  )
  #v(2.5mm)
  #line(length: 100%, stroke: 1.35pt + brand)
  #v(4mm)
  #text(size: 9pt, style: "italic", fill: muted)[Trabajo de Grado · Documento técnico]
  #v(2.5mm)
  #block(width: 100%)[
    #set par(justify: false, leading: 0.55em)
    #set text(hyphenate: false)
    #text(size: 22pt, weight: "semibold")[Tabla de correspondencia de combustibles patagónicos a Scott & Burgan FBFM40]
  ]
  #v(5mm)
  #text(size: 11.5pt, weight: "semibold")[Ignacio Chevallier Boutell#super[1], Manuel Salas Seeber#super[1]]
  #v(2mm)
  #text(size: 9.2pt, fill: muted)[#super[1] Ingeniería en Informática, Universidad Austral, Argentina]
  #v(6mm)
  #grid(
    columns: (20%, 1fr),
    column-gutter: 8mm,
    align: (left, left + top),
    text(size: 8.4pt, fill: muted)[
      #set par(justify: false)
      *Profesora* \
      Gabriela Robiolo

      *Director* \
      Gastón Gadea
    ],
    text(size: 9.5pt)[
      *Resumen.* Este documento presenta la correspondencia entre las clases de la Clasificación de Tipos Forestales y Cobertura del Suelo del Bosque Andino Patagónico (CCS-BAP) y los 40 modelos estándar de combustible de Scott y Burgan (FBFM40), tal como la usa modelo-v0 en Ignite Insights. La clave combina la categoría de cobertura con la especie o formación declarada. Se completa con diez excepciones de tercer nivel y una regla de altura para la estepa. Cada asignación se fundamenta en la estructura del lecho, la humedad de extinción, las cargas regionales medidas por el CIEFAP y el contraste con una quema experimental. Las fichas por clase indican qué evidencia es directa, qué decisiones son analogías y qué incertidumbres se conservan. El documento no presenta resultados de simulación.
    ],
  )
  #v(1fr)
  #line(length: 100%, stroke: 0.7pt + brand)
  #v(2mm)
  #grid(
    columns: (1fr, 1fr),
    text(size: 8pt, style: "italic", fill: muted)[Trabajo de Grado · Documento técnico · 2026],
    align(right, text(size: 8pt, fill: muted)[Universidad Austral]),
  )
]
#counter(page).update(1)

#outline(title: [Contenido], indent: auto, depth: 1)
#pagebreak()

= Introducción <sec:intro>
Este documento presenta y justifica la correspondencia entre las clases de cobertura del suelo del Bosque Andino Patagónico y los 40 modelos estándar de combustible de Scott & Burgan (FBFM40). El problema que busca resolver puede expresarse mediante una pregunta: ¿cómo determina un simulador de incendios la manera en que arde la vegetación de una región? Un mapa de cobertura describe #emph[qué vegetación o uso del suelo hay en cada lugar], mientras que el simulador necesita representar #emph[cómo puede arder ese material y cómo puede propagarse el fuego a través de él]. La correspondencia desarrollada aquí conecta ambas descripciones.

El objetivo es construir un mapa de combustibles adecuado para el área de interés de la tesis y dejar documentado por qué se eligió cada modelo. Para ello se combinan la información cartográfica disponible, mediciones regionales de combustible, bibliografía sobre la vegetación patagónica y el contraste con una quema experimental.

El documento no propone modelos de combustible nuevos ni pretende describir con exactitud cada sitio del territorio. Selecciona, para cada clase cartográfica, el modelo estándar que mejor representa su estructura conocida; además, señala dónde la evidencia es directa, dónde se recurrió a una analogía y qué incertidumbres deben conservarse. Las fichas de la sección~@sec:5 reúnen ese razonamiento para las clases principales; las clases menores sólo figuran en la tabla de la sección~@sec:4.

#strong[Alcance.] La tabla es la que usa modelo-v0, el modelo de la tesis. Los resultados de las simulaciones no forman parte de este documento y se presentan en el informe de la tesis. La aplicación aplica además, sobre el mapa resultante, una regla por edad para las quemas posteriores al mapa de cobertura; esa regla es posterior a modelo-v0 y no forma parte de esta correspondencia.

= El insumo <sec:1>
El punto de partida fue un conjunto de datos geográficos denominado #strong[Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico] (CCS-BAP). El producto fue elaborado de manera conjunta por el CIEFAP, el Ministerio de Ambiente y Desarrollo Sustentable de la Nación y las provincias de la región, y fue provisto por el CIEFAP el 13 de septiembre de 2026.

En términos prácticos, este conjunto de datos divide el territorio en polígonos y asigna a cada uno una clase de cobertura. Así permite reconocer, entre otras categorías, bosques diferenciados por especie, formaciones arbustivas, pastizales, humedales y superficies afectadas por disturbios recientes. Ese nivel de detalle es el que luego permite asociar estructuras de vegetación diferentes con modelos de combustible diferentes. Por eso se eligió CCS-BAP: a diferencia de WorldCover y MapBiomas, distingue el bosque por especie, separa el bosque (`TF`) de las formaciones leñosas bajas (`OFL`) y mapea la superficie con disturbio reciente.

La entrega incluyó capas de Río Negro, Neuquén, Chubut, Santa Cruz y Tierra del Fuego para las épocas 2013 y 2017. Para el área de interés se usan las dos capas de Chubut. Cada incendio simulado usa el último mapa anterior al incendio: la capa 2013 en Cholila 2015, Los Alerces 2015 y Los Alerces 2016, y la capa 2017 en los otros ocho casos. La correspondencia es la misma para las dos épocas.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (37%, 63%),
      align: (left + top, left + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[Característica]], [#strong[Detalle]],
      ),
      table.hline(stroke: 0.6pt),
      [Capas usadas], [`cob_2013_N3_aok_CH` y `cob_2017_N3_aok_CH` — Chubut, nivel 3],
      [Formato], [Shapefile, #strong[POSGAR94 Faja 1] (EPSG:22181), geometría Polygon Z],
      [Unidad mínima], [1 ha · exactitud global reportada 87 % en nivel 2],
      [Cobertura del AOI (2017)], [#strong[95,45 %] (667.229 ha). El 4,55 % restante es el lado chileno],
    )
  ]
]
== Cambios entre 2013 y 2017 <sec:1.1>
Al comparar ambas épocas dentro del AOI aparecen cambios que ningún producto global registra. La tabla muestra las principales variaciones entre clases, pero no constituye un balance completo de todas las transiciones:

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (32%, 22%, 22%, 24%),
      align: (left + top, right + top, right + top, right + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[Clase]], [#strong[2013]], [#strong[2017]], [#strong[Δ]],
      ),
      table.hline(stroke: 0.6pt),
      [Remanente de disturbio reciente], [155 ha], [#strong[37.736 ha]], [#strong[+37.581]],
      [Lenga], [143.012 ha], [135.275 ha], [−7.737],
      [Ñire], [75.704 ha], [68.308 ha], [−7.395],
      [Mixto de ñire], [27.683 ha], [20.727 ha], [−6.956],
      [Coihue], [53.723 ha], [46.919 ha], [−6.804],
    )
  ]
]
La clase "remanente de disturbio reciente" identifica sectores cuya cobertura vegetal fue alterada hace poco y todavía presenta las huellas del disturbio. Por la fecha y la magnitud del cambio, se interpreta que corresponde principalmente al área afectada por el incendio de Cholila de 2015. La pérdida de bosque de Hansen et al. (2013) lo respalda: dentro de la clase, la mitad de la superficie perdió el bosque en 2015 y el 8 % en 2016, y casi todo el resto no registra pérdida de bosque. Esta atribución no equivale a una transición verificada polígono por polígono. #strong[El 5,4 % del AOI queda clasificado como superficie recientemente disturbada en la capa 2017], con una estructura de vegetación y de material combustible diferente de la del bosque previo y que, por lo tanto, debe representarse con un modelo de combustible propio (§@sec:5.7).

= Método <sec:2>
Se aplica el procedimiento de selección de Scott & Burgan (#link("https://doi.org/10.2737/RMRS-GTR-153")[2005], pp. 8-9).

+ Identificar el #strong[estrato portador del fuego]: pasto, arbusto, hojarasca o combinación con sotobosque.

+ Seleccionar la #strong[humedad de extinción] con evidencia regional, sin heredar la etiqueta climática del modelo.

+ Contrastar #strong[profundidad, compacidad, tamaño, carga y proporción viva/muerta] del lecho.

+ Usar el #strong[comportamiento predicho como filtro de rechazo], contrastándolo con lo observado. La §@sec:metodo-quema resume el contraste con una quema experimental y la falla que comparten los candidatos de arbustal.

Cada #strong[ficha de asignación] de la sección~@sec:5 documenta la clase analizada, el modelo FBFM40 elegido, la evidencia que respalda la decisión y los aspectos que dependen del juicio del autor. No se modifican los parámetros de los modelos FBFM40: construir modelos propios queda fuera del alcance de este documento.

Para elegir entre modelos FBFM40 de una misma familia se utilizan dos criterios regionales: la #strong[humedad de extinción] y la #strong[carga de combustible fino]. El primero permite descartar modelos que sólo sostendrían el fuego en condiciones demasiado secas; el segundo permite comparar la cantidad de material disponible para arder.

== Humedad de extinción <sec:metodo-mex>
La humedad de extinción (`MEX`) es el contenido máximo de humedad con el que los combustibles muertos finos todavía pueden sostener la combustión. Cuando su humedad supera ese límite, el modelo considera que el fuego deja de propagarse por ese material.

Los ensayos de Bianchi & Defossé (2014) con combustibles finos muertos de bosques nativos patagónicos determinaron que estos pueden encenderse con contenidos de humedad de hasta #strong[21,5 % en ciprés y 25,0 % en ñire] (véase Fuentes). En este trabajo, esos resultados se utilizan como una cota inferior para seleccionar la humedad de extinción: un modelo cuyo `MEX` sea menor predice ausencia de propagación en condiciones en las que la medición todavía registra ignición.

Los modelos de Scott & Burgan (2005) sólo ofrecen valores discretos de `MEX`: 12, 15, 20, 25, 30, 35 y 40 %. Como los umbrales se midieron en especies leñosas, el criterio se aplica a las #strong[formaciones leñosas nativas], bosque y matorral: entre sus candidatos se descartan las variantes de 12 a 20 % y se exige `MEX` ≥ 25 %, el menor valor disponible que satisface los dos umbrales. Para los pastos de la estepa no hay un umbral medido en la región, y la estepa graminosa queda en GR2, con `MEX` de 15 % (§@sec:5.8).

== Carga de combustible fino <sec:metodo-carga>
La carga indica cuánta materia vegetal combustible existe por unidad de superficie. En este análisis interesa especialmente la carga fina: hojas, pastos y ramas pequeñas que se humedecen, se secan y participan rápidamente en la propagación del fuego.

La Publicación Técnica N.º 37 de CIEFAP (Bianchi et al., 2012; en adelante PT-37) aporta mediciones para cuatro formaciones arbustivas patagónicas. Esas mediciones están expresadas en toneladas por hectárea (t/ha) y se convierten a libras por pie cuadrado (lb/ft²) para compararlas con los parámetros de FBFM40:

#block[
  `t/ha × 0,0204816 = lb/ft²`.
]
La columna #strong[Carga fina medida] muestra el valor observado en Patagonia. La columna #strong[Carga 1 h del modelo] muestra la carga de los combustibles muertos más finos incorporada en el modelo FBFM40 elegido. La expresión "1 h" no indica cuánto tarda el material en quemarse: identifica una categoría de combustibles finos cuya humedad responde rápidamente a los cambios ambientales.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (24%, 18%, 18%, 18%, 22%),
      align: (left + top, right + top, right + top, right + top, left + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[Modelo PT-37]], [#strong[Carga fina medida]], [#strong[Equivalente]], [#strong[Modelo elegido]], [#strong[Carga 1 h del modelo]],
      ),
      table.hline(stroke: 0.6pt),
      [A1 · ñire maduro arbustivo], [5,91 t/ha], [0,1210 lb/ft²], [SH8], [0,09412],
      [A2 · ñire post-fuego, 2 años], [0,82 t/ha], [0,0168 lb/ft²], [— (§@sec:5.7)], [—],
      [A3 · matorral maqui-radal-ciprés], [1,68 t/ha], [0,0344 lb/ft²], [SH4], [0,03903],
      [A4 · arbustal bajo], [5,66 t/ha], [0,1159 lb/ft²], [GS3 / SH8], [—],
    )
  ]
]
La comparación no busca una igualdad exacta. Se utiliza para elegir, dentro de la familia estructuralmente adecuada, el modelo cuya carga fina sea más cercana a la medida. Por ejemplo, el ñire maduro arbustivo presenta 0,1210 lb/ft² de combustible fino y SH8 utiliza 0,09412 lb/ft² en la categoría de 1 h. Esa proximidad respalda la elección, pero no la determina por sí sola: también se consideran la estructura de la vegetación, la humedad de extinción y el comportamiento esperado del fuego. El modelo A2 describe la regeneración a los dos años del fuego; la clase que lo usaría se asignó por la edad del disturbio y no por esta carga (§@sec:5.7).

== Contraste con una quema experimental <sec:metodo-quema>
El paso 4 se aplicó con la quema experimental del modelo A4 de la PT-37 (§3.3-3.4): Cerro Jones, 14 de septiembre de 2011, en el ecotono y con meteorología medida. El frente recorrió 40 m en 30 s, es decir 4.800 m/h en el pico bajo ráfaga, con llamas de 3 a 4 m. Se reprodujeron esas condiciones con los candidatos de arbustal, sobre terreno plano, con ignición puntual y con viento sostenido y en ráfaga, y el resultado se lee como horquilla.

- SH8, SH4 y GS3 reproducen la longitud de llama, pero su velocidad de propagación queda entre 3 y 11 veces por debajo de la observada.

- SH9 y SH5 se acercan más a la propagación observada, pero con llamas mayores que las medidas: de 7,5 a 12,8 m en SH9 y de 4,9 a 8,0 m en SH5.

Ningún modelo de arbustal de FBFM40 reproduce a la vez la propagación y la llama. Como todas las alternativas fallan en el mismo sentido, el contraste no invalida ninguna asignación. Las asignaciones de arbustal se mantienen #strong[con el sesgo declarado de subestimar la velocidad de propagación]. SH3, asignado al remanente de disturbio (§@sec:5.7), no formó parte de este ensayo.

La evidencia corresponde a una sola quema, en un único sitio, y la comparación usa los parámetros propios de FBFM40, no las cargas medidas en la PT-37.

= Clave de identificación de las clases <sec:3>
Para asignar un modelo de combustible a cada polígono es necesario identificar sin ambigüedades su clase dentro de la leyenda de CCS-BAP. Esa leyenda es jerárquica y distribuye la información en varios campos. `Ley_N1` indica el grupo general de cobertura: Tierras Forestales (`TF`), Otras Formaciones Leñosas (`OFL`) u Otras Tierras (`OT`). `Ley_N2` identifica la clase dentro de ese grupo, por ejemplo la especie o el tipo de cobertura. `Ley_N3` detalla la clase de nivel 2.

La "clave" es la combinación de campos que se utiliza para buscar el modelo FBFM40 correspondiente. En este trabajo se emplea el par `(Ley_N1, Ley_N2)`, y no `Ley_N2` por sí solo, porque algunos códigos se repiten en grupos diferentes.

Por ejemplo, el código `Le` aparece como `TF Le`, donde representa un bosque de lenga, y también como `OFL Le`, donde representa lenga achaparrada de porte arbustivo. Aunque comparten especie, sus estructuras de combustible son distintas: el bosque se asocia con un modelo de hojarasca y la formación achaparrada con uno de arbustal. Si se utilizara únicamente `Ley_N2 = Le`, ambas clases se fusionarían y recibirían incorrectamente el mismo modelo.

Se elige el nivel 2 como principal porque es el nivel con exactitud reportada (87 %). El nivel 3 sólo se usa en las excepciones.

#strong[Excepciones por nivel 3.] Cinco clases de nivel 2 agrupan cosas que arden de manera distinta, y ahí el nivel 2 no alcanza:

- `OT Humedales` contiene mallín, otros humedales y #strong[turbera].

- `OT Exot-Artif` contiene #strong[forestación de coníferas], arboledas, arbustal exótico, pasturas, cultivos e #strong[infraestructura].

- `OT Herb-Subarb` contiene estepa graminosa, #strong[estepa arbustiva] y #strong[pradera].

- `OFL Arbu Na` contiene, entre otros arbustales nativos, la #strong[caña colihue].

- `OFL Cg` contiene el #strong[ciprés de las Guaitecas sobre turbera].

Sin excepciones, la turbera heredaría el modelo del mallín y una plantación de pino heredaría el de un cultivo. Las diez excepciones están en §@sec:tabla-excepciones. Una de las clases de nivel 3, `Estepa`, cambia además de modelo según la altura (§@sec:tabla-altura).

= Tabla de correspondencia <sec:4>
Esta sección resume el resultado principal del trabajo: para cada clase cartográfica se indica el modelo FBFM40 que se utilizará para representar su combustible superficial. Las tablas están separadas según las grandes categorías de la clasificación original. La columna `% AOI` muestra qué proporción del área de interés ocupa cada clase, calculada sobre el recorte de la capa 2017. #strong[Código FBFM40] presenta el identificador numérico requerido por el simulador, mientras que #strong[Modelo y descripción] muestra la sigla equivalente del modelo —por ejemplo, `TL6`— y una descripción breve de su tipo de combustible. La columna `mex` indica la humedad de extinción del modelo.

== Tierras Forestales (TF) - Bosque <sec:tabla-tf>
Esta tabla reúne las clases reconocidas como bosque. La especie dominante se utiliza para distinguir estructuras de combustible diferentes: algunos bosques se representan principalmente por su hojarasca y otros incluyen una participación importante del sotobosque.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (10%, 27%, 9%, 10%, 35%, 9%),
      align: (left + top, left + top, right + top, right + top, left + top, right + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[N2]], [#strong[Especie]], [#strong[% AOI]], [#strong[Código FBFM40]], [#strong[Modelo y descripción]], [#strong[`mex`]],
      ),
      table.hline(stroke: 0.6pt),
      [Le], [Lenga], [10,64], [#strong[186]], [TL6 · hojarasca latifoliada moderada], [25],
      [Co], [Coihue], [6,70], [#strong[165]], [TU5 · hojarasca alta con sotobosque], [25],
      [Ñi], [Ñire], [4,32], [#strong[163]], [TU3 · hojarasca con pasto y arbustos], [30],
      [Mx], [Mixtos], [3,03], [#strong[165]], [TU5], [25],
      [Ci], [Ciprés de la cordillera], [2,60], [#strong[165]], [TU5], [25],
      [Ma], [Maitén], [0,07], [#strong[182]], [TL2 · hojarasca latifoliada carga baja], [25],
      [Rd], [Radal], [0,07], [#strong[182]], [TL2], [25],
      [Al], [Alerce], [0,04], [#strong[185]], [TL5 · hojarasca de conífera carga alta], [25],
      [Mr], [Mirtáceas], [0,04], [#strong[182]], [TL2], [25],
      [Cg], [Ciprés de las Guaitecas], [0,00], [#strong[185]], [TL5], [25],
    )
  ]
]
== Otras Formaciones Leñosas (OFL) - Matorral y bosque achaparrado <sec:tabla-ofl>
Acá se agrupan formaciones leñosas bajas, abiertas o de porte arbustivo que no presentan la estructura de un bosque alto. Por ese motivo predominan los modelos de la familia SH, diseñados para combustibles arbustivos.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (10%, 27%, 9%, 10%, 35%, 9%),
      align: (left + top, left + top, right + top, right + top, left + top, right + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[N2]], [#strong[Descripción]], [#strong[% AOI]], [#strong[Código FBFM40]], [#strong[Modelo y descripción]], [#strong[`mex`]],
      ),
      table.hline(stroke: 0.6pt),
      [Le], [Lenga achaparrada, baja, marginal], [8,71], [#strong[148]], [SH8 · arbustal carga alta clima húmedo], [40],
      [Arbu Na], [Arbustal nativo], [6,59], [#strong[144]], [SH4 · arbustal carga baja clima húmedo], [30],
      [Ñi], [Ñire bajo], [5,45], [#strong[148]], [SH8], [40],
      [MMx], [Matorral mixto], [2,97], [#strong[144]], [SH4], [30],
      [Ci], [Ciprés abierto y juvenil], [0,06], [#strong[144]], [SH4], [30],
      [Co, Ch, Rd, Mr, Ma, Cg], [Juveniles y arbustos menores], [0,02], [#strong[144]], [SH4], [30],
    )
  ]
]
== Otras Tierras (OT) <sec:tabla-ot>
Esta tabla contiene las coberturas que no pertenecen a las dos categorías leñosas anteriores: pastizales, humedales, áreas disturbadas recientemente, agua, hielo, superficies estériles y usos artificiales. Algunas reciben modelos combustibles y otras se representan como áreas no combustibles.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (16%, 14%, 15%, 46%, 9%),
      align: (left + top, right + top, right + top, left + top, right + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[N2]], [#strong[% AOI]], [#strong[FBFM40]], [#strong[Modelo y descripción]], [#strong[`mex`]],
      ),
      table.hline(stroke: 0.6pt),
      [Herb-Subarb], [15,02], [#strong[102]], [GR2 · pastizal carga baja clima seco (`Estepa` sobre 1.300 m: 99 NB9)], [15],
      [Erial], [11,76], [#strong[99]], [NB9 · estéril], [—],
      [Rem Dist Rec], [5,40], [#strong[143]], [SH3 · arbustal carga moderada clima húmedo], [40],
      [Hie-Nie], [3,86], [#strong[92]], [NB2 · nieve y hielo], [—],
      [Agua], [3,84], [#strong[98]], [NB8 · agua], [—],
      [Exot-Artif], [2,50], [#strong[101]], [GR1 · pastizal ralo], [15],
      [Humedales], [1,76], [#strong[105]], [GR5 · pastizal húmedo carga baja], [40],
    )
  ]
]
== Excepciones por nivel 3 <sec:tabla-excepciones>
En estas diez clases, el nivel 2 es demasiado general para describir el combustible. Se utiliza entonces la categoría más detallada del nivel 3 para evitar asignaciones poco realistas, por ejemplo tratar una turbera como un mallín o una forestación de coníferas como una pastura. La excepción tiene prioridad sobre el par `(Ley_N1, Ley_N2)`.

#align(center)[
  #set par(justify: false, spacing: 0.2em)
  #text(size: 0.88em)[
    #table(
      columns: (23%, 19%, 58%),
      align: (left + top, left + top, left + top),
      inset: (x: 4pt, y: 3pt),
      stroke: none,
      table.header(
        [#strong[Ley_N3]], [#strong[FBFM40]], [#strong[Motivo]],
      ),
      table.hline(stroke: 0.6pt),
      [Turbera], [#strong[99] NB9], [Combustión latente, fuera del alcance de Rothermel (§@sec:5.10)],
      [Cg Juv-Tur], [#strong[99] NB9], [Ciprés de las Guaitecas sobre turbera, ídem],
      [Caña], [#strong[149] SH9], [Caña colihue: carga muy alta, lecho profundo],
      [Estepa Arb], [#strong[123] GS3], [Estepa arbustiva — PT-37 modelos A4 y A5],
      [Pradera], [#strong[105] GR5], [Pastizal húmedo de mayor productividad que la estepa],
      [Forest], [#strong[188] TL8], [Forestación de coníferas exóticas, acícula larga],
      [Arles Ex], [#strong[182] TL2], [Arboledas exóticas latifoliadas],
      [Arbu Ex], [#strong[144] SH4], [Arbustal exótico],
      [Pastura], [#strong[102] GR2], [Pastura implantada],
      [Infraest], [#strong[91] NB1], [Infraestructura],
    )
  ]
]
Las clases de nivel 3 que son #strong[mezclas de especies] (`Le-Co`, `Co-Ci`, `Ñi Baj-Le`, …) heredan el modelo de su nivel 2, es decir el de la especie dominante, que es la que da nombre a la clase. Regla declarada, no caso por caso.

== Regla de altura <sec:tabla-altura>
Las celdas de la clase `Ley_N3 = Estepa` situadas a 1.300 m o más, según el modelo digital de elevación de la simulación, se asignan a #strong[99 (NB9)]. Por debajo de esa altura conservan el modelo de su nivel 2, 102 (GR2). La regla se aplica sólo a la clase `Estepa`; el resto de las clases conserva su modelo a cualquier altura. El fundamento está en §@sec:5.8.

= Fichas de asignación <sec:5>
Las fichas de asignación son apartados breves que documentan cómo se llegó desde una clase de la cartografía CCS-BAP hasta un modelo FBFM40. Cada ficha analiza una clase o un grupo de clases con estructura similar, identifica el modelo elegido y desarrolla la evidencia que respalda esa elección.

Cuando la información lo permite, la ficha sigue los cuatro pasos del método: identifica el estrato por el que se propaga el fuego, revisa la humedad de extinción, compara la estructura y la carga del combustible, y contrasta el comportamiento esperado. También distingue los datos bibliográficos o medidos de las decisiones basadas en el juicio del autor, y declara las limitaciones y alternativas.

== TF Le — Bosque de lenga → #strong[186 (TL6)] · 10,64 % del AOI <sec:5.1>
#strong[Paso 1 · Estrato portador.] Hojarasca. La lenga (#emph[Nothofagus pumilio]) es caducifolia y produce un lecho de hojas pequeñas; el sotobosque es pobre en los rodales densos de altura. Es el caso en que la familia TL corresponde y TU no.

#figure(
  block(width: 100%, grid(
    columns: (1fr, 1fr),
    gutter: 1.2em,
    align: top + center,
    ph("images/lenga-hojas.jpg", [*A.* Hojas de lenga.]),
    ph("images/lenga-tronco.jpg", [*B.* Detalle del fuste.]),
  )),
  caption: [
    Lenga (#emph[Nothofagus pumilio]). El detalle foliar permite reconocer el carácter latifoliado y caducifolio asociado a la formación de hojarasca. Fotografías: Gagea, CC BY-SA 3.0 (A); Bob Ramsak, CC BY-SA 4.0 (B), vía Wikimedia Commons.
  ],
)
<fig:lenga>

#strong[Paso 2 · Humedad de extinción.] TL6 tiene `mex = 25 %`, que iguala el umbral de ignición medido en ñire (25,0 %) y supera el de ciprés. Se descarta #strong[TL3 (183)] por dos razones: `mex = 20 %` y, sobre todo, porque es hojarasca de #strong[conífera de acícula larga], un lecho físicamente distinto del de una latifoliada caducifolia.

#strong[Paso 3 · Estructura.] TL6: 1 h 0,11019 lb/ft², lecho 0,3 pies, sin componente vivo. Es hojarasca latifoliada de carga moderada.

#strong[Paso 4 · Contraste.] TL6 presenta una propagación #emph[moderada] y una llama #emph[baja], coherentes con un fuego de superficie bajo dosel cerrado. El fuego de copas en lenga no se representa aquí, sino mediante las capas de dosel del simulador.

#strong[Procedencia.] El estrato portador y el tipo de hojarasca son bibliográficos; la elección de TL6 sobre TL2 y TU2 es juicio fundamentado del autor. No hay carga medida de sotobosque para toda la clase (§@sec:11).

== TF Co, TF Ci y TF Mx — Coihue, ciprés y mixtos → #strong[165 (TU5)] · 12,33 % del AOI <sec:5.2>
Coihue (#emph[N. dombeyi], perennifolio) y ciprés (#emph[Austrocedrus chilensis], conífera) comparten una característica que decide el modelo: #strong[sotobosque leñoso denso], de caña colihue (#emph[Chusquea culeou]), #emph[Berberis] y #emph[Maytenus]. El estrato portador es la hojarasca #strong[con] sotobosque; es decir, corresponde la familia TU.

#figure(
  block(width: 100%, grid(
    columns: (1fr, 1fr),
    gutter: 1.2em,
    align: top + center,
    row-gutter: 1em,
    ph("images/coihue-hojas.jpg", [*A.* Follaje de coihue.], h: 30mm),
    ph("images/cipres-follaje.jpg", [*B.* Follaje de ciprés de la cordillera.], h: 30mm),
    ph("images/cana-colihue.jpg", [*C.* Formación densa de caña colihue.], h: 30mm),
    ph("images/maiten-porte.jpg", [*D.* Porte de maitén; ejemplar urbano usado sólo como referencia visual.], h: 30mm),
  )),
  caption: [
    Especies y estructura vegetal asociadas a la ficha TU5. La caña colihue ilustra el sotobosque denso que diferencia este modelo de uno compuesto únicamente por hojarasca. Fotografías: Valerio Pillar, CC BY-SA 2.0 (A); Gagea, CC BY-SA 3.0 (B); McKay Savage, CC BY 2.0 (C); Pdassori, CC BY-SA 4.0 (D), vía Wikimedia Commons.
  ],
)
<fig:tu5-especies>

TU5 es el modelo de mayor carga de la familia (1 h 0,18365, 10 h 0,18365, 100 h 0,13774, leñoso vivo 0,13774, `mex` 25) y su descripción —#emph["heavy forest litter with a shrub or small tree understory"]— coincide con la estructura descrita. Se restringe a las especies que efectivamente la justifican, en lugar de aplicarse a todo el bosque.

#strong[TF Mx — mixtos (3,03 %).] Son rodales donde ninguna especie domina, por lo que no se aplica la regla general de mezclas de la §@sec:4, según la cual la clase hereda el modelo de la especie dominante. Se les asigna TU5 porque las especies que integran la mezcla son las mismas de esta ficha, además de la lenga, y ninguna de ellas modifica el estrato portador: el sotobosque leñoso de caña permanece y el fuego continúa propagándose por la hojarasca #strong[con] sotobosque. #strong[Es la asignación con menos respaldo específico de las tres de esta ficha], porque la composición exacta de cada rodal mixto no se verificó clase por clase.

#strong[Limitación.] Coihue (muy húmedo, oeste) y ciprés (más seco, este) reciben el mismo modelo pese a tener regímenes de humedad distintos. CCS-BAP los separa, pero nuestra parametrización no los diferencia. Los mixtos agravan esta limitación: un rodal de lenga y coihue recibe el modelo del coihue puro.

== TF Ñi — Bosque de ñire → #strong[163 (TU3)] · 4,32 % del AOI <sec:5.3>
El ñire (#emph[N. antarctica]) forma bosques abiertos con estrato herbáceo continuo, históricamente pastoreados, en el ecotono. Es el caso que Scott & Burgan advierten en el paso 1: con dosel abierto #strong[el pasto puede llevar el fuego, no la hojarasca].

#figure(
  block(width: 100%, grid(
    columns: (1fr, 1fr),
    gutter: 1.2em,
    align: top + center,
    ph("images/nire-formacion.jpg", [*A.* Formación de ñire.]),
    ph("images/nire-hojas.jpg", [*B.* Detalle de ramas, hojas y brotes.]),
  )),
  caption: [
    Ñire (#emph[Nothofagus antarctica]). La misma especie aparece en CCS-BAP como bosque de ñire y como ñire bajo; la diferencia relevante para la asignación de combustible es estructural y no taxonómica. Fotografías: Lin linao, CC BY-SA 3.0 (A y B), vía Wikimedia Commons.
  ],
)
<fig:nire>

TU3: #emph["moderate forest litter with grass and shrub components"], `mex = 30 %`, #strong[dinámico], propagación #emph[alta]. La PT-37 lo respalda de manera indirecta: sus modelos de ñire (A1 y A2) describen la propagación por el estrato herbáceo de los entreparches.

== OFL Ñi — Ñire bajo → #strong[148 (SH8)] · 5,45 % del AOI <sec:5.4>
#strong[Es la asignación con mejor respaldo de toda la tabla], y la única con carga medida en la misma formación.

#strong[Paso 1.] Arbustivo. CCS-BAP documenta que el ñire arbóreo y el arbustivo no son separables por sensores ópticos y los agrupa como #emph[Ñire Bajo]; fisonómicamente es matorral.

#strong[Paso 2.] SH8, `mex = 40 %`, clima húmedo. Muy por encima del umbral medido de 25,0 % en ñire, que es la especie de esta clase.

#strong[Paso 3.] El modelo A1 de la PT-37 —ñire maduro arbustivo, dosel continuo, laura, radal y caña colihue— registra #strong[5,91 t/ha de combustible fino muerto = 0,1210 lb/ft²], con 27,5 % de material muerto aéreo en la copa y una altura media de 4,83 m. La carga de 1 h de SH8 es 0,09412 lb/ft², la más cercana entre los modelos de arbustal de clima húmedo. #strong[Se descarta SH9 (149)] por su carga de 1 h de 0,20661, casi el doble de lo medido, y #strong[SH5 (145)] por `mex = 15 %`.

#strong[Paso 4 · Contraste con la quema experimental] (§@sec:metodo-quema). SH8 reproduce la longitud de llama observada —3,1 m frente a los 3 a 4 m medidos—, pero #strong[subestima la propagación]: 437 m/h con viento sostenido y 900 m/h bajo ráfaga, frente a 4.800 m/h observados. Ningún modelo de arbustal de FBFM40 reproduce las dos variables a la vez. La asignación se mantiene porque es la que mejor ajusta la llama y la carga fina medida, y #strong[se declara que subestima la velocidad de propagación].

#strong[Segunda fuente, independiente.] Cóbar-Carranza et al. (2014) miden en rodales de #emph[N. antarctica] de la Reserva Malalcahuello (Chile, ≈38°S, 2.580 árboles/ha, 3,6 m de altura media —es decir, ñire bajo—) #strong[1.930 ± 307 kg/ha de leña fina caída de menos de 0,6 cm]. No es directamente comparable con la PT-37, porque ese trabajo separa la hojarasca de la leña fina y la PT-37 las agrupa, pero se encuentra en el mismo orden de magnitud y refuerza que la clase no es de carga alta. #strong[Limitación de transferencia:] corresponde a otra latitud y a un bosque subalpino con araucaria, ausente del AOI.

#strong[Procedencia.] Carga: medida (PT-37, Tabla 2), corroborada por una segunda fuente. `mex`: bibliográfico. Elección final del modelo: juicio del autor sobre carga, sujeto al paso 4.

== OFL Le — Lenga achaparrada → #strong[148 (SH8)] · 8,71 % del AOI <sec:5.5>
La lenga de porte achaparrado del límite altitudinal forma una cobertura densa y baja, con abundante material muerto en pie. No hay una carga medida para esta formación; se le asigna el mismo modelo que al ñire bajo por analogía estructural, ya que ambas son formaciones densas de #emph[Nothofagus] caducifolios de porte arbustivo.

#strong[Esta simplificación se declara explícitamente.] CCS-BAP separa la lenga achaparrada del ñire bajo, pero #strong[nuestra parametrización no puede reflejar esa diferencia]: no existe un modelo FBFM40 construido a partir de ninguna de las dos formaciones y sólo una cuenta con una carga medida. La alternativa más cercana es SH3 (143), de carga menor.

== OFL Arbu Na y MMx — Arbustal nativo y matorral mixto → #strong[144 (SH4)] · 9,56 % <sec:5.6>
El modelo A3 de la PT-37 representa un matorral de maqui, radal, ciprés y laura, con una altura media de 3,42 m, una cobertura del 54 % y #strong[1,68 t/ha de combustible fino = 0,0344 lb/ft²]. La carga de 1 h de SH4 es 0,03903 lb/ft², el valor más cercano de la tabla.

SH4: lecho de 3 pies, leñoso vivo 0,11708, `mex = 30 %`, propagación #emph[alta], llama #emph[moderada]. Coherente con Mermoz et al. (2005): los matorrales patagónicos propagan más que los bosques.

La clase de origen es efectivamente matorral, y la PT-37 aporta una carga medida en una formación equivalente. Dentro de `Arbu Na`, la caña colihue es una excepción y va a SH9 (§@sec:tabla-excepciones).

== OT Rem Dist Rec — Remanente de disturbio reciente → #strong[143 (SH3)] · 5,40 % <sec:5.7>
La clase reúne superficies alteradas poco antes del mapa. En la capa 2017 corresponde principalmente al incendio de Cholila de 2015 (§@sec:1.1); en la capa 2013 ocupa sólo 155 ha.

El análogo medido más cercano es el modelo A2 de la PT-37, regeneración coetánea de ñire a los dos años del fuego, con entreparches amplios y estrato herbáceo de gramíneas, donde #emph["el fuego propaga rápidamente por el estrato herbáceo en los entreparches y por las copas de los arbustos en los parches"]. A2 mide 0,82 t/ha de fino = 0,0168 lb/ft², una carga compatible con GS3 (1 h 0,01377).

Pero A2 describe los primeros años después del fuego, y en los incendios simulados el remanente es más viejo. De los ocho casos que usan la capa 2017, siete ocurren entre seis y once años después del incendio de Cholila, que comenzó en febrero de 2015. La excepción es Epuyén 2019, a cuatro años. A esa edad, el ñire y los arbustos que rebrotan ya forman un #strong[matorral leñoso denso], con más combustible fino y más inflamable que el bosque que reemplazan (Tiribelli et al., 2018; Blackhall et al., 2017). Por eso se asigna SH3: arbustal de carga moderada y clima húmedo, estático, lecho de 2,4 pies, 1 h 0,02066 lb/ft², leñoso vivo 0,28466 lb/ft² y `mex = 40 %`, por encima de los umbrales de ignición medidos.

#strong[Alternativas descartadas.] GS3 (123), porque representa los primeros dos a cinco años de regeneración. SB2 (202), de la familia #emph[slash-blowdown], porque representa el material muerto en pie inmediatamente después del fuego.

#strong[Procedencia.] La edad del remanente y la estructura del rebrote son bibliográficas. La elección de SH3 sobre GS3 es juicio del autor y se revisó también durante la calibración de modelo-v0, por lo que no es puramente bibliográfica; las cifras están en el informe de la tesis. SH3 no formó parte de la quema experimental (§@sec:metodo-quema), así que no tiene contraste de comportamiento observado.

== OT Herb-Subarb — Estepa → #strong[102 (GR2)] · 15,02 %, con excepciones y regla de altura <sec:5.8>
`Estepa` (graminosa, coirón de #emph[Festuca] y #emph[Stipa]) → GR2, #emph["low load, dry climate grass"], `mex = 15 %`, dinámico. La estepa de coirón es un pastizal ralo, con suelo desnudo entre matas, en el sector más seco del AOI; GR2 representa ese lecho de carga baja. La alternativa considerada fue GR3 (103), pasto grueso de clima húmedo, con más carga y `mex = 30 %`.

El `mex` de 15 % queda por debajo del criterio de §@sec:metodo-mex, que se aplica sólo a las formaciones leñosas: los umbrales de ignición se midieron en ciprés y ñire, y no hay un umbral medido para los pastos de la estepa.

#strong[Sobre el límite del bosque.] CCS-BAP llama `Estepa` también a la vegetación altoandina escasa que crece entre roca y nieve, por encima del límite del bosque. Por eso las celdas de `Estepa` situadas a 1.300 m o más se asignan a #strong[99 (NB9)], no combustible (§@sec:tabla-altura). La regla no alcanza a `Estepa Arb`, `Pradera` ni a otras clases de alta montaña.

#strong[Procedencia.] La estructura de la estepa y la presencia de vegetación altoandina dentro de la clase son bibliográficas y cartográficas. La elección de GR2 sobre GR3 y el umbral de 1.300 m son juicio del autor y se revisaron también durante la calibración de modelo-v0, por lo que no son puramente bibliográficos; las cifras están en el informe de la tesis.

`Estepa Arb` (estepa arbustiva) → #strong[GS3], por los modelos A4 y A5 de la PT-37: arbustal bajo con gramíneas, donde #emph["con vientos moderados o fuertes el largo de llama supera la distancia entre parches"]. Es una codominancia de arbustos y pastos, por lo que corresponde a la familia GS.

`Pradera` → GR5, pastizal húmedo de mayor productividad.

== OT Erial → #strong[99 (NB9)] · 11,76 % <sec:5.9>
Erial es clase propia en CCS-BAP: suelo desnudo, roca, pedregal. Que exista como clase permite tomar la fracción no combustible del insumo regional, en vez de heredarla de un producto global.

== OT Humedales — Mallín y turbera <sec:5.10>
`Mallin` y `Otros Hum` → GR5 (`mex = 40 %`, dinámico, carga herbácea viva alta): pastizal higrófilo que sólo propaga cuando está curado, que es la manera correcta de codificar esa fenología dentro del formalismo de Rothermel.

`Turbera` → #strong[NB9, declarado fuera de alcance.] Scott & Burgan (2005, p. 3) limitan el conjunto al #emph["surface fire behavior at the flaming front only, not residual combustion"]. Una turbera arde por combustión latente subterránea. Asignarle un modelo de superficie produciría un resultado sin sustento físico. #strong[Esta decisión subestima el fuego en turberas, y la limitación se declara explícitamente.]

= Limitaciones <sec:7>
+ #strong[Desfase temporal.] El mapa más reciente es de 2017 y los incendios simulados llegan a 2026: hasta nueve años de desfase. Se usa el último mapa anterior a cada incendio (§@sec:1), pero los cambios posteriores al mapa —regeneración, nuevos disturbios o cambios de uso del suelo— no están en el insumo.

+ #strong[Hueco fronterizo del 4,55 % en el recorte vectorial.] CCS-BAP no cubre el lado chileno del AOI, que se rellena con WorldCover. En el borde oeste, la calidad del combustible queda limitada por ese insumo.

+ #strong[FBFM40 no distingue lo que CCS-BAP sí distingue] (§@sec:5.5): el ñire bajo y la lenga achaparrada comparten modelo, al igual que el coihue y el ciprés. La limitación principal se encuentra en el sistema de modelos y no en el insumo.

+ #strong[Los modelos de arbustal subestiman la velocidad de propagación] observada en la única quema experimental disponible (§@sec:metodo-quema).

+ #strong[Homogeneidad dentro de la clase]: no se distingue estado sucesional, historia de fuego ni carga de material muerto en pie, salvo por la clase de disturbio reciente.

+ #strong[Agregación a 30 m por clase mayoritaria]: se pierden corredores de combustible más angostos que un píxel, y la continuidad gobierna la propagación.

+ #strong[La PT-37 sólo cubre arbustales], no bosque. Las clases de bosque siguen sin carga medida.

+ #strong[FBFM40 se calibró con series fotográficas de combustibles de los Estados Unidos.] Ninguna especie patagónica participó en su construcción. Los cuarenta modelos forman un conjunto estándar desarrollado para otro continente; esta es la limitación de fondo de todo el ejercicio: la tabla selecciona el modelo disponible más adecuado, no un modelo necesariamente correcto para la Patagonia.

+ #strong[El modelo de Rothermel supone un lecho de combustible homogéneo y continuo] (Scott & Burgan 2005, p. 3). Los mosaicos de bosque, matorral y estepa del ecotono violan ese supuesto, y la continuidad del combustible es justamente lo que gobierna la propagación. Las quemas de la PT-37 lo muestran: el fuego cruza entre parches por el estrato herbáceo de los entreparches, que es geometría que el formalismo no representa.

+ #strong[No existe crosswalk publicado de especies patagónicas a FBFM40.] No hay precedente contra el cual contrastar esta tabla ni calibración de origen que heredar: es una #strong[propuesta original] y debe presentarse y evaluarse como tal. Es también la razón por la que cada asignación lleva ficha con su procedencia (§@sec:5) y por la que sus limitaciones se declaran en vez de dar la tabla por cerrada.

= Verificación <sec:8>
- `ccsbap_fuel_code()` #strong[genera una excepción] ante una clase de leyenda sin modelo asignado. Un `KeyError` silencioso asignaría una clase real a la categoría no combustible sin que el problema quedara registrado.

- `assert_codes_are_defined()` verifica, antes de escribir el ráster, que todo código exista en la tabla que ELMFIRE realmente carga. ELMFIRE resuelve cualquier código ausente al modelo 256 (NB, no combustible) #strong[sin error y sin registro].

- Las 92 clases de nivel 3 de Chubut se asignan a un modelo; esto se verificó durante la construcción del ráster.

#strong[Procedencia de los números.] Los porcentajes de §@sec:4–§@sec:5 corresponden al recorte vectorial de la capa 2017 sobre el AOI, antes de rasterizar. Los parámetros de los modelos son los de Scott & Burgan (2005), Tabla 7, que coinciden con la tabla que carga ELMFIRE (`app/elmfire/fuel_models.csv`).

= Glosario <sec:9>
#term-def[AOI (Area Of Interest)][Zona geográfica delimitada para el análisis. En este documento corresponde al área de estudio de la tesis sobre la cual se calculan superficies y porcentajes.]

#term-def[Estepa][Ambiente abierto con pocos árboles, dominado por pastos y arbustos bajos, característico de sectores secos de la Patagonia.]

#term-def[Turbera][Humedal donde se acumula turba, un material formado por restos vegetales parcialmente descompuestos y saturados de agua. Puede mantener combustión lenta bajo la superficie cuando se seca.]

#term-def[Rodal][Sector de bosque relativamente homogéneo en cuanto a especies, edad, densidad o estructura de los árboles.]

#term-def[Dosel][Capa superior de un bosque, formada principalmente por las copas y ramas de los árboles. Su densidad condiciona la cantidad de luz, viento y precipitación que alcanza el sotobosque y el suelo.]

#term-def[Sotobosque][Vegetación que crece debajo del dosel de los árboles, como pastos, hierbas y arbustos.]

#term-def[Caducifolia][Especie vegetal que pierde sus hojas durante una época del año.]

#term-def[Hojarasca][Capa de hojas, ramitas y otros restos vegetales que se acumula sobre el suelo.]

#term-def[Lecho de combustible][Conjunto y disposición del material vegetal disponible para arder cerca de la superficie del suelo.]

#term-def[Estrato portador del fuego][Tipo de vegetación o material combustible por el cual se propaga principalmente el fuego, por ejemplo pasto, arbustos u hojarasca.]

#term-def[Familias TL y TU][Grupos de modelos de combustible de Scott & Burgan. La familia TL representa principalmente fuego propagado por hojarasca; la familia TU representa hojarasca combinada con vegetación de sotobosque.]

#term-def[MEX (humedad de extinción)][Contenido máximo de humedad con el cual los combustibles finos muertos todavía pueden sostener la combustión.]

= Fuentes <sec:10>
- CIEFAP, MAyDS (2016). #emph[Actualización de la Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico. Informe Final.] Capas `cob_2013_N3_aok_CH` y `cob_2017_N3_aok_CH`, provistas por CIEFAP el 2026-09-13.

- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. (2012). #emph[Modelos de combustibles en el ecotono bosque-estepa de la Patagonia andina.] CIEFAP, Publicación Técnica N.º 37. ISSN 1514-2264.

- Scott, J.H.; Burgan, R.E. (2005). #emph[Standard Fire Behavior Fuel Models: A Comprehensive Set for Use with Rothermel's Surface Fire Spread Model.] RMRS-GTR-153. #link("https://doi.org/10.2737/RMRS-GTR-153")[https://doi.org/10.2737/RMRS-GTR-153] (Procedimiento de selección pp. 8-9 · alcance p. 3 · modelos dinámicos p. 4 · parámetros Tabla 7)

- Bianchi, L.O.; Defossé, G.E. (2014). #emph[Ignition probability of fine dead surface fuels of native Patagonian forests of Argentina.] Forest Systems 23(1):129-138. #link("https://doi.org/10.5424/fs/2014231-04632")[https://doi.org/10.5424/fs/2014231-04632] (Umbrales de ignición: 21,5 % en ciprés y 25,0 % en ñire · §@sec:2)

- Blackhall, M.; Raffaele, E.; Paritsis, J.; Tiribelli, F.; Morales, J.M.; Kitzberger, T.; Gowda, J.H.; Veblen, T.T. (2017). #emph[Effects of biological legacies and herbivory on fuels and flammability traits: A long-term experimental study of alternative stable states.] Journal of Ecology 105(5):1309-1322. #link("https://doi.org/10.1111/1365-2745.12796")[https://doi.org/10.1111/1365-2745.12796]

- Hansen, M.C.; Potapov, P.V.; Moore, R.; Hancher, M.; Turubanova, S.A.; Tyukavina, A.; Thau, D.; Stehman, S.V.; Goetz, S.J.; Loveland, T.R.; Kommareddy, A.; Egorov, A.; Chini, L.; Justice, C.O.; Townshend, J.R.G. (2013). #emph[High-resolution global maps of 21st-century forest cover change.] Science 342(6160):850-853. #link("https://doi.org/10.1126/science.1244693")[https://doi.org/10.1126/science.1244693] Versión GFC-2025 v1.13, capa `lossyear`.

- Cóbar-Carranza, A.J.; García, R.A.; Pauchard, A.; Peña, E. (2014). #emph[Effect of Pinus contorta invasion on forest fuel properties and its potential implications on the fire regime of Araucaria araucana and Nothofagus antarctica forests.] Biological Invasions.

- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). #emph[Landscape influences on occurrence and spread of wildfires in Patagonian forests and shrublands.] Ecology 86(10).

- Tiribelli, F.; Kitzberger, T.; Morales, J.M. (2018). #emph[Changes in vegetation structure and fuel characteristics along post-fire succession promote alternative stable states and positive fire–vegetation feedbacks.] Journal of Vegetation Science 29(2):147-156. #link("https://doi.org/10.1111/jvs.12620")[https://doi.org/10.1111/jvs.12620]

= Supuestos metodológicos sujetos a validación <sec:11>
Para completar la correspondencia fue necesario adoptar cuatro supuestos en clases donde la información disponible no permite una asignación directa. Estos supuestos hacen posible construir el mapa de combustibles, pero introducen incertidumbres que deben considerarse al usarlo.

+ #strong[OFL Le → SH8.] Se asumió que la lenga achaparrada se comporta como un arbustal húmedo de carga alta debido a su estructura baja y densa. La asignación se basa en una analogía estructural, ya que no se dispone de una medición local de carga para esta clase. Abarca el #strong[8,71 % del AOI] y puede introducir incertidumbre en la intensidad y la velocidad de propagación estimadas (§@sec:4 y §@sec:5.5).

+ #strong[TF Le → TL6.] Se asumió que en el bosque de lenga el fuego se propaga principalmente por la hojarasca y que el sotobosque tiene una participación limitada. Por eso se eligió TL6 y no un modelo de la familia TU. No se cuenta con información específica sobre el sotobosque para toda la clase, que representa el #strong[10,64 % del AOI] (§@sec:4 y §@sec:5.1).

+ #strong[Rem Dist Rec → SH3.] Se asumió que las áreas disturbadas mapeadas en 2013 y 2017, principalmente el incendio de Cholila de 2015, ya son matorral leñoso rebrotante cuando ocurren los incendios simulados, entre 2015 y 2026. La capa no describe el estado ni el grado de regeneración de cada sector en la fecha de cada incendio, por lo que esta asignación resume como una sola clase situaciones que pueden ser heterogéneas. Comprende el #strong[5,40 % del AOI] (§@sec:4 y §@sec:5.7).

+ #strong[Uso del último mapa anterior a cada incendio.] Se asumió que la cobertura registrada en 2013 o 2017 sigue siendo suficientemente representativa en la fecha de cada incendio, con hasta nueve años de diferencia. Los cambios posteriores al mapa —por regeneración, nuevos disturbios o cambios de uso del suelo— no están reflejados en el insumo y constituyen una fuente de incertidumbre temporal (§@sec:1 y §@sec:7).
