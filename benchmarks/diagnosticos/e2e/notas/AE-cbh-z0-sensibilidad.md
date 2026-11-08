# AE · CBH nativo y rugosidad: sensibilidad acotada, sin ELMFIRE

> 2026-10-31. Diseño registrado antes de calcular nada (§1–§2). Resultado en §3.
> **Decisión del usuario (2026-10-31): las dos se cierran como límites declarados**
> (`ESTADO-RESEARCH.md` §6.2, `PENDING_PARAMETERS.md` §3, `RIESGOS_Y_SUPOSICIONES.md` §8).
> No cambia modelo-v0 ni calibra nada: es insumo para que el autor decida si las dos
> incertidumbres de `PENDING_PARAMETERS.md` §2 se cierran como límite declarado o quedan abiertas
> con un camino para reabrirlas. No elige valores.

## 0. Problema

`PENDING_PARAMETERS.md` §2 deja abiertas dos incertidumbres de entrada:

1. **CBH de bosque nativo.** Valores indirectos de literatura por clase FBFM40
   (`docs/crosswalk.md` §2): lenga TL6 6 m, alerce TL5 4 m, coihue/ciprés con
   caña TU5 1,5 m, ñire TU3 1,5 m, matorral alto TL2 1 m. El pino (TL8, 1,5 m) está medido y no se
   toca acá.
2. **Rugosidad.** `z0 = 0,22 m` uniforme en `weather_builder.wind_height_factor` para llevar el
   viento de 10 m a 20 ft. `z0-dosel-001` (z0 = 0,13 × CH) empeoró el objetivo por el doble conteo
   con el WAF de ELMFIRE (loop 3, interfaz v2).

La pregunta, para cada una: ¿el rango plausible puede mover algo material?

## 1. CBH: diseño

**Casos:** los seis incendios de calibración del diagnóstico de copa (`benchmark.py copa`,
`DIA-1-PROPUESTA.md` §7.4): Alerces 2023 (h54), Epuyén 2025, Alerces 2024, Patriada 2026,
Alerces 2016 (ERA5), Cholila 2015 (ERA5). Las Golondrinas queda fuera, como en §7.4. **El conjunto
de prueba no se abre.**

**Celdas:** las de `diagnosticar_copa`, día 1 (ventana 0): bosque TU/TL con dosel (CC ≥ 0,15,
CH ≥ 2 m, CBH > 0, CBD > 0), dentro de la cicatriz y vistas por VIIRS en esa ventana.

**Cálculo.** Igual que `diagnosticar_copa` del lado ELMFIRE: Rothermel sin pendiente
(`copa.rothermel`) con el viento a 20 ft × WAF de ELMFIRE (`copa.waf_elmfire`), clima por hora del
paquete `calibracion-v6`, LW/LH de `lw-100-001`, cualquier hora hasta la primera detección. El WAF
no depende del CBH, así que por celda basta la intensidad máxima antes de verse, `I_max`. La celda
inicia copa con un CBH `c` si `I_max > I_0(c)` (Van Wagner, FMC 90 %). De ahí sale, por celda, el
**CBH umbral** `c* = I_max^(2/3) / (0,01 · (460 + 26 · 90))`: inicia copa con todo CBH < `c*`. La
fracción que inicia con un CBH dado es la fracción de celdas con `c*` mayor. Una sola pasada da la
curva entera.

**Control:** con el CBH de literatura, la fracción Van Wagner del día 1 tiene que coincidir con
`benchmarks/diagnosticos/copa/*.json` (§7.4). Si no coincide, el cálculo no vale y no se informa.

**Rangos declarados** (por clase; el resto de la curva se informa igual):

