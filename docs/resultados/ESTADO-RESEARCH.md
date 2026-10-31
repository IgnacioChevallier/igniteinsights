# Estado del research

> Fuente canónica desde el 2026-10-04. Reemplaza las secciones de “estado actual” y “próximos
> pasos” dispersas en documentos anteriores. La bitácora física completa permanece en
> `docs/resultados/AUDITORIA-FISICA.md`.

## 1. Estado

La fase de ajuste de receta está **cerrada**. La receta `lw-100-001` sobre los protocolos v6 fue
promovida a **`modelo-v0`**, el primer snapshot que pasa el gate productivo. Su identidad
inmutable está en `benchmarks/modelos/modelo-v0.json`.

Convención:

- **receta:** configuración experimental que puede aplicarse a distintos casos;
- **iteración:** receta × caso, con manifiesto, insumos y salidas por hash;
- **modelo:** receta, casos, resultados y criterios congelados después de pasar un gate.

Promover una receta no cambia ni renombra sus iteraciones históricas. `modelo-v0` referencia
`lw-100-001`; no existe una “receta modelo-v0”.

## 2. Configuración de modelo-v0

- ELMFIRE 2025.0212.
- Protocolos v6.
- CCS-BAP del último año anterior al incendio.
- Humedad viva leñosa (LW): 100 %.
- ADJ: 1,0.
- Estepa → GR2; vegetación altoandina sobre 1.300 m → NB9.
- Remanente de disturbio reciente → SH3.
- CBH por tipo de bosque y CBD de pino de 0,16 kg/m³.
- Sin dosel donde Hansen registra pérdida anterior al incendio.
- Alerces 2023 puntuado a 54 h, cuando el área FIRMS deja de crecer.

## 3. Evidencia congelada

La partición tiene siete incendios de calibración y cuatro de prueba. Las Golondrinas se conserva
en las tablas, pero es un caso límite meteorológico y no participa de la restricción de sesgo.

| Conjunto | n | Dice medio | Mediana | Alarmas |
|---|---:|---:|---:|---:|
| Calibración | 7 | 0,439 | 0,501 | 0 sin el caso límite |
| Validación cruzada | 7 | 0,416 | 0,496 | — |
| Prueba | 4 | 0,191 | 0,167 | 2 |
| Robustez de ignición | 21 | 0,461 | 0,497 | 2 |

La reproducción ejecutable del cierre comparó byte a byte un caso GFS (4/4 ventanas iguales)
y uno ERA5 (3/3 ventanas iguales) contra sus artefactos congelados.

La validación cruzada vigente fue regenerada el 2026-10-04 con las cinco recetas que tienen
iteraciones completas sobre los siete casos v6. Reemplaza el valor 0,437/0,490 que había quedado
escrito durante el loop M con otro conjunto de recetas completas.

El resultado de prueba es deliberadamente descriptivo: no se usa para volver a elegir LW, ADJ,
crosswalk, CBH ni viento.

**Propuesta (2026-10-31): P-24 como métrica principal del producto.** Las cifras de arriba miden la
cadena: 72–120 h desde el punto de ignición reportado y sin supresión. Son el benchmark de la física.
La app hace otra cosa: arranca en la primera detección VIIRS y re-siembra en cada pasada (P-24). Por
eso se propone informar como métrica del producto el Dice del crecimiento a 12 y 24 h desde la
última pasada, con el pronóstico disponible, junto a la cadena y sin reemplazar el 0,191:

| Conjunto | P-24, mediana del Dice a 12 / 24 h | Cadena, mismas ventanas | P-24 gana a la cadena | Clima |
|---|---|---|---|---|
| Calibración (4 incendios GFS) | 0,192 / 0,262 | 0,085 / 0,151 | 4 de 4 / 3 de 4 | pronóstico GFS (nota Z) |
| Prueba (4) | 0,084 / 0,145 | 0,009 / 0,026 | 4 de 4 / 4 de 4 | pronóstico GFS en El Turbio y Puerto Café; ERA5 en Epuyén 2019 y Alerces 2015 (nota AB) |

En prueba, P-24 gana a la cadena en los cuatro casos. Pero el nivel absoluto es la mitad que en
calibración, y la ventaja sobre la persistencia es chica (+0,021 y +0,038, en 3 de 4). Las notas:
`diagnostico-e2e/notas/Z-p24-pronostico-gfs.md` y `AB-p24-prueba.md`.

