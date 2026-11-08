# Crosswalk CCS-BAP → Scott & Burgan FBFM40

## Objetivo

Convertir la clasificación regional CCS-BAP 2017 a los modelos estándar FBFM40 usados por
ELMFIRE. La clave principal es `(Ley_N1, Ley_N2)`: el mismo código de especie puede representar
bosque (`TF`) o formación leñosa baja (`OFL`). Diez excepciones de nivel 3 separan coberturas que
no pueden compartir comportamiento.

El crosswalk es una propuesta regional reproducible. No modifica parámetros de FBFM40 ni crea
modelos propios.

## Criterio

La selección sigue a Scott & Burgan (2005): estrato portador, humedad de extinción, estructura y
carga del lecho, y contraste con comportamiento observado. Para vegetación nativa se usan
`mex ≥ 25 %`, coherente con umbrales regionales de ignición. Las cargas de arbustal se contrastan
con la Publicación Técnica 37 de CIEFAP.

## Correspondencia

Los porcentajes corresponden al AOI sobre la capa CCS-BAP 2017.

### Tierras Forestales — bosque

| N2 | Especie | % AOI | Código | Modelo | `mex` |
|---|---|---:|---:|---|---:|
| Le | Lenga | 10,64 | 186 | TL6 | 25 |
| Co | Coihue | 6,70 | 165 | TU5 | 25 |
| Ñi | Ñire | 4,32 | 163 | TU3 | 30 |
| Mx | Mixtos | 3,03 | 165 | TU5 | 25 |
| Ci | Ciprés de la cordillera | 2,60 | 165 | TU5 | 25 |
| Ma | Maitén | 0,07 | 182 | TL2 | 25 |
| Rd | Radal | 0,07 | 182 | TL2 | 25 |
| Al | Alerce | 0,04 | 185 | TL5 | 25 |
| Mr | Mirtáceas | 0,04 | 182 | TL2 | 25 |
| Cg | Ciprés de las Guaitecas | 0,00 | 185 | TL5 | 25 |

### Otras Formaciones Leñosas

| N2 | Descripción | % AOI | Código | Modelo | `mex` |
|---|---|---:|---:|---|---:|
| Le | Lenga achaparrada | 8,71 | 148 | SH8 | 40 |
| Arbu Na | Arbustal nativo | 6,59 | 144 | SH4 | 30 |
| Ñi | Ñire bajo | 5,45 | 148 | SH8 | 40 |
| MMx | Matorral mixto | 2,97 | 144 | SH4 | 30 |
| Ci | Ciprés abierto y juvenil | 0,06 | 144 | SH4 | 30 |
| Co, Ch, Rd, Mr, Ma, Cg | Juveniles y arbustos menores | 0,02 | 144 | SH4 | 30 |

### Otras Tierras

| N2 | % AOI | Código | Modelo | `mex` |
|---|---:|---:|---|---:|
| Herb-Subarb | 15,02 | 102; sobre 1.300 m: 99 | GR2; NB9 sobre el límite del bosque | 15 |
| Erial | 11,76 | 99 | NB9 | — |
| Rem Dist Rec | 5,40 | 143 | SH3 | 40 |
| Hie-Nie | 3,86 | 92 | NB2 | — |
| Agua | 3,84 | 98 | NB8 | — |
| Exot-Artif | 2,50 | 101 | GR1 | 15 |
| Humedales | 1,76 | 105 | GR5 | 40 |

### Excepciones de nivel 3

| `Ley_N3` | Código | Modelo | Motivo |
|---|---:|---|---|
| Turbera | 99 | NB9 | combustión latente fuera de Rothermel |
| Cg Juv-Tur | 99 | NB9 | ciprés sobre turbera |
| Caña | 149 | SH9 | carga alta y lecho profundo |
| Estepa Arb | 123 | GS3 | estepa arbustiva |
| Pradera | 105 | GR5 | pastizal húmedo |
| Forest | 188 | TL8 | coníferas exóticas |
| Arles Ex | 182 | TL2 | arboledas latifoliadas exóticas |
| Arbu Ex | 144 | SH4 | arbustal exótico |
| Pastura | 102 | GR2 | pastura implantada |
| Infraest | 91 | NB1 | infraestructura |