| Clase | Literatura (v6) | Rango | De dónde sale |
|---|---:|---|---|
| TL6 lenga | 6 m | 3–10 m | El hueco de ~6 m de Paritsis et al. (2015) y el CBH derivado de v5 (5–10 m) arriba; abajo, la mitad del valor adoptado, sin fuente que lo sostenga |
| TL5 alerce, ciprés de las Guaitecas | 4 m | 1,5–8 m | Sin dato; entre el TU5 con caña y el doble del valor adoptado |
| TU5 coihue, ciprés, mixtos | 1,5 m | 0,5–3 m | La caña colihue (2–7 m) como escalera continua; 2,5 m ya se probó en el loop L |
| TU3 ñire | 1,5 m | 0,5–3 m | Sin separación vertical (Tiribelli et al. 2018); 2 m es la ramificación mínima del monte bajo en la ley XVII-92 de Chubut, una definición legal y no una medición |
| TL2 matorral alto | 1 m | 0,5–2 m | Matorral alto continuo (Mermoz et al. 2005) |

Cada clase se mueve sola, con las demás en su valor v6, y además todas juntas a los dos extremos.

**Qué se concluye (fijado antes):**

- **No material.** Si en los seis incendios la fracción Van Wagner del día 1 cambia menos de
  0,10 (absoluto) en todo el rango de cada clase y en los dos extremos conjuntos, el rango plausible
  no cambia la iniciación de copa. Apoya cerrar el CBH como límite declarado.
- **Material en una clase.** Si cambia 0,10 o más en algún incendio, se informa en qué clase y en
  qué extremo. Si es por bajar el CBH, sólo un dato de esa clase lo resolvería, y es el camino
  concreto para reabrirlo. El loop L ya mostró que el CBH mueve el Dice (TU5 a 2,5 m: Cholila
  0,508 → 0,313), así que esto no mide si el CBH importa, sino **si el rango plausible cruza el
  umbral de iniciación** en lo que ardió.
- **Material sólo en clases sin anclaje** (TL5, TL6): el rango es mío, no de la literatura, y lo
  que habría que medir es esa clase.

Ningún resultado elige un CBH ni toca modelo-v0.

## 2. z0: diseño

**Fórmula:** la de `weather_builder.wind_height_factor`, `U(6,096 m) = U(10 m) · ln(6,096/z0) /
ln(10/z0)`. El WAF de ELMFIRE no depende de z0 (`copa.waf_elmfire`, Albini y Baughman), así que el
viento a media llama cambia en la misma proporción que el de 20 ft.

**Rango plausible declarado: 0,03–0,5 m.**

- 0,03 m: pasto corto, el terreno abierto de la OMM. Es también la rugosidad que ERA5 supone en su
  diagnóstico de viento a 10 m sobre tierra, sea cual sea la de la celda (documentación de ECMWF,
  «Surface winds»).
- 0,5 m: matorral de 2–4 m con z0 = 0,13 h (Baughman y Albini 1980), el terreno no boscoso más
  rugoso del AOI.
- Arriba de eso empieza el bosque, que ya cubre el WAF de ELMFIRE: es el doble conteo de
  `z0-dosel-001`. Se informa como referencia, no como rango: z0 = 1 m y z0 = 0,13 × 20 m = 2,6 m.

**Qué se mide:**

1. El factor 10 m → 20 ft y su cociente contra 0,22 m.
2. El viento a media llama del día 1, mediana por clase en las celdas de §1, a 0,22 m y en los dos
   extremos.
3. La velocidad de Rothermel (`copa.rothermel`) en esas celdas a la hora de máxima intensidad, en
   los extremos contra 0,22 m: un «ADJ equivalente» por incendio (mediana de la razón de ROS).
4. La fracción Van Wagner del día 1 con el viento escalado por el cociente de los extremos.

**Qué se concluye (fijado antes):**

- **No material.** Si el ADJ equivalente queda dentro de 0,95–1,05 en los seis incendios y la
  fracción Van Wagner cambia menos de 0,05, el rango plausible mueve menos que el ancho del
  intervalo de ADJ sin alarmas que se midió en v4 (~[1,05; 1,15], `AUDITORIA-FISICA.md` loop C).
  Apoya cerrar la rugosidad como límite declarado.