La tabla por caso, su lectura y la sensibilidad al horizonte (2026-10-19) están en
`docs/resultados/MODELO-V0.md`. Volver a puntuar las corridas congeladas cortadas a 24–120 h
muestra que el Dice de calibración crece con el horizonte: con un tope de 72 h la media bajaría
a 0,409. En prueba, sólo Epuyén 2019 empeora con el horizonte largo (supresión).

## 4. Qué quedó demostrado

1. La interfaz original con ELMFIRE tenía errores materiales; los cinco hallazgos de la auditoría,
   la orientación del terreno y los problemas de preparación asociados están corregidos y
   cubiertos por pruebas físicas.
2. Con la interfaz correcta no hace falta un ajuste global de velocidad: ADJ queda en 1.
3. LW 100 % es la única perilla regional adoptada.
4. El crosswalk y el dosel v6 mejoran la calibración y reducen las alarmas, aunque no resuelven
   la transferencia a todos los regímenes de incendio.
5. La comparación controlada v5 muestra que CCS-BAP supera a WorldCover en los incendios sin
   fuga temporal y empata globalmente con MapBiomas. Esa comparación todavía no usa el crosswalk
   final de modelo-v0 y, por eso, no es el cierre definitivo de mapas.

## 5. Qué no queda pendiente como receta

- ADJ, LW, paso temporal, rugosidad, orientación, CBH/CBD y tratamiento de pérdida previa ya
  tienen una decisión.
- Pavesas, supresión, ERA5 ×1,3, dosel abierto en matorral, WindNinja completo y las alternativas
  de estepa fueron medidos y no adoptados.
- m10/m100 carece de una base física completa, pero resultó insensible en este benchmark. Se
  cerró como límite declarado el 2026-10-31: no se buscan mediciones.

No queda otro barrido justificable con los mismos datos. La regla de parada de modelo-v0 es:
**sólo se reabre por un bug físico o por evidencia externa nueva**, no por mejorar un caso de
prueba.

## 6. Alcance, límites y pendientes

Estado de cierre al 2026-10-31. Tres categorías: lo que queda fuera del alcance del producto, los
límites declarados (cerrados: sólo se reabren por un bug físico o por evidencia externa nueva) y lo
pendiente. El detalle de cada límite está en `docs/resultados/RIESGOS_Y_SUPOSICIONES.md`.

### 6.1 Fuera del alcance

- **Las 2–6 h anteriores a la primera pasada VIIRS** (decisión del usuario, 2026-10-31). La app
  arranca en la primera detección VIIRS, así que lo que arde antes no es parte del producto. Sólo
  aparece porque el benchmark de cadena arranca en el punto de ignición reportado: ahí está casi
  todo el déficit del día 1 (6–21× a 24 h desde la ignición en cuatro de seis incendios; RIESGOS §2).
- **El ensamble paramétrico** (decisión del usuario, 2026-10-19;
  `docs/out-of-scope/ENSAMBLE-PARAMETRICO.md`).

### 6.2 Límites declarados (cerrados)

- **Día 1 dentro del alcance: el residuo de P-24 después de la primera pasada.** Desde ahí, el
  pronóstico a 12–24 h con reinicio en cada pasada (protocolo P-24), con el pronóstico GFS que se
  tenía en cada reinicio, mejora a la cadena en 4 de 4 incendios GFS a 12 h (+0,118) y en 3 de 4 a
  24 h (+0,154) (`diagnostico-e2e/notas/Z-p24-pronostico-gfs.md`). El error de pronóstico cuesta
  −0,001 frente a los análisis; las cifras previas de 6 de 6 y 5 de 6 son hindcast (análisis GFS
  posteriores al reinicio, ERA5 en Cholila y Alerces 2016). El primer reinicio queda 2–4,5× por
  debajo en Patriada y Alerces 2024 (sesgo 0,44 y 0,24 a 24 h con el pronóstico real). Ese residuo
  coincide con copa que el acople Van Wagner + Rothermel de ELMFIRE no enciende
  (`docs/resultados/DIA-1-PROPUESTA.md` §7.3–7.6).
