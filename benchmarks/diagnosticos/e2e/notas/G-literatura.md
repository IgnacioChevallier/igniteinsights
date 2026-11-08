# G. Literatura: estado del arte para mejorar la precisión

Nota de la Tarea G del diagnóstico. Revisión hecha el 2026-10-17.

**Regla de citas.** Sólo cito páginas que abrí con WebFetch. Cuando sólo vi el resumen lo marco
"(sólo abstract)". Varias editoriales (ScienceDirect, MDPI, Springer, HAL, Wiley) devolvieron 403
y no pude abrirlas: lo que no pude leer queda en "No verificado" al final, sin DOI.

**Qué ya estaba en el repo.** De `DIA-1-PROPUESTA.md` §Referencias ya figuran: Cardil et al. 2019
(los dos), Cruz y Alexander 2010, Cruz et al. 2004 y 2005, Duff et al. 2016, Lautenberger 2013,
Rochoux et al. 2014, Srivas et al. 2016 y arXiv 2204.00686 (Haley). De la literatura patagónica ya
están Bianchi y Defossé 2015, Cobar y Carranza 2014, Tiribelli (tesis), Blackhall et al. 2017
(en `docs/referencias/`), y Mermoz et al. 2005, Paritsis et al. 2015, Barberá et al. y Tiribelli et
al. (en `HUMEDAD-ALTURA-PROPUESTA.md`). Donde repito una de esas lo digo. Lo nuevo son las demás.

**Nota de métrica.** El Dice de `ESTADO-RESEARCH.md` (0,439 calibración, 0,191 prueba) es el
índice de Sørensen: son lo mismo. Con el Jaccard, J = D / (2 − D), así que Dice 0,439 equivale a
Jaccard 0,283 y Dice 0,191 a Jaccard 0,106. Hay que comparar siempre Dice con Dice.

## Las 8 más útiles

1. Cruz y Alexander (2013): el error de ROS de los modelos operativos es de 20 a 310 %.
2. Price y Germino (2022): el mapa de combustible movió el Sørensen de FARSITE de 0,38 a 0,70.
3. Sá et al. (2022): Sørensen 0,60 en los 9 mayores incendios de Portugal, tras calibrar.
4. Carrasco et al. (2019): ajustar factores de ROS por combustible rinde ~5 % más que uno global.
5. Allaire et al. (2021): un ensamble calibrado baja ROS y sobreestimación sin perder cobertura.
6. Reeves y Swedosh (2025): correr el clima un τ reproduce el retardo de humedad fina.
7. Wagenbrenner et al. (2016) y Forthofer et al. (2014): WindNinja ayuda con viento fuerte; mixto en flujos térmicos.
8. Cruz et al. (2005): Rothermel 1991 subestima el fuego de copa con error de 66 a 84 %.

## 1. Asimilación de datos y calibración secuencial

**Rochoux, Ricci, Lucor, Cuenot y Trouvé (2014).** *Towards predictive data-driven simulations of
wildfire spread – Part I: Reduced-cost Ensemble Kalman Filter based on a Polynomial Chaos surrogate
model for parameter estimation.* NHESS 14: 2951–2973. https://doi.org/10.5194/nhess-14-2951-2014
(sólo abstract). EnKF secuencial que corrige de manera uniforme el viento y la biomasa del ROS de
Rothermel al llegar posiciones del frente. Un sustituto de caos polinómico da un desempeño parecido
al EnKF estándar a mucho menor costo. Concluye que la habilidad del pronóstico depende mucho de
cuánto varía el error de los parámetros en el espacio y en el tiempo. Ya citada en el repo.

**Rochoux, Emery, Ricci, Cuenot y Trouvé (2015).** *Towards predictive data-driven simulations of
wildfire spread – Part II: Ensemble Kalman Filter for the state estimation of a front-tracking
simulator of wildfire spread.* NHESS 15: 1721–1739. https://doi.org/10.5194/nhess-15-1721-2015
(sólo abstract). Corrige directamente las coordenadas del frente. Hace falta que los miembros
varíen la ignición y los parámetros de ROS a la vez para representar bien las correlaciones del
error. La ventana de asimilación debe ajustarse a cuánto dura la condición inicial y a qué tan
rápido cambia el ambiente. Corrige frentes inexactos y mejora los plazos largos, sobre un fuego
de pasto a escala reducida. No da números en el resumen.