- **Material.** Si algún incendio sale de 0,95–1,05, el rango plausible es comparable a pasos de
  ADJ que movieron alarmas en v4 (Cholila con ADJ 1,0 contra 1,1). Medirlo de verdad pediría
  ELMFIRE con los dos extremos sobre `lw-100-001`, que no se corre sin el OK del usuario.

El ADJ equivalente es un orden de magnitud: no captura la forma ni el horizonte, y el ADJ de v4 se
midió con LW 110 % y protocolos v4.

## 3. Resultado

`uv run python scripts/diagnostico_cbh_z0.py` → `benchmarks/diagnosticos/e2e/datos/AE_cbh_z0.json`
(~2 min, sin ELMFIRE). **El control pasa en los seis incendios:** con el CBH v6, la fracción Van
Wagner del día 1 coincide exactamente con `benchmarks/diagnosticos/copa/*.json`.

### 3.1 CBH: material, y sólo por TU5 (y TU3 debajo de 1 m)

Fracción del bosque quemado con dosel del día 1 que inicia copa según Van Wagner + Rothermel:

| Incendio | Con dosel | v6 | Todas al mínimo | Todas al máximo | TU5 0,5 / 3 m | TU3 0,5 / 3 m |
|---|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 279 ha | 0,005 | 0,962 | 0,000 | 0,365 / 0,000 | 0,602 / 0,005 |
| Epuyén 2025 | 500 ha | 0,304 | 0,479 | 0,000 | 0,364 / 0,001 | 0,419 / 0,303 |
| Alerces 2024 | 370 ha | 0,034 | 0,745 | 0,000 | 0,182 / 0,000 | 0,597 / 0,034 |
| Patriada 2026 | 456 ha | 0,247 | 0,799 | 0,000 | 0,746 / 0,000 | 0,300 / 0,247 |
| Alerces 2016 | 521 ha | 0,230 | 0,645 | 0,000 | 0,404 / 0,000 | 0,471 / 0,230 |
| Cholila 2015 | 122 ha | 0,079 | 0,844 | 0,000 | 0,829 / 0,000 | 0,095 / 0,079 |

Las columnas de TU5 y TU3 son la fracción total con esa clase en el extremo y las demás en v6.

CBH umbral por clase (mediana / p90 de las celdas; inicia copa con todo CBH menor):

| Clase | v6 | Umbral, rango entre incendios | Dentro del rango declarado |
|---|---:|---|---|
| TU5 coihue, ciprés | 1,5 m | 0,84–1,63 / 1,34–2,09 m | **Sí: el valor v6 está sobre el umbral.** A 1 m inicia el 48–100 %; a 2 m, el 0–15 % |
| TU3 ñire | 1,5 m | 0,68–1,01 / 0,75–1,32 m | Sólo debajo de ~1 m: a 0,5 m inicia el 99–100 % |
| TL6 lenga | 6 m | 0,26–0,35 / 0,31–0,40 m | No: ningún CBH de 3–10 m inicia copa |
| TL2 matorral alto | 1 m | 0,07 / 0,07–0,09 m | No: ningún CBH de 0,5–2 m inicia copa |
| TL5 alerce | 4 m | — | No hay celdas TL5 quemadas el día 1 en los seis incendios |
| TL8 pino (no se varía) | 1,5 m | 0,44–0,51 / 0,48–0,54 m | — |

**Lectura, con el criterio de §1:**

- **Es material:** el cambio supera 0,10 en los seis incendios. Pero **sólo por dos clases**: TU5
  en todo su rango, en los dos sentidos, y TU3 en el extremo bajo. El valor de TU5 en v6 (1,5 m)
  está justo en el umbral de Van Wagner de lo que ardió: medio metro abajo enciende casi todo y
  medio metro arriba casi nada.