- **P-24 con reanálisis en Cholila 2015, Alerces 2016, Epuyén 2019 y Alerces 2015.** Para esas fechas
  el GFS sólo está archivado cada 3 h, así que su P-24 corre con ERA5 y no es pronóstico (Z §2.2,
  AB §1.1). El usuario decidió el 2026-10-31 no bajar ese archivo (~25 GB, trihorario): interpolarlo
  cambiaría a la vez producto, resolución y plazo, y no aislaría el error de pronóstico.
- **Reconstrucción del perímetro FIRMS** (decisión del usuario, 2026-10-31). No participa en la
  calibración de ignición puntual. En P-24 da pronósticos casi iguales a los de arrancar desde la
  cicatriz real (`DIA-1-PROPUESTA.md` §7.3, `diagnostico-e2e/notas/U-reconstruccion-semilla.md`).
  Sólo la reabre un perímetro operativo independiente (vuelo IR, partes).
- **Supresión:** El Turbio y Epuyén 2019 no son reproducidos por el módulo disponible.
- **Transferencia:** en prueba, la cadena da 0,191 / 0,167 con dos alarmas, y P-24 da 0,084 / 0,145
  de mediana a 12 / 24 h, ganándole a la cadena en 4 de 4 (§3, `diagnostico-e2e/notas/AB-p24-prueba.md`).
- **Viento de superficie:** una estación cercana a Alerces 2016 o Cholila permitiría contrastar
  ERA5 con WindNinja. Las series pedidas al INTA y a Bosques de Chubut no llegaron y el pedido se
  canceló el 2026-10-31: no reabre ninguna decisión.
- **Pavesas condicionadas (Y, 2026-10-23): no se usan.** Techo por incendio 0,470; ninguna regla
  con umbral previo pasa de 0,439 sin alarmas. Un orden exploratorio por la intensidad del modelo
  base coincide con el techo, con márgenes de menos de un punto, y queda registrado como hipótesis
  para incendios nuevos. Reabre sólo una prueba independiente de esa regla (d1, Y §4); la otra
  condición, viento observado, se canceló con el pedido al INTA
  (`docs/resultados/diagnostico-e2e/notas/Y-pavesas-condicionadas.md`).
- **Las Golondrinas:** hacen falta a la vez el evento meteorológico que el GFS no tiene y las
  pavesas, que modelo-v0 no tiene. Juntos dan 9.088 ha y Dice 0,545, como diagnóstico. Por separado,
  el SYNOP da ×8 y las pavesas ×1,0
  (`docs/resultados/diagnostico-e2e/notas/G-golondrinas-meteo-observada.md` §7,
  `X-pavesas-calibracion.md`). Las pavesas fuertes sobre la calibración v6 dan media 0,451 con 3
  alarmas nuevas y no pasan la puerta.
- **Humedad en altura:** la lenga de altura arde tan seca como el valle. Las correcciones del aire no
  alcanzan y no existe una medición de humedad de hojarasca bajo lenga. La lenga achaparrada sigue
  en SH8, con su limitación declarada (`docs/resultados/HUMEDAD-ALTURA-PROPUESTA.md`).
- **m10/m100:** sin base física completa, pero insensible en este benchmark. Cerrado el 2026-10-31:
  no se buscan mediciones.
- **Islas en la referencia truncada** y **sub-dispersión de GEFS en la capa de acuerdo**: declaradas
  en `PENDING_PARAMETERS.md` §3 y en §8.

Ninguno bloquea la comparación de mapas condicionada a modelo-v0.

El ensamble meteorológico GEFS se cerró el 2026-10-17 con 23/23 backtests contemporáneos de
calibración, de cuatro incendios, con 31/31 miembros cada uno. Todos pasaron la integridad, sin
sustituciones ni fallos científicos. La capa **“Acuerdo del ensamble”** se adopta con
limitaciones como comunicación de sensibilidad meteorológica y ya está en el sidebar, apagada
por defecto. No mejora predictivamente a c00 de forma consistente: en medianas por incendio,
≥0,80 gana en 2/4 incendios a 12 h y en 3/4 a 24 h por ≤0,003 de IoU, ≥0,50 es equivalente y
≥0,10 gana recall a costa de área. La banda es angosta (4–14 % del área de c00) y queda
crecimiento observado fuera de ≥0,10, así que la leyenda lo advierte. No es probabilidad. La evaluación con usuarios
reales está pendiente (§6.3). Los resultados están en
`docs/resultados/ENSAMBLE-BACKTESTS-CONSOLIDADO.md`, el método en
`docs/resultados/ENSAMBLE-METEOROLOGICO-POC.md` y la semántica en
`docs/resultados/DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md`.