**Mandel, Beezley, Chakraborty, Coen, Douglas, Vodacek y Wang (2008).** *Towards a Real-Time Data
Driven Wildland Fire Model.* IPDPS 2008, pp. 1–5; arXiv 0801.3875. https://arxiv.org/abs/0801.3875
(sólo abstract). EnKF "morphing" sobre un modelo level-set acoplado a WRF: corrige posición y
amplitud, con imágenes térmicas como observación. Es la formulación apropiada para errores de
posición del frente que un EnKF aditivo no corrige. No trae números en el resumen.

**Subramanian, Tan, de Callafon, Crawl y Altintas (2020).** *Recursive Updates of Wildfire Perimeters
using Barrier Points and Ensemble Kalman Filtering.* ICCS 2020, LNCS; doi 10.1007/978-3-030-50433-5_18
(el DOI figura en el PDF que abrí; URL: https://www.iccs-meeting.org/archive/iccs2020/papers/121420217.pdf).
Texto del resumen e introducción. FARSITE más EnKF sobre perímetros observados; los puntos fijos del
perímetro (barrera) se usan como restricción. Dicen que da "una mejora significativa" del perímetro
a futuro en el incendio Sandfire 2016 (California). El resumen no da un número. Menciona además a
Srivas et al. (2016) y su EnKF con factores de ajuste por combustible.

**Dabrowski, Huston, Hilton, Mangeon y Kuhnert (2022).** *Towards Data Assimilation in Level-Set
Wildfire Models Using Bayesian Filtering.* arXiv 2206.08501. https://arxiv.org/abs/2206.08501 (vi
también la versión HTML). Compara filtro de partículas (100 partículas) y EnKF (10 muestras) en un
modelo level-set, con una quema controlada de 90 s cartografiada cada 10 s. El EnKF resulta menos
exacto (los frentes se expanden demasiado rápido) y el filtro de partículas es el más prometedor.
No hay métricas cuantitativas; la comparación es visual.

