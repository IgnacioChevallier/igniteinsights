# Decisiones de tesis sobre transparencia e incertidumbre

> Estado: decisiones acordadas el 2026-10-12 y gate técnico actualizado el 2026-10-13. Este
> documento fija el alcance conceptual y los criterios de evaluación discutidos después del
> cierre de `modelo-v0`. La prueba de concepto documentada en
> `ENSAMBLE-METEOROLOGICO-POC.md` pasó el smoke de 31 miembros y el primer backtest
> contemporáneo. Queda en estado **adoptar con condiciones**.

## 1. Afirmación central

La contribución central que se defenderá es:

> Esta tesis demuestra la viabilidad de un sistema regional, reproducible y auditable que integra
> observaciones satelitales y simulación física para representar de forma comprensible el estado de
> un incendio forestal en la Patagonia y generar escenarios de propagación potencial de corto
> plazo, comunicando explícitamente el acuerdo entre simulaciones, la vigencia de los datos y las
> limitaciones del modelo.

La afirmación se apoya en tres contribuciones:

1. **Transparencia:** estado observado, procedencia, vigencia y diferencia entre observación y
   simulación comprensibles para usuarios operativos y público general.
2. **Reducción de incertidumbre:** varios escenarios meteorológicos físicamente consistentes y un
   mapa de acuerdo entre sus simulaciones, en lugar de un único perímetro presentado como exacto.
3. **Adaptación regional:** mapa de combustibles patagónico, decisiones regionales documentadas,
   auditoría de la interfaz ELMFIRE y validación histórica sin fuga temporal.

## 2. Afirmaciones que no se harán

La tesis no afirmará que:

- el sistema reduce efectivamente el área quemada;
- se demostró una mejora causal en las decisiones operacionales;
- existe una probabilidad calibrada de que cada píxel se queme;
- se validó exactitud a una hora, porque no hay perímetros observados horarios adecuados;
- se predice la cicatriz final de un incendio combatido;
- el sistema modela brigadas, medios aéreos o líneas de contención.

La utilidad operacional es la motivación del sistema. La evidencia de la tesis se limita a la
viabilidad técnica, la evaluación retrospectiva disponible y la comprensión de la interfaz.

## 3. Semántica de la predicción

La predicción comienza desde el último perímetro reconstruido con observaciones VIIRS, no desde
el punto original de ignición. La salida representa:

> Propagación potencial bajo las condiciones modeladas, sin considerar acciones de combate o
> contención.

La ausencia de supresión debe aparecer junto al resultado. No puede quedar únicamente en la
documentación técnica.

El salto explosivo anterior a la primera detección VIIRS queda fuera del horizonte pronosticable.
El reinicio desde VIIRS absorbe gran parte de ese error, pero persiste un límite en el primer
reinicio de algunos incendios. Ese límite se presenta como escenario de estrés o advertencia, no
como miembro meteorológico ordinario.

La humedad sin gradiente altitudinal también permanece como limitación o sensibilidad separada.
Las correcciones físicas ya ensayadas no justifican asignarle una distribución probabilística.

## 4. Definición de confianza

La confianza comunicada por la interfaz se define como:

> Grado de acuerdo entre los miembros del ensamble bajo las incertidumbres consideradas.

Para cada píxel `x`:

```text
acuerdo(x) = miembros que quemaron x / miembros válidos
```

El acuerdo no se denomina probabilidad de quema mientras no exista una calibración apropiada
contra observaciones temporales independientes. La interfaz debe informar el número de miembros
válidos y esperados, el ciclo meteorológico, el horizonte y el timestamp.

## 5. Diseño del ensamble

### 5.1 Ensamble principal

La fuente primaria que debe evaluarse es GEFS. Cada miembro meteorológico alimenta una corrida
ELMFIRE manteniendo congelados combustible, dosel y parámetros de `modelo-v0`.

Las variables meteorológicas relevantes son:

- componentes U y V del viento a 10 m;
- temperatura a 2 m;
- humedad relativa o punto de rocío para derivarla;
- precipitación previa, cuando intervenga en el cálculo vigente de humedad.

La incertidumbre de la reconstrucción del perímetro VIIRS puede incorporarse de forma controlada,
sin multiplicar indiscriminadamente todas las variantes de perímetro por todos los miembros
meteorológicos.

### 5.2 Escenario regional

SMN WRF se evalúa como escenario regional determinista e independiente. No se suma al denominador
GEFS ni recibe el mismo peso por conveniencia.