Dos problemas de la app quedaron resueltos el 2026-10-12, sin cambiar modelo-v0
(`docs/resultados/LO-YA-QUEMADO-PROPUESTA.md`):

- Lo ya quemado: la app reasigna por edad el combustible de las quemas posteriores al mapa
  (protocolo de no regresión LYQ-3: 0,439 / 0,501).
- Ingesta histórica de FIRMS: la app pide las fuentes SP y las NRT.

### 6.3 Pendiente

1. **La evaluación con usuarios de la capa «Acuerdo del ensamble»**
   (`docs/resultados/PROTOCOLO-EVALUACION-ACUERDO-ENSAMBLE.md`). La hace el autor con personas reales.
2. **Llevar los resultados al informe** (`../informe`). Es trabajo de ese repositorio, no de este.

Abiertos. Lo que el autor decidió el 2026-10-31 está en cada punto:

- **CBH de bosque nativo y rugosidad regional** (`PENDING_PARAMETERS.md` §2): siguen abiertas por
  decisión del autor. No bloquean el modelo. La reconstrucción del perímetro FIRMS, que estaba en la
  misma lista, pasó a límite declarado (§6.2).
- **Del ensamble:** CPU/RSS del runner y latencia operativa
  (`DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md`). El mínimo operativo de 24/31 se ratificó
  como decisión de producto el 2026-10-31.
- la semilla conexa de P-24, que la app en tiempo real todavía no aplica (`PENDING_PARAMETERS.md` §1).

## 7. Comparación final de mapas

La comparación predefinida en `docs/resultados/COMPARACION-MAPAS-MODELO-V0.md` fue ejecutada
sobre los once casos. Los controles CCS-BAP reprodujeron modelo-v0 byte a byte.

- Sin fuga temporal (6 incendios): Dice 0,415 CCS-BAP, 0,118 WorldCover y 0,378 MapBiomas.
- Calibración sin el límite: 0,510 CCS-BAP, 0,131 WorldCover y 0,430 MapBiomas.
- Prueba: 0,191 CCS-BAP, 0,272 WorldCover y 0,284 MapBiomas.

WorldCover queda descartado como fuente principal. CCS-BAP permanece en modelo-v0; MapBiomas es
competitivo y no hay evidencia para afirmar superioridad general de CCS-BAP sobre él, pero sí
no inferioridad: con 95 % de confianza (Hodges-Lehmann, cota exacta de Wilcoxon), CCS-BAP no
pierde más de 0,098 de Dice en los seis casos sin fuga, dentro de un margen de 0,130 (la mitad
de la ventaja de MapBiomas sobre WorldCover, fijado después de ver los datos). El holdout
no se usa retrospectivamente para cambiar el modelo. Resultado completo:
`docs/resultados/COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`.

## 8. Diagnóstico de precisión (2026-10-18)