- **No es material en lenga, matorral alto ni alerce:** con el viento a media llama del día 1
  (0,5–1,3 mph, WAF 0,07–0,12), su intensidad sólo iniciaría copa con un CBH de menos de 0,4 m.
  Ninguna fuente plausible los lleva ahí. Que la lenga a 8 m diera idéntico que a 6 m en el loop L
  es lo mismo visto desde el Dice.
- El rango de TU5 y TU3 es el más anclado en literatura (la caña y el ñire sin separación vertical
  son escaleras), pero el anclaje es cualitativo: dice «bajo», no cuánto. Lo que reabriría la
  pregunta es **una medición de la altura de la escalera (CBH o base del combustible continuo) en
  coihue/ciprés con caña y en ñire**, no un inventario de dosel en general.
- Esto mide la iniciación en lo que ardió, no el Dice. El único dato de Dice es el del loop L (TU
  a 2,5 m: Cholila 0,508 → 0,313, sin alarmas). Y DIA-1-PROPUESTA §7.6 ya mostró que encender más
  copa acelera todas las horas, no sólo el primer reinicio.

### 3.2 z0: la superficie no se mueve; la copa sí, por el mismo filo de TU5

| z0 | Factor 10 m → 20 ft | Viento contra 0,22 m |
|---:|---:|---:|
| 0,03 m (pasto corto; diagnóstico de ERA5) | 0,915 | ×1,051 |
| **0,22 m (v6)** | **0,870** | ×1 |
| 0,5 m (matorral de 2–4 m) | 0,835 | ×0,959 |
| 1 m (referencia, bosque) | 0,785 | ×0,902 |
| 2,6 m (referencia, 0,13 × 20 m) | 0,633 | ×0,727 |

El WAF no depende de z0, así que el viento a media llama cambia en la misma proporción: en TU5, que
anda en 0,47–0,99 mph, menos de 0,05 mph.

| Incendio | ADJ eq. z0 0,03 / 0,5 | Copa v6 | Copa z0 0,03 / 0,5 | Referencia z0 2,6: ADJ eq. / copa |
|---|---|---:|---|---|
| Alerces 2023 | 1,039 / 0,969 | 0,005 | 0,005 / 0,004 | 0,804 / 0,001 |
| Epuyén 2025 | 1,032 / 0,975 | 0,304 | 0,339 / 0,272 | 0,838 / 0,137 |
| Alerces 2024 | 1,039 / 0,970 | 0,034 | 0,077 / 0,016 | 0,806 / 0,001 |
| Patriada 2026 | 1,024 / 0,981 | 0,247 | **0,354** / 0,202 | 0,877 / 0,064 |
| Alerces 2016 | 1,026 / 0,980 | 0,230 | **0,317** / **0,171** | 0,867 / 0,041 |
| Cholila 2015 | 1,027 / 0,979 | 0,079 | **0,157** / 0,057 | 0,863 / 0,011 |

En negrita, los cambios de copa ≥ 0,05.

**Lectura, con el criterio de §2:**

- **La superficie no es material:** el ADJ equivalente queda en 0,97–1,04 en los seis, dentro de
  0,95–1,05. Es menos que la mitad del paso entre las recetas de ADJ medidas en v4.
- **La segunda condición no se cumple:** la copa cambia ≥ 0,05 en tres de seis con z0 = 0,03
  (Patriada +0,107, Alerces 2016 +0,087, Cholila +0,078) y en uno con 0,5 (Alerces 2016 −0,059). El
  resultado no cae en «no material» ni en el «material» que se había previsto (ADJ fuera de la
  banda): **es intermedio, y la causa es la de 3.1.** Un ×1,04 de intensidad mueve el CBH umbral
  ×1,04^(2/3) = ×1,026, y sólo TU5 tiene su umbral a menos de un 3 % de su CBH. No es una
  sensibilidad propia de z0: es TU5 en el filo, empujado por el viento.
- La referencia de bosque (z0 = 2,6 m) es el doble conteo: ADJ eq. 0,80–0,88 y copa casi nula.
  Coincide con lo que mostró `z0-dosel-001`.