**Cardil, Monedero, Silva y Ramírez (2019).** *Adjusting the rate of spread of fire simulations in
real-time.* Ecological Modelling 395: 39–44. https://doi.org/10.1016/j.ecolmodel.2019.01.017
(sólo abstract, vía https://nrfirescience.org/node/19327). Wildfire Analyst calcula, **por modelo
de combustible**, el factor de ajuste de ROS que minimiza el error de tiempo de llegada en puntos de
control con llegada observada. Dos casos reales muestran menos error, sin cifras en el resumen. Se
puede resolver en tiempo real y aplica a cualquier modelo empírico. Ya citada en el repo.

**Cardil, Monedero, Ramírez y Silva (2019).** *Assessing and reinitializing wildland fire
simulations through satellite active fire data.* J. Environ. Manage. 231: 996–1003. (sólo abstract,
vía https://nrfirescience.org/node/19103). Tres incendios grandes (EE. UU., Chile, España). La
discrepancia con las detecciones activas crece con la duración del incendio. Reiniciar en casi
tiempo real "mejoró sustancialmente" la exactitud en los tres casos. Sin cifras en el resumen. Ya
citada en el repo.

**Carrasco, Pais, Shen y Weintraub (2019).** *Adjusting Rate of Spread Factors through
Derivative-Free Optimization: A New Methodology to Improve the Performance of Forest Fire
Simulators.* arXiv 1909.05949. https://ar5iv.arxiv.org/html/1909.05949 (preprint; no vi revista).
Optimiza cuatro factores (ROS de frente, flanco y cola, y excentricidad) en Cell2Fire con
optimizadores sin derivadas (BOBYQA, Nelder-Mead y otros). Sobre un incendio real (Dogrib), el
ajuste global baja el error objetivo de 96,98 a 81,94 (15,5 %). El ajuste **por modelo de
combustible** llega a 77,53, un ~5 % mejor que el global, con unas 4 veces más evaluaciones. Hay una
variante hora a hora que reajusta al llegar cada cicatriz.

**Haley (2022).** *Assimilation of Satellite Active Fires Data.* arXiv 2204.00686.
https://arxiv.org/abs/2204.00686 (sólo abstract). Tesis: reconstruir la historia del fuego,
asimilar y deducir propiedades del combustible, todo a partir de tiempos de llegada estimados desde
detecciones satelitales. Ya citada en el repo.

**Implicancia para IgniteInsights.** Hay tres líneas, de menor a mayor costo: reiniciar (ya hecho y
con ganancia en 12–24 h), ajustar el ROS por clase de combustible a las detecciones previas
(Cardil, Carrasco) y filtrar estado y parámetros (Rochoux). Con el reinicio ya capturando la
corrección de posición, el siguiente paso barato es calibrar un escalar de ADJ por clase de
combustible dominante con los tiempos de llegada VIIRS ya vistos. *Experimento falsable:* en cada
pasada VIIRS k, ajustar un ADJ global y otro por clase (sólo con detecciones hasta k), congelarlo y
pronosticar de k a k + 12 h; comparar el Dice a 12 h contra sólo reiniciar, con validación dejando
una pasada afuera. Se descarta si la mediana de la ganancia es menor de 0,03 Dice o si el ADJ ajustado
en k no sirve en k + 1 (Rochoux 2015 advierte justamente que la ventana debe coincidir con la
persistencia de la condición). Ningún trabajo que abrí mide la mejora de estos métodos con VIIRS
sobre incendios patagónicos.

## 2. Ensambles que representan el error del modelo

**Allaire, Filippi y Mallet (2020).** *Generation and evaluation of an ensemble of wildland fire
simulations.* Int. J. Wildland Fire 29(2): 160–173. https://doi.org/10.1071/WF19073 (leí el PDF
de https://connectsci.au/wf/article-pdf/29/2/160/149194/wf19073.pdf, que mostró sólo el resumen).
Distribuciones de probabilidad sobre entradas (pronóstico meteorológico, parametrización del
combustible y otras características del fuego) y cientos de simulaciones Monte Carlo, resumidas en
un mapa de probabilidad de quema. Para evaluarlas definen propiedades y scores probabilísticos
tomados de la meteorología. Sobre 7 incendios de Córcega (2017–2018), el desempeño es "regular":
la exactitud y la fiabilidad mejorables. Sugieren que los mismos scores sirvan para calibrar el
ensamble.

**Allaire, Mallet y Filippi (2021).** *Novel method for a posteriori uncertainty quantification in
wildland fire spread simulation.* Applied Mathematical Modelling 90: 527–546.
https://doi.org/10.1016/j.apm.2020.08.040 (sólo abstract, vía https://nrfirescience.org/node/22708).
En lugar de distribuciones fijadas por expertos, calibran la distribución posterior de las entradas
con una pseudo-verosimilitud basada en la distancia de Wasserstein entre áreas quemadas simulada y
observada, con un emulador de proceso gaussiano y MCMC (~1 día en 8 núcleos). Los ensambles
calibrados son más exactos que los no calibrados; la posterior favorece **ROS más bajo** y menos
incertidumbre en la dirección del viento, y baja mucho la sobreestimación sin que el ensamble deje
de cubrir el área observada.

**Finney, Grenfell, McHugh, Seli, Trethewey, Stratton y Brittain (2011).** *A Method for Ensemble
Wildland Fire Simulation.* Environmental Modeling and Assessment 16: 153–167 (FSim, sólo
abstract, vía https://www.nrfirescience.org/resource/12732). Humedad del combustible sintética a
partir del ERC y viento muestreado de probabilidades conjuntas históricas, cientos o miles de
corridas. Con 91 incendios de 2007–2009, el tamaño simulado concuerda en general, pero el promedio
del ensamble **sobrestima** el tamaño y la extensión máxima quemada se **subestima**.

**Cruz y Alexander (2013).** *Uncertainty associated with model predictions of surface and crown
fire rates of spread.* Environmental Modelling & Software 47: 16–28. Texto completo abierto en
https://d10.nrfirescience.org/sites/default/files/2023-07/09-S-03-1_CruzAlexander_2013_EMS_UncerModeledROS.pdf
49 conjuntos de evaluación, 1.278 observaciones, siete tipos de combustible. Sólo el 3 % de las
predicciones fue exacto; el error porcentual medio va de 20 a 310 % y algo más de la mitad de los
conjuntos tiene errores medios de 51 a 75 %; en el 75 % hay subestimación. Proponen una banda de
±35 % (aprox. una desviación estándar) como estándar razonable de desempeño para el ROS frontal.
Es la mejor guía para dimensionar la perturbación de ADJ.

No encontré (en lo que pude abrir) un trabajo de Lautenberger con Monte Carlo de ELMFIRE
publicado y verificable; el repo ya cita su presentación de 2023.

**Implicancia para IgniteInsights.** Si la banda de GEFS (4–14 % del área) es angosta, el
ensamble sólo mide una incertidumbre que no domina. La literatura sugiere perturbar el modelo:
ADJ por combustible (±35 % como orden de magnitud inicial, según Cruz y Alexander 2013), humedad
y clase de combustible, y evaluar con scores probabilísticos y no con el Dice del miembro medio.
Hay que vigilar el sesgo del promedio (Finney) y que la calibración suele empujar el ROS hacia
abajo (Allaire 2021). *Experimento falsable:* reemplazar los 31 miembros GEFS por 31 miembros con
el mismo viento y ADJ lognormal con σ ≈ 0,35 (más una clase de combustible vecina del crosswalk).
Si el área observada cae dentro de [P10, P90] del área simulada en ≥ 80 % de los 11 incendios
(contra la cobertura actual de GEFS) y el histograma de rangos de tiempo de llegada es más plano,
la incertidumbre dominante es de modelo; si el ancho de banda sigue por debajo de 15 % del área,
la causa es otra (referencia o ignición).

## 3. Humedad de combustible muerto con retardo

**Nelson (2000).** *Prediction of diurnal change in 10-h fuel stick moisture content.* Can. J.
For. Res. 30(7): 1071–1087. (sólo abstract, vía https://www.frames.gov/catalog/4793). Resuelve
la transferencia de calor y humedad en un palito de 1,27 cm con temperatura, HR, insolación y lluvia
de una estación RAWS. Reproduce los cambios diurnos, pero algunos valores quedan fuera de la
variabilidad observada. El resumen no da estadísticas de error.

**Reeves y Swedosh (2025).** *Fuel moisture lag effects in fire spread calculations.* MODSIM 2025
(CSIRO Data61), acceso abierto CC-BY. https://mssanz.org.au/modsim2025/files/G08.reeves.pdf (resumen
de una página; extraje el texto del PDF). Tratan la humedad fina como un sistema lineal de primer
orden dm/dt = (μ − m)/τ. Muestran que desplazar el clima τ horas ("aproximación de clima desplazado")
reproduce la solución completa con error que escala como (τ/T)². Aplicado a los modelos de ROS
australianos de pastizal y bosque de eucalipto, reduce "considerablemente" el error de ROS y de
progresión, y también el error y el sesgo con un clima real. Advierte que simuladores como Spark
usan la humedad muerta de las condiciones **actuales**, que es el caso de ELMFIRE aquí.

**Farguell, Drucker, Mirocha, Cameron-Smith y Kochanski (2024).** *Dead Fuel Moisture Content
Reanalysis Dataset for California (2000–2020).* Fire 7: 358. https://doi.org/10.3390/fire7100358
(leí el PDF de https://mdpi-res.com/d_attachment/fire/fire-07-00358/article_deploy/fire-07-00358.pdf,
sólo abstract). Un modelo de retardo simplificado con asimilación de la humedad de 10 h de RAWS da
un error absoluto medio de 0,03 g/g, contra 0,05 g/g del modelo de Nelson; la humedad muerta en
California suele estar entre 0,05 y 0,30 g/g.

**Sharples, Reddy, Resco de Dios, Nolan, Boer y Bradstock (2024).** *Evaluation and comparison of
simple empirical models for dead fuel moisture content.* Int. J. Wildland Fire 33(6): WF23120.
https://doi.org/10.1071/WF23120 (sólo abstract, vía
https://researchers.westernsydney.edu.au/en/publications/evaluation-and-comparison-of-simple-empirical-models-for-dead-fue/).
Cinco modelos simples en cuatro conjuntos de datos. Los mejores son los lineales en la diferencia
ponderada entre temperatura y HR. Advierte sobre su uso con humedades menores de 10 %.

**Sensibilidad del ROS a la humedad.** La documentación de `firebench` muestra un análisis de Sobol
del modelo de Rothermel en los 13 modelos de Anderson (viento −15 a 15 m/s, pendiente −45 a 45°,
humedad 1 a 50 %): el viento explica más del 80 % de la varianza y la humedad cerca del 10 %, sobre
todo en combustibles gruesos, con interacción viento-humedad (https://firebench.readthedocs.io/en/0.5.0/workflows_0D_models/sensitivity/Rothermel_SFIRE_A13.html;
es documentación de software, no un artículo, y los rangos condicionan la conclusión).

**Implicancia para IgniteInsights.** El m1 del proyecto es la humedad de equilibrio de Nelson con
T y HR de GFS/ERA5 (ver `HUMEDAD-ALTURA-PROPUESTA.md`), o sea instantánea. Para el combustible fino
el retardo es de ~1 h, así que el error por ese motivo debería ser pequeño en el medio del día y
mayor en la transición de la tarde y el amanecer. La mejora esperable es modesta; el sesgo de
equilibrio (bajo dosel, resolución 0,25°) probablemente pesa más. *Experimento falsable:* filtrar
la serie de m1 con τ = 1 h, la de m10 con τ = 10 h y la de m100 con τ = 100 h (o aplicar el
desplazamiento de clima de Reeves) y re-correr los 7 incendios de calibración: si la media del Dice
cambia menos de 0,01 y ninguna ventana cruza el umbral de supresión por humedad, se archiva. Antes
hay que revisar en `namelist_writer.py` que ELMFIRE admita humedad variable en el tiempo en la
forma elegida.

## 4. Iniciación y propagación de copa

**Cruz y Alexander (2010).** *Assessing crown fire potential in coniferous forests of western North
America: a critique of current approaches and recent simulation studies.* Int. J. Wildland Fire
19(4): 377–398. https://doi.org/10.1071/WF08132 (leí el PDF en
https://connectsci.au/wf/article-pdf/19/4/377/161528/wf08132.pdf, sólo abstract). Los sistemas que
acoplan Rothermel con Van Wagner (NEXUS, FlamMap, FARSITE, FFE-FVS, BehavePlus) muestran un sesgo
importante a **subpredecir** el fuego de copa. Cuatro causas: acoples incompatibles, modelos de
ROS de superficie y de copa sesgados a la baja, funciones de fracción de copa quemada que reducen el
ROS sin respaldo, y modelos de combustible personalizados sin calibrar. El resumen no cuantifica
el sesgo. Ya citada en el repo.

**Cruz, Alexander y Wakimoto (2005).** *Development and testing of models for predicting crown fire
rate of spread in conifer forest stands.* Can. J. For. Res. 35: 1626–1639.
https://doi.org/10.1139/x05-085 (texto completo extraído de
https://victoriasforestryheritage.org.au/pinefire/Cruz_etal_2005_DevelopmentAndTestingOfModelsForPredictingCrownFireRateOfSpread.pdf).
El modelo de fuego de copa activo (viento a 10 m, humedad fina estimada, densidad aparente del
dosel) explica el 61 % de la variabilidad. En fuegos experimentales independientes, 42 % de las
predicciones tienen error menor de 25 % y el error absoluto porcentual medio es 26 %. El modelo de
Rothermel (1991) subestima: error absoluto porcentual medio de 66 % (n = 24 fuegos activos) y 84 %
(experimentos ICFME). Para fuego de copa pasivo el modelo propio fue malo (177 %), con el de
Rothermel 1991 en 53 %. Todos los datos son de coníferas, sobre todo boreales. Ya citada en el repo
(es la que implementa ELMFIRE).

No encontré, en lo que pude abrir, una evaluación que muestre que acoplar copa mejore un simulador
operativo contra incendios reales: la literatura abierta que vi sólo documenta el sesgo y los errores
de ROS en experimentos de conífera.

**Implicancia para IgniteInsights.** `DIA-1-PROPUESTA.md` ya cuantifica el residuo con CFIS y lo
atribuye a este sesgo de acople. La evidencia externa respalda la dirección (subestimación) pero no
el tamaño en Nothofagus o ciprés, porque todo está calibrado en coníferas boreales y de Norteamérica.
*Experimento falsable:* en los incendios cuyo bosque tiene CBH/CBD asignado, multiplicar el ROS de
copa activa por un factor único (p. ej. 1,5 y 2) y mirar el Dice y el sesgo de área en esos casos
solamente; si el Dice no sube en ≥ 3 de los 5 o 6 casos de bosque, el déficit de copa no es la
palanca. Cuidado con que Cruz y Alexander 2013 muestra que incluso el modelo ajustado tiene ±35 %
de error, así que un factor de 1,5 está dentro de lo que no se puede distinguir sin muchos casos.

## 5. Viento en terreno complejo

**Wagenbrenner, Forthofer, Lamb, Shannon y Butler (2016).** *Downscaling surface wind predictions
from numerical weather prediction models in complex terrain with WindNinja.* Atmos. Chem. Phys. 16:
5229–5241. https://doi.org/10.5194/acp-16-5229-2016 (leí la página y el PDF). Cuatro modelos NWP
(NAM de 12 km, HRRR de 3 km y dos WRF) contra observaciones en Big Southern Butte. El
downscaling mejoró el viento cerca de la superficie con **viento fuerte y atmósfera casi neutra**;
los resultados fueron **mixtos en flujos de ladera arriba y abajo** (térmicos), aunque la
dirección mejoró en general. El downscaling no mejoró la velocidad con viento observado menor de
~5 m/s, y la precisión cae para velocidades observadas de más de 10 m/s.

**Forthofer, Butler, McHugh, Finney, Bradshaw, Stratton, Shannon y Wagenbrenner (2014).** *A
comparison of three approaches for simulating fine-scale surface winds in support of wildland fire
management. Part II.* Int. J. Wildland Fire 23(7): 982–994. https://doi.org/10.1071/WF12090
(sólo abstract, leí el PDF de https://connectsci.au/wf/article-pdf/23/7/982/144334/wf12090.pdf).
Con FARSITE, un incendio hipotético y dos reales: el modelo que conserva momento produjo los
perímetros más cercanos a lo observado, luego el que conserva masa (WindNinja) y por último el
viento uniforme. Los modelos físicos reducen la sensibilidad de la simulación a la dirección del
viento de entrada. El resumen no da cifras.

**Implicancia para IgniteInsights.** Estos resultados concuerdan con lo que el repo ya midió: la
velocidad de WindNinja con flujos diurnos y la dirección del GFS/ERA5 fue la mejor variante
(`AUDITORIA-FISICA.md`), y el flujo nocturno de WindNinja empeora la dirección. Que el viento
domine la varianza del ROS (Sobol arriba) y la banda de GEFS sea angosta sugiere que el error
relevante del viento no es el sinóptico, sino el de escala fina y el sesgo de velocidad de ERA5/GFS
en el valle. *Experimento falsable:* en los 11 incendios, perturbar la velocidad de superficie por
un factor lognormal (σ ≈ 0,3) manteniendo la dirección y medir el ancho de la banda de área. Si
sube de 4–14 % a > 30 % y la cobertura de la cicatriz mejora, la palanca es la velocidad local y
justifica seguir con WindNinja; si no, el viento ya no es el límite.

## 6. Evaluación de simuladores y qué es un Dice "normal"

**Valores reportados (todos Sørensen/Dice, contra cicatriz final de incendios mayormente grandes).**

| Fuente | Simulador | Resultado | Notas |
|---|---|---|---|
| Price y Germino (2022), Fire Ecology, https://doi.org/10.1186/s42408-022-00147-2 (vía https://www.usgs.gov/publications/modeling-fire-spread-sagebrush-steppe-using-farsite-approach-improving-input-data-and; sólo abstract) | FARSITE, incendio Soda 2015 (~113.000 ha) | 0,38 con mapas LANDFIRE; 0,70 con combustible derivado de cobertura; 0,80 en el segundo incendio (Cherry Road 2016) | El mapa de combustible mueve el Dice más de 0,3. Las discrepancias principales son flancos y contrafuegos |
| Sá et al. (2022), NHESS 22: 3917–3938, https://doi.org/10.5194/nhess-22-3917-2022 | FlamMap MTT (Rothermel), Portugal | 0,60 en los 9 mayores incendios (> 1000 ha), tras calibrar | "Límite entre acuerdo moderado y sustancial". La distribución de tamaños simulada subestima los de ~200 ha y sobrestima los de 500–1500 ha |

Con esto, el Dice de calibración 0,439 está en el rango de simulaciones **sin** combustible
dedicado (0,38 con LANDFIRE genérico) y por debajo de lo calibrado (0,60 a 0,80). El 0,191 de
prueba es bajo incluso para ese rango. No son comparables al pie de la letra: esas comparaciones
son contra la cicatriz final de incendios grandes, en que la saturación de área ayuda al Dice,
y acá es a 96 h de incendios combatidos y con una ignición estimada. Por eso conviene mirar
también el Dice a área igualada que ya reporta `IGN-26-VALIDACION.md`.

**Cruz y Alexander (2013)** (ver §2) da el piso de ruido del modelo: un ROS con error de ±35 % es
"razonable" y los errores medios habituales son de 51 a 75 %. Cálculo propio y muy idealizado, con
dos círculos concéntricos (propagación isótropa, ROS proporcional al radio): un error de ROS de
±35 % deja un Dice de 0,59 a 0,71; un factor 2 de error de ROS da 0,40. Es decir, **un Dice de 0,44
equivale a un error de ROS de ~1,9× en el caso ideal**, y en la práctica los errores de forma y
posición lo bajan más. Es una cota de orden de magnitud, no una medición.

**Sá et al. (2017).** *Evaluating fire growth simulations using satellite active fire data.*
Remote Sensing of Environment 190: 302–317. https://doi.org/10.1016/j.rse.2016.12.023 (sólo abstract,
vía https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=25220). Evaluación de FARSITE
contra detecciones activas de MODIS en 9 incendios portugueses muy grandes, con dos medidas de
discrepancia espacial (SpD absoluta y NRSpD relativa) que incorporan la incertidumbre de dónde está
el frente dentro de la huella de la detección. Las detecciones captan la dinámica a pesar de su
resolución gruesa y no hace falta el perímetro de referencia. Avala usar VIIRS como referencia y
sugiere una métrica de distancia que descuente la huella de 375 m.

**Fox-Hughes, Bridge, Faggian, Jolly, Matthews, Ebert, Jacobs, Brown y Bally (2024).** *An evaluation
of wildland fire simulators used operationally in Australia.* Int. J. Wildland Fire 33: WF23028.
https://doi.org/10.1071/WF23028 (sólo abstract, vía https://frames.gov/catalog/69214). Compara
Australis, Phoenix, Prometheus y Spark con 10 incendios históricos, con corridas base con el
pronóstico disponible y corridas perturbadas. Ninguno es claramente mejor; cada uno es más
sensible a distintos parámetros. Pide recolectar observaciones del comportamiento del fuego. El
resumen no da valores de Dice.

**Duff et al. (2018).** *Conditional Performance Evaluation: Using Wildfire Observations for
Systematic Fire Simulator Development.* Forests 9(4): 189 (título y volumen según el enlace de
búsqueda; sólo abstract, vía https://nrfirescience.org/node/17657, que no lista los autores). Dos versiones de
PHOENIX RapidFire contra 9 incendios australianos: la nueva fue algo mejor en conjunto, **sin
diferencia estadísticamente significativa**, y la original predijo mejor 3 de los 9. Con n = 9, no se
distinguen simuladores; con n = 4 de prueba, menos.

**Fractions Skill Score.** Antonio y Aitchison (2025), *How to derive skill from the Fractions Skill
Score*, arXiv 2311.11985 (preprint), https://arxiv.org/html/2311.11985v3. Cuentan que la referencia
habitual de "habilidad útil" (1 + f₀)/2 viene de Roberts (2008) y Roberts y Lean (2008), que está
mal motivada, y proponen comparar con el FSS de un pronóstico Bernoulli aleatorio en cada tamaño
de vecindad. No abrí a Roberts y Lean directamente. FSS por vecindad separa el error de
desplazamiento del de área, que el Dice mezcla.

**Duff et al. (2016)** (índices para evaluar simulaciones con perímetros) ya está citada en el repo;
no pude abrirla (403), de modo que no extraigo de ella ningún número.

**Implicancia para IgniteInsights.** El 0,439 no es "bajo" si se compara con una simulación de
combustible genérico (0,38 con LANDFIRE) pero está debajo de lo calibrado (0,60 a 0,80), y el 0,191
de prueba es el dato preocupante. Ningún artículo abierto da techo por incertidumbre de la
referencia. *Experimento falsable:* (a) techo de la referencia: dilatar y erosionar 1 píxel VIIRS
(375 m) la máscara observada y calcular el Dice entre la máscara y su versión perturbada; si es
≥ 0,9 en los 11 incendios, la referencia no explica el 0,44, y si es ≈ 0,6, el techo práctico es
cercano a lo logrado. (b) Reportar FSS a 1, 3 y 10 píxeles junto al Dice: si el FSS a 3 píxeles
sube mucho, el error es de desplazamiento y favorece asimilación de posición; si no, es de área
y favorece ADJ.

## 7. Literatura patagónica

Ya en el repo: Bianchi y Defossé 2015 (humedad viva e ignición de hojas), Cobar y Carranza 2014,
Tiribelli (tesis), Blackhall et al. 2017, Mermoz et al. 2005, Paritsis et al. 2015, Barberá et al.
Lo que abrí ahora y aporta:

**Bianchi y Defossé (2015).** *Live fuel moisture content and leaf ignition of forest species in
Andean Patagonia, Argentina.* Int. J. Wildland Fire 24(3): 340–348 (sólo abstract, vía
https://www.frames.gov/catalog/53470). Humedad viva (LFMC): caña colihue < 100 %; ñire, laura,
ciprés y radal 110–220 %; álamo > 220 %. Orden de ignición: caña colihue, ñire, radal, ciprés,
laura, álamo; la ignición cae al subir la humedad. Ya está en `docs/referencias/` y se usa en el
repo para el umbral húmedo de 110 %.

**Kitzberger, Swetnam y Veblen (2001).** *Inter-hemispheric synchrony of forest fires and the El
Niño-Southern Oscillation.* Global Ecology and Biogeography 10: 315–326 (texto del PDF de
https://www.ltrr.arizona.edu/~tswetnam/tws-pdf/KitzbergerEtal.pdf; sólo leí el resumen). En el
norte de la Patagonia los años de fuegos muy extendidos siguen al paso de El Niño a La Niña: El
Niño aumenta el combustible fino, que La Niña seca. Es contexto de régimen, no de comportamiento del
fuego. Sirve para decir que el estado del combustible fino a escala de temporada es un factor
(y que las ventanas de 96 h no lo capturan).

**Landesmann, Tiribelli, Paritsis, Veblen y Kitzberger (2020).** *Increased fire severity triggers
positive feedbacks of greater vegetation flammability and favors plant community-type conversions.*
J. Vegetation Science, https://doi.org/10.1111/jvs.12936 (sólo abstract, vía
https://nrfirescience.org/node/21739). En el NO patagónico, tras fuego de severidad moderada a muy
alta no se recupera el bosque a los 18 años y pasa a matorral y pastizal más inflamables, con más
combustible fino y más riesgo de reincendio. Respalda la decisión del repo de tratar el remanente
de disturbio reciente como matorral (SH).

**Implicancia para IgniteInsights.** La literatura patagónica que pude abrir es sobre ignitabilidad,
régimen y retroalimentaciones de vegetación; no encontré mediciones de velocidad de propagación en
lenga, coihue, ñire o caña que sirvan para calibrar ADJ por combustible. Eso explica por qué la
calibración por combustible tiene que salir de las propias cicatrices. *Experimento falsable:*
estratificar el Dice de los 11 incendios por la clase de combustible dominante del área quemada
(lenga/coihue, ñire/matorral, ciprés, caña, pino, estepa). Si ≥ 70 % de la pérdida de Dice se
concentra en un tipo (hipótesis: bosque de Nothofagus con sotobosque de caña o matorral), un ADJ
específico para ese tipo es la intervención de mayor retorno.

## No verificado (no pude abrir; no se usan como evidencia)

Las siguientes aparecieron en las búsquedas pero la página no abrió o sólo vi un título. Son pistas
para revisar a mano, sin DOI porque no los verifiqué:

- Zhang, Rochoux, Tang, Gollner, Filippi y Trouvé (2017), Fire Safety Journal 91: estimación de
  parámetros distribuida en el espacio con FIREFLY sobre FireFlux I; el resumen que vi en una
  búsqueda habla de una "mejora sustancial" frente al modelo solo, pero no abrí la página.
- Benali et al. (2016), Science of the Total Environment: incertidumbre en viento, combustible e
  ignición sobre 8 incendios portugueses. Sólo vi el registro bibliográfico.
- Salis et al. (2016), IJWF: simulación en paisajes mediterráneos con combustibles a medida; sólo
  vi registros.
- Morales et al. (2015), Ecological Modelling: modelo estocástico de propagación en el norte de la
  Patagonia con ABC. Sólo vi el registro.
- Un estudio de calibración de humedad de combustible en El Manso (Río Negro) y el de umbrales de FWI
  para ciprés y ñire (Forest Systems, 2014). Sólo vi los registros.
- Lautenberger (2013) y Duff et al. (2016): ScienceDirect devolvió 403.
- Mermoz et al. (2005, Ecology 86: 2705–2715): abrí sólo los datos bibliográficos (autores, revista,
  DOI 10.1890/04-1850), sin el resumen; ya está citada en `HUMEDAD-ALTURA-PROPUESTA.md`.