Las mezclas de especies heredan el modelo de la especie dominante declarada por el nivel 2.

## Decisiones principales

- **Lenga → TL6:** hojarasca latifoliada; se mantiene por comportamiento regional y ausencia de
  sesgo agregado, aunque no hay carga local medida.
- **Coihue, ciprés y mixtos → TU5:** hojarasca con sotobosque leñoso denso.
- **Ñire arbóreo → TU3:** dosel abierto con componente herbáceo y arbustivo.
- **Ñire bajo → SH8:** es la asignación mejor respaldada por carga regional; reproduce longitud
  de llama pero subestima velocidad.
- **Lenga achaparrada → SH8:** analogía estructural sin carga propia; se mantiene con sesgo
  declarado.
- **Arbustal nativo → SH4:** su carga 1 h coincide con el modelo A3 de la PT-37.
- **Remanente de disturbio → SH3:** representa rebrote leñoso de 6–15 años; reemplaza GS3.
- **Humedad viva:** `LW = 100 %`, calibrada dentro de la banda regional publicada; `LH = 30 %`
  es una convención de pasto curado, no una medición local.

## Resultado

En los seis incendios sin fuga temporal, CCS-BAP obtiene Dice medio 0,415, frente a 0,378 de
MapBiomas y 0,118 de WorldCover. CCS-BAP permanece en `modelo-v0`; MapBiomas es competitivo y no
hay evidencia para afirmar superioridad general. Ver
[`resultados/combustibles/resultados.md`](resultados/combustibles/resultados.md).

## Limitaciones

- CCS-BAP es de 2017; LYQ-3 corrige parcialmente quemas posteriores.
- El 4,55 % del AOI sin cobertura argentina se rellena con WorldCover.
- FBFM40 no fue construido con especies patagónicas y agrupa clases que CCS-BAP distingue.
- Las cargas locales disponibles cubren arbustales, no todo el bosque.
- La agregación a 30 m pierde corredores angostos.
- Dosel y combustible provienen de fuentes y fechas distintas y pueden contradecirse.
- El modelo supone lechos homogéneos y continuos; el ecotono es un mosaico.

## Verificación

`ccsbap_fuel_code()` falla ante clases sin asignación y `assert_codes_are_defined()` verifica que
cada código exista en la tabla cargada por ELMFIRE. Las 92 clases de nivel 3 resuelven a un
modelo. La implementación canónica está en `app/elmfire/builder/fuels_builder.py`; la distribución
se reproduce con `scripts/build_fuel_maps.py`.

## Fuentes principales

- CIEFAP y MAyDS (2016), *Actualización de la Clasificación de Tipos Forestales y Cobertura del
  Suelo de la Región Bosque Andino Patagónico*.
- Bianchi et al. (2012), *Modelos de combustibles en el ecotono bosque-estepa de la Patagonia
  andina*, Publicación Técnica 37.
- Scott y Burgan (2005), *Standard Fire Behavior Fuel Models*, RMRS-GTR-153.
- Bianchi y Defossé (2015), *Live fuel moisture content and leaf ignition of forest species in
  Andean Patagonia, Argentina*, IJWF 24(3):340.
- Cóbar-Carranza et al. (2014), *Effect of Pinus contorta invasion on forest fuel properties*,
  Biological Invasions.
- Tiribelli (2019), *Cambios en la inflamabilidad con la edad post-fuego...*, tesis doctoral,
  Universidad Nacional del Comahue.
- Blackhall et al. (2017), *Effects of biological legacies and herbivory on fuels and
  flammability traits*, Journal of Ecology 105(5), DOI 10.1111/1365-2745.12796.