- **Sobre qué reabriría z0.** El 0,22 m no representa la rugosidad del AOI: es el valor que
  reproduce el factor 0,87 entre el viento a 10 m de una estación OMM y el de 20 ft de los índices
  de incendios (el comentario de `weather_builder.py`; ELMFIRE usa el mismo 0,87 en
  `CROWN_SPREAD_RATE`). Un producto de rugosidad regional mediría otra cosa, la del dosel, que ya
  está en el WAF. Lo que lo reabriría es una medición del cociente 20 ft / 10 m en terreno abierto
  del AOI, o un contraste de ERA5/GFS con estaciones, y ese pedido se canceló el 2026-10-31.

### 3.3 Qué no dice esta nota

- No elige un CBH ni un z0. No toca modelo-v0, ni las recetas, ni el conjunto de prueba.
- El lado ELMFIRE es la reimplementación sin pendiente de `copa.py`: un orden de magnitud, no
  ELMFIRE byte a byte (`DIA-1-PROPUESTA.md` §7.4, límites).
- Medir el efecto en el Dice pediría correr ELMFIRE con TU5 en sus extremos sobre `lw-100-001`. No
  se corrió.

## 4. Evidencia externa relevada (2026-10-31)

¿Hay algo que cuente como «evidencia externa nueva» en el sentido de la regla de parada? **No se
encontró nada que mida lo que resultó material** (la altura de la escalera en TU5 y TU3) dentro del
AOI ni en un sitio comparable. Las búsquedas fueron web (no bases bibliográficas con suscripción), así
que un dato no publicado o de circulación restringida puede existir igual.

### 4.1 CBH