### 5.3 Separación de riesgos

- **Meteorología y perímetro observado:** pertenecen al ensamble principal cuando sus variantes
  tienen una procedencia trazable.
- **Día 1 explosivo:** escenario expansivo separado.
- **Supresión:** fuera de alcance; no se activa el módulo genérico de ELMFIRE.
- **Humedad sin gradiente de altura:** advertencia o sensibilidad separada.
- **Combustible y dosel:** congelados en `modelo-v0`.

## 6. Presentación en la interfaz

Las isocronas se mantienen como representación principal y permanecen visibles.

El panel lateral derecho incorpora un fondo temático activable llamado provisionalmente
**Acuerdo del ensamble**. Los fondos temáticos son mutuamente excluyentes:

- Tiempo de llegada;
- Intensidad del frente de fuego;
- Acuerdo del ensamble.

Activar o desactivar el acuerdo no altera las isocronas. Al desactivarlo, la interfaz conserva el
comportamiento anterior.

La visualización propuesta para el acuerdo es:

- `>= 0,80`: zona de alto acuerdo;
- `>= 0,50`: escenario central;
- `>= 0,10`: propagación posible.

La leyenda debe utilizar expresiones como **acuerdo entre simulaciones** y evitar porcentajes
presentados como probabilidades calibradas.

## 7. Evaluación de transparencia

La evaluación inicial se realiza sin capacitación ni explicación oral. Los participantes sólo
pueden usar la información visible en la interfaz. Las explicaciones posteriores sirven para
entender errores, no para corregir las respuestas de la prueba.

Se evalúan dos cohortes por separado:

### 7.1 Usuarios operativos

- un brigadista;
- un guardaparque;
- un coordinador.

Cada participante debe resolver correctamente al menos el 80 % de las tareas correspondientes a
su perfil. Los tres deben responder correctamente los conceptos críticos:

- diferencia entre observación y simulación;
- ausencia de supresión;
- diferencia entre acuerdo del ensamble y probabilidad calibrada;
- horizonte y vigencia del pronóstico.

Los resultados se reportan individualmente. Con tres participantes no se generaliza
estadísticamente a toda la población operativa.

### 7.2 Público general

Participan diez personas. Al menos ocho deben resolver correctamente un mínimo del 80 % de las
tareas básicas. Las tareas cubren:

- estado y perímetro observado;
- hora y fuente de la última observación;
- diferencia entre observación y proyección;
- lectura de las isocronas;
- alcance potencial sin supresión;
- significado de las bandas de acuerdo.

Los resultados de ambas cohortes se informan por separado. No se construye un promedio único con
las trece personas.

## 8. Evaluación predictiva

IoU y Dice permanecen como métricas retrospectivas de exactitud. El umbral `IoU >= 0,60` se
retira como condición obligatoria de éxito de la tesis porque fue definido para una predicción a
una hora que no puede validarse con los datos temporales disponibles. Se conserva como objetivo
operacional futuro.

La prueba del ensamble debe comparar, como mínimo:

- miembro de control;
- contorno de acuerdo `>= 0,50`;
- cobertura de la referencia por la banda `>= 0,10`;
- área adicional necesaria para obtener esa cobertura;
- estabilidad frente a escenarios meteorológicos diferentes;
- costo, latencia, fallos y denominador efectivo.

El conjunto de prueba no se usa para seleccionar miembros, umbrales o parámetros. Un resultado
negativo de la prueba de concepto es informativo y no invalida las demás contribuciones de la
tesis.

## 9. Gate técnico y adopción condicionada

El smoke de infraestructura usó `epuyen-2025/pronostico-v6`, ventana 1, con el perímetro VIIRS
observado hasta el 2025-01-15 18:33 UTC y GEFS `2026101200`. Por la diferencia de fechas es un
ensayo no puntuable, no evidencia de exactitud predictiva.

El gate técnico pasó:

- 31 de 31 miembros ejecutados sin sustituciones ni fallos finales;
- meteorología distinta y trazable para todos los miembros;
- TOA válidos sobre la misma grilla;
- áreas entre 1.065,42 y 1.297,98 ha;
- IoU geométrica entre miembros entre 0,820 y 0,972;
- mapa de acuerdo no vacío ni uniforme;
- 1.056,6 s acumulados de solver serial y aproximadamente 8,5 GB por ciclo con la
  implementación de la prueba.