Un diagnóstico e2e, sin ELMFIRE y sin tocar modelo-v0, buscó por qué la predicción no es mejor
(`docs/resultados/DIAGNOSTICO-PRECISION-E2E.md`, notas en `docs/resultados/diagnostico-e2e/`).
Encontró que el Dice lo decide **la forma, no el área**. En P-24 el crecimiento sale ×4 errado de
área, pero igualar el área no sube el Dice: el modelo crece casi isótropo alrededor de la semilla
(elongación 1,5 contra 2,9–3,2 observada) y con el rumbo errado en ~60°. La referencia no explica
la brecha: el techo está en ~0,7–0,9 y la corrección de las islas no vistas deja modelo-v0 en
0,440. Tampoco el ensamble GEFS prueba que la meteorología no domine: está sub-dispersado de
entrada (3–11° contra un error del GFS en estaciones de σ 30–41°). Se corrigió un sesgo a favor de
P-24: el anillo ya visto al reiniciar contaba como crecimiento. Sin él, P-24 sigue ganando a la
cadena en 6 de 6 a 12 h, pero por +0,096 y no por +0,168 (hindcast; con el pronóstico real, nota Z). Desde el 2026-10-18,
`pronostico.puntuar` excluye ese anillo y las cifras de `DIA-1-PROPUESTA.md` §7, RIESGOS y
PENDING quedaron corregidas. La versión anterior además tenía invertidas las semillas FIRMS y
oráculo. El residuo del día 1 pasa de 2–3,5× a 2–4,5×. La severidad dNBR no permitió
afirmar copa en el día 1 (indiscriminado). La puerta meteorológica (frente 4) se cerró el
2026-10-18 con "no pasa": contra SYNOP crudo, SMN WRF 4 km mejora al GFS sólo en El Bolsón
(n = 21) y empeora la dirección en Esquel y Futaleufú, así que no se ingiere
(`diagnostico-e2e/notas/W-viento-estaciones.md`). El diagnóstico de isotropía (frente 2) también se
cerró el 2026-10-18, con "método" y no "abrigo". Bajo el dosel el crecimiento predicho no es más
redondo que en lo abierto, pero el 70 % brota de semilla fuera de la cicatriz, y ahí está casi todo
el exceso de flanco (`diagnostico-e2e/notas/I-isotropia.md`). Por eso el abrigo del dosel
(`CROWN_RATIO`, frente 3) no se abre. La semilla de afuera se descompuso el 2026-10-18
(`diagnostico-e2e/notas/T-semilla.md`). El 26 % son detecciones de otros incendios, casi todas en
Cholila, y se resuelve con un filtro de conexión a la ignición. El resto es el píxel de 375 m, el
relleno del casco y quema que la cicatriz no marca. El filtro no mueve la mediana de P-24. El
2026-10-19 se midió, sin ELMFIRE, si cambiar la regla de reconstrucción ayuda
(`diagnostico-e2e/notas/U-reconstruccion-semilla.md`). Se probó sembrar sólo con las huellas del
píxel, y también el casco sin buffer: ninguna de las dos mueve el Dice (±0,003). Crecer sólo desde el
frente activo gana +0,026 a 12 h y pierde −0,027 a 24 h, así que tampoco pasa. La reconstrucción
se mantiene. El crecimiento "fuera de la cicatriz" es el perímetro inactivo, que ELMFIRE quema igual
que la cabeza, y queda como límite. El 2026-10-19 el usuario decidió que el ensamble paramétrico no
entra en la tesis (`docs/out-of-scope/ENSAMBLE-PARAMETRICO.md`). La sub-dispersión de GEFS queda
como limitación declarada de la capa de acuerdo.
El 2026-10-19 se cerró el truncado asimétrico (`diagnostico-e2e/notas/T-truncado.md`). Puntuar sólo
dentro de lo visto premia quemar todo el dominio. Excluir sólo las islas no vistas vale ≤ 0,01 y no
cambia la receta ni P-24. El 2026-10-22 se corrió el filtro conexo en Cholila
(`cholila-2015/pronostico-v7`, 5 ventanas nuevas; `diagnostico-e2e/notas/T-semilla-v7.md` §4). El Dice
de Cholila pasa de 0,070 / 0,262 a 0,078 / 0,327 a 12 / 24 h, igual que la aproximación, y las medianas
de P-24 no cambian. El usuario adoptó v7 ese mismo día: los 6 casos de P-24 pasan a `*/pronostico-v7`, y los otros 5 paquetes son idénticos a v6 (tabla en `data/benchmark/p24/tabla-pronostico-v7.md`, cifras en `DIA-1-PROPUESTA.md` §7). El mismo día se cerró
offline la humedad viva por especie (frente 6, `diagnostico-e2e/notas/V-humedad-viva.md`). Con el LFMC
medido por especie, el modelo se aleja de la ROS observada en 5 de 7 clases.

## 9. Mapa documental

- `docs/resultados/`: estado vigente, modelo promovido, auditoría y comparaciones.
- `docs/resultados/DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md`: afirmación central de la
  tesis, alcance operacional, definición de acuerdo del ensamble, presentación en la interfaz y
  protocolo congelado de evaluación con usuarios.
- `docs/crosswalk/`: tablas activas y decisiones de combustible/dosel.
- `docs/historico/`: planes, propuestas y resultados superados que se conservan como registro.
- raíz: documentación operativa o transversal que no pertenece a esas categorías.
- Informe de tesis: repositorio aparte, `../informe` (`github.com/IgnacioChevallier/informe`).
  Se encuadra como producto y se evalúa con su rúbrica de productos. Los resultados de este repo
  se incorporan allí.