| Fuente | Qué mide | Resolución, cobertura | Acceso, licencia | Independencia del benchmark | ¿Sirve para TU5/TU3? |
|---|---|---|---|---|---|
| Segundo Inventario Nacional de Bosques Nativos (INBN2), [manual de campo](https://www.researchgate.net/publication/335868153_Manual_de_campo_Segundo_Inventario_Nacional_de_Bosques_Nativos) e [informe regional BAP](https://www.researchgate.net/publication/342424254_NUESTROS_BOSQUES_EN_NUMEROS_-_Informe_Regional_del_Bosque_Andino_Patagonico) | DAP, altura total, longitud de fuste y diámetro de copa; según extractos, el fuste hasta la primera rama sólo en Monte (bosque bajo, donde entra el ñire). No se vio una variable de altura de inicio de copa viva ni de sotobosque | Parcelas permanentes sistemáticas en la región andino-patagónica | Informes públicos; datos de parcela por pedido al Ministerio de Ambiente. No se verificó si hay parcelas dentro del AOI | Independiente (inventario forestal) | **Quizás para TU3:** el fuste hasta la primera rama del ñire es un sustituto del CBH. No para TU5: no mide la caña. Sin verificar en el manual completo (el PDF oficial dio 404) |
| INFOR (Chile), Martin et al. 2018, [Diagramas de manejo de densidad para lenga de Aysén y Magallanes](https://investigacion.conaf.cl/archivos/repositorio_documento/2020/08/INFORME_FINAL.pdf) | Altura de inicio de copa viva en renovales de lenga (parcelas Prodan y árboles de análisis fustal) | Aysén y Magallanes (≥ 44° S); renovales densos manejados | Informe público; la medición está en los métodos pero el informe no publica los valores | Independiente | No: es lenga, que no resultó material, y fuera del AOI |
| Paritsis, Veblen y Holz 2015, [J Veg Sci 26:89](https://ri.conicet.gov.ar/handle/11336/12143) | Distribución vertical del combustible fino en lenga quemada y no quemada (NO de Chubut) | Parcelas | Artículo | Independiente | No: es lenga (ya es la fuente de v6) |
| Lencinas, Díaz y Mohr-Bell 2025, *Southern Forests*, [doi:10.2989/20702620.2025.2601032](https://doi.org/10.2989/20702620.2025.2601032) | LiDAR desde dron en bosques andino-patagónicos, usado para validar mapas globales de altura | Sitios no verificados | Artículo; las nubes de puntos no se encontraron publicadas (CIEFAP) | Independiente | **Quizás:** una nube de dron en coihue con caña permitiría estimar la base del combustible continuo. Habría que pedir los datos y ver si cubre TU5 |
| GEDI L2B ([catálogo](https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI02_B_002)) | Perfil vertical de cobertura y de PAI desde lidar espacial | Huellas de ~25 m; perfil cada 5 m; 51,6° N–51,6° S (cubre el AOI); desde abril de 2019, sin datos entre el 17-03-2023 y abril de 2024 ([NASA](https://www.earthdata.nasa.gov/data/catalog/lpcloud-gedi02-a-003)) | Abierto (NASA) | Independiente, pero dentro de las cicatrices de 2015–2016 mide bosque ya quemado | **No:** con un paso de 5 m no resuelve un CBH de 0,5–3 m, que es donde está el umbral. Hay métodos de CBH con todo el perfil RH (Zhao et al. 2026, [Remote Sensing 18:2092](https://www.citedrive.com/en/discovery/mapping-canopy-base-height-through-integration-of-gedi-and-sentinel-2-data/)), pero sin validación en Patagonia ni bajo caña |
| Bianchi, Dentoni y otros 2012, [modelos de combustibles del ecotono bosque-estepa](https://sidalc.net/search/Record/KOHA-OAI-FCF:11314/Similar) | Asociaciones arbustivas según su respuesta al fuego | — | Ficha bibliográfica; no se accedió al texto | Independiente | No se pudo verificar |

Para ciprés (*Austrocedrus*) sólo se encontraron descripciones cualitativas (corteza fina, ramas
secas persistentes que dan acceso a la copa), y para ñire en Santa Cruz, alturas dominantes y
coberturas de los sistemas silvopastoriles de Peri y colegas, sin CBH.

### 4.2 Rugosidad

| Fuente | Qué mide | Resolución, cobertura | Acceso, licencia | Independencia | ¿Sirve? |
|---|---|---|---|---|---|
| ERA5, rugosidad pronosticada (`fsr`, parámetro 244) | z0 del modelo; sobre tierra, fijo por tipo de cobertura (tabla del IFS), casi sin variación temporal salvo pastizal y cultivo ([foro ECMWF](https://forum.ecmwf.int/t/roughness-length/12367)) | 0,25° (~30 km) | Copernicus, abierto | No es una medición: es una tabla del modelo | No |
| ECMWF, [«Surface winds»](https://confluence.ecmwf.int/x/lXI0Dw) | El viento a 10 m de ERA5/IFS es un diagnóstico que supone z0 = 0,03 m (pasto corto), sea cual sea la rugosidad de la celda | Global | Documentación pública | — | Sí, para fijar el extremo bajo del rango (§2). No reabre nada: 0,87 ya es el factor entre una estación OMM y una de 20 ft |
| Mapas globales de altura de dosel: Potapov et al. 2021 ([GLAD, 30 m, 2019](https://zenodo.org/records/4008406)); Lang et al. 2023 (ETH, 10 m, ya es el CH del repo); HRCH y GMTCH evaluados en Patagonia por Lencinas et al. 2025 | Altura del dosel (z0 ≈ 0,13 h) | 1–30 m; cubren el AOI | Abiertos | Independientes | No: es la rugosidad del dosel, la que duplica el WAF. Además, sesgados en el bosque andino-patagónico (Lencinas et al. 2025) |
| Rugosidad MODIS global de 1 km (UMD/ESSIC) y LBA-ECO LC-15 ([ORNL](https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1182)) | z0 y desplazamiento | 1 km | La global no está publicada; la de ORNL sólo cubre la Amazonia | — | No |
| Perfiles de viento o torres de flujo en bosques patagónicos | — | — | No se encontró ninguno | — | — |