El primer backtest contemporáneo también pasó los controles de integridad. Usó el reinicio
Epuyén P-24 del 2025-01-15 18:33 UTC y el ciclo GEFS 12Z, disponible completamente antes del
reinicio. El offset de 6 h 33 min se aplicó mediante horas válidas absolutas (`f006..f033`), y
`forecast_valid_at` se definió desde el inicio real de la simulación.

El resultado separa dos mejoras:

- **validez técnica y trazabilidad:** mejora material; los 31 miembros son distintos, el ciclo
  era contemporáneo y el experimento es reproducible;
- **exactitud predictiva:** mejora marginal y no generalizable con un solo reinicio. A 24 h,
  `>= 0,80` elevó IoU de 0,3795 a 0,3817 y Dice de 0,5502 a 0,5525 frente a c00; `>= 0,50`
  fue prácticamente equivalente al control. `>= 0,10` cubrió el 91,4 % de la observación, a
  costa de 1.139,67 ha adicionales fuera de la referencia.

### 9.1 Resultado con 23 reinicios (2026-10-17)

La extensión se completó: 23/23 reinicios P-24 de calibración de cuatro incendios, con 31/31
miembros cada uno y todos con la integridad aprobada. No se abrió el conjunto de prueba ni se
modificaron umbrales, miembros, ciclos, `modelo-v0` ni `lw-100-001`. El detalle está en
`ENSAMBLE-BACKTESTS-CONSOLIDADO.md`.

Las tres preguntas se responden por separado:

- **Validez técnica y trazabilidad:** sí. No hubo sustituciones ni fallos científicos, los
  ciclos estaban disponibles antes de cada reinicio y los artefactos tienen hash. Con la
  política de retención, cada caso retiene ~1,6 GiB. Tarda cerca de 1 h de reloj en serie, así
  que es viable fuera de línea, pero no en latencia operativa sin paralelizar.
- **Comunicación de sensibilidad:** sí, con una limitación. Las bandas nunca fueron vacías ni
  uniformes, pero son angostas: la diferencia entre `>= 0,10` y `>= 0,80` es el 4–14 % del área
  de c00. Además queda crecimiento observado fuera de `>= 0,10` (mediana de 685 ha en Puerto
  Patriada a 24 h). Por eso la leyenda aclara que sólo varía la meteorología y que el incendio
  puede extenderse fuera de esa zona.
- **Exactitud predictiva:** no hay mejora consistente entre incendios. Con medianas por
  incendio, `>= 0,80` supera a c00 en IoU en 2/4 incendios a 12 h y en 3/4 a 24 h, siempre por
  ≤0,003, y empeora en Puerto Patriada. `>= 0,50` es equivalente a c00. `>= 0,10` gana recall
  en 4/4 incendios, pero pierde IoU y agrega área. El resultado favorable de Epuyén no se
  generalizó.

Decisión: se adopta **con limitaciones** como capa de acuerdo/incertidumbre, conectada al
sidebar y apagada por defecto. No se adopta como mejora predictiva, y `>= 0,80` no se promueve.
Siguen abiertos:

1. la evaluación con usuarios reales (`PROTOCOLO-EVALUACION-ACUERDO-ENSAMBLE.md`).

**CPU/RSS y latencia: medidas el 2026-10-31** con un backtest GEFS reproducido byte a byte
(`diagnostico-e2e/notas/AD-recursos-ensamble.md`). Son 35 min por reinicio en serie: descarga 22 %,
materialización 51 % y las 31 corridas de ELMFIRE 23 %. La RAM es de 1,4 GiB por corrida, así que
entran 5 a la vez en la VM de 7,75 GB, y el costo es de ~430 CPU·s de solver. Quedan como límites
medidos: la latencia entra entre dos pasadas, y paralelizar ELMFIRE sólo la bajaría en una parte
chica.

**Mínimo operativo de 24/31: ratificado** por el autor el 2026-10-31 como decisión de producto. Con
menos de 24 miembros válidos no se escribe el mapa de acuerdo, y la interfaz muestra siempre
válidos/esperados, ciclo, horizonte y timestamp (§4).

Estas condiciones de §9 quedan resueltas:

- los 22 reinicios adicionales;
- los roles predefinidos;
- la no apertura de prueba;
- la comparación pareada por incendio;
- la retención;
- la semántica de acuerdo, no probabilidad.

La evidencia respalda una capa de acuerdo/incertidumbre, no una superioridad predictiva sobre
c00. La escritura de introducción, alcance,
arquitectura, adaptación regional, auditoría física, metodología de transparencia y limitaciones
no depende de que el ensamble supere al control.
