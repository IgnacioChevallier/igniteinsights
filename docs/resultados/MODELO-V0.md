# Modelo v0

> Estado: **aprobado internamente para producción** el 2026-10-04. Snapshot ejecutable:
> `benchmarks/modelos/modelo-v0.json`.

## Identidad

`modelo-v0` es la promoción de la receta `lw-100-001` sobre la partición v6. No es una receta
nueva y no duplica corridas. El snapshot fija:

- SHA de la receta;
- once casos y sus paquetes por SHA;
- partición calibración/prueba;
- resultados del gate;
- commit de código del cierre físico;
- limitaciones y regla de reapertura.

Validación local:

```bash
uv run python scripts/benchmark.py modelo modelo-v0
```

## Gate

| Criterio | Resultado |
|---|---|
| Interfaz física | Cinco hallazgos de ELMFIRE y orientación del terreno corregidos |
| Inmutabilidad | Receta, casos, manifiestos y métricas referenciados por SHA-256 |
| Calibración | 0,439 de media, 0,501 de mediana; sin alarmas salvo el caso límite |
| Validación cruzada | 0,416 de media y 0,496 de mediana fuera de muestra |
| Prueba | 0,191/0,167 y dos alarmas; informativo, no usado para ajustar |
| Robustez a la ignición | 0,461/0,497 sobre 21 perturbaciones |
| Reproducción ejecutable | GFS 4/4 y ERA5 3/3 ventanas iguales byte a byte |
| Regla de parada | Sólo bug físico o evidencia externa nueva |

La verificación ejecutable del 2026-10-04 reprodujo
`epuyen-2025/calibracion-v6` (GFS) y
`los-alerces-2016/calibracion-era5-v6` (ERA5) con la receta congelada. Todas las ventanas
coincidieron con sus artefactos registrados.

## Resultados por caso

Cada caso se puntúa al final de su horizonte. Lo que se compara es lo acumulado que el modelo
quemó desde la ignición contra la cicatriz dNBR **truncada al horizonte**: las celdas a menos de
un píxel VIIRS (375 m) de alguna detección hecha hasta el fin de la última ventana. Lo que ardió
después va a la exclusión, que no cuenta ni como acierto ni como error.

El horizonte no es fijo. Dura mientras el área FIRMS acumulada siga creciendo, con un tope de
120 h, y se corta antes si el incendio se funde con otro (`docs/historico/RESULTADOS-CSS-BAP.md`
§2). *t\** es la hora en que lo predicho alcanza el área observada: si es menor que el horizonte,
el modelo es más rápido que el incendio real.

**Calibración** (media 0,439, mediana 0,501):

| Caso | Horizonte | Dice | IoU | Precisión | Recall | Sesgo de área | *t\** | Lectura |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Alerces 2024 | 120 h (tope) | 0,635 | 0,465 | 0,55 | 0,75 | 1,35 | 97 h | El mejor caso. Le sobra área en las últimas 24 h |
| Alerces 2023 | 54 h | 0,528 | 0,358 | 0,41 | 0,75 | 1,86 | 40 h | Buena forma, pero quema casi el doble: el incendio real fue combatido y se frenó a las ~54 h |
| Cholila 2015 | 120 h (tope) | 0,513 | 0,345 | 0,55 | 0,48 | 0,87 | — | Se queda algo corto y nunca alcanza el área. Puntúa sólo el 26 % de la cicatriz final |
| Epuyén 2025 | 96 h | 0,501 | 0,334 | 0,43 | 0,60 | 1,41 | 78 h | Arranca muy lento (Dice 0,05 a 24 h) y lo compensa después |
| Patriada 2026 | 96 h (fusión) | 0,496 | 0,330 | 0,61 | 0,42 | 0,70 | — | Lo que quema está bien ubicado (precisión 0,61), pero le falta un 30 % de área |
| Alerces 2016 | 72 h | 0,389 | 0,242 | 0,31 | 0,52 | 1,69 | 53 h | Quema de más hacia donde el fuego real no fue (ERA5, sin estación cercana) |
| Las Golondrinas 2021 | 24 h | 0,012 | 0,006 | 0,28 | 0,01 | 0,02 | — | Caso límite: el GFS no tiene el viento prefrontal del norte ni el aire seco de la noche (a las 21 ART: 29 kt y 27 % reales, contra 6,7 mph y 61 %; RIESGOS §3). Quema 224 de 10.622 ha. Con ese SYNOP sostenido hasta 06Z quema 2.404 ha (Dice 0,24, sesgo 0,23, precisión 0,66): la meteorología explica una parte, no el orden de magnitud. Sostenido hasta 12Z, sesgo 0,44: el freno es TL6 bajo dosel más una franja de agua, no la duración de la ventana (§6). Con SYNOP hasta 03Z más pavesas fuertes (diagnóstico, no modelo), 9.088 ha y Dice 0,545; con el GFS, las mismas pavesas no cambian nada. Hacen falta las dos cosas a la vez (`diagnostico-e2e/notas/G-golondrinas-meteo-observada.md` §7, `X-pavesas-calibracion.md`). La referencia es válida (perímetro SNMF, MODIS y FIRMS; G §9). Sin pavesas y con 72 h, la forma en `t*` es 0,40: nada de la cicatriz más allá de 15 km (G §8) |

Cinco de los siete casos quedan entre 0,49 y 0,64. La media la baja un solo caso, Las Golondrinas,
que falla por la meteorología de entrada y, en parte, por el modelo de propagación (sin pavesas ni
estructuras; nota G). Sin él la media
sería 0,510. El sesgo sigue un patrón: casi todos los casos se quedan cortos al principio y
terminan con área de más (1,35–1,86 en Alerces 2023, 2024, 2016 y Epuyén 2025). Es lo esperable
en un modelo sin supresión que, además, subestima el primer día (`DIA-1-PROPUESTA.md`).

**Prueba** (media 0,191, mediana 0,167; informativa, no se usa para ajustar):

| Caso | Horizonte | Dice | Sesgo de área | *t\** | Lectura |
|---|---:|---:|---:|---:|---|
| Alerces 2015 | 72 h | 0,309 | 1,48 | 54 h | Sube la ladera en vez de bordear el lago (RIESGOS §3, viento) |
| Puerto Café 2025 | 96 h | 0,207 | 0,30 | — | Fase explosiva tras 27 días latente. Quema menos de un tercio del área |
| Epuyén 2019 | 120 h | 0,128 | 14,6 | 37 h | Se desborda sin supresión: 19.534 ha contra 1.338. La forma a área igualada es razonable (0,346) |
| El Turbio 2025 | 120 h | 0,122 | 1,08 | 115 h | Área correcta en el lugar equivocado: Dice ~0,1 en todos los cortes |

## Sensibilidad al horizonte

`benchmark.py horizonte modelo-v0` vuelve a puntuar las corridas congeladas de cada caso como si
se hubieran cortado a 24, 48, 72, 96 o 120 h, con la cicatriz truncada a cada corte. No corre
ELMFIRE. El corte igual al horizonte reproduce `metricas.json` en los 11 casos (lo verifica el
propio comando). Los datos quedan en `benchmarks/diagnosticos/horizonte-modelo-v0.json`.

| Caso | Conjunto | 24 h | 48 h | 72 h | 96 h | 120 h |
|---|---|---|---|---|---|---|
| Alerces 2023 | calibración | 0,358 / 0,77 | 0,491 / 2,46 | 0,528 / 1,86 (54 h) | — | — |
| Epuyén 2025 | calibración | 0,047 / 0,05 | 0,145 / 0,25 | 0,454 / 0,88 | 0,501 / 1,41 | — |
| Alerces 2024 | calibración | 0,223 / 0,16 | 0,463 / 0,40 | 0,656 / 0,92 | 0,629 / 1,08 | 0,635 / 1,35 |
| Patriada 2026 | calibración | 0,214 / 0,17 | 0,310 / 0,30 | 0,464 / 0,54 | 0,496 / 0,70 | — |
| Las Golondrinas 2021 | calibración | 0,012 / 0,02 | — | — | — | — |
| Alerces 2016 | calibración | 0,139 / 0,13 | 0,343 / 0,61 | 0,389 / 1,69 | — | — |
| Cholila 2015 | calibración | 0,563 / 1,58 | 0,273 / 0,39 | 0,362 / 0,53 | 0,462 / 0,71 | 0,513 / 0,87 |
| El Turbio 2025 | prueba | 0,109 / 0,68 | 0,100 / 0,74 | 0,092 / 0,95 | 0,088 / 0,81 | 0,122 / 1,08 |
| Puerto Café 2025 | prueba | 0,089 / 0,23 | 0,066 / 0,15 | 0,189 / 0,26 | 0,207 / 0,30 | — |
| Epuyén 2019 | prueba | 0,269 / 0,75 | 0,326 / 3,52 | 0,270 / 5,50 | 0,178 / 9,46 | 0,128 / 14,6 |
| Alerces 2015 | prueba | 0,168 / 0,18 | 0,247 / 0,77 | 0,309 / 1,48 | — | — |

Cada celda es Dice / sesgo de área. Con todos los casos cortados a lo sumo en H:

| Tope H | 24 h | 48 h | 72 h | 96 h | 120 h (vigente) |
|---|---:|---:|---:|---:|---:|
| Calibración, media / mediana | 0,222 / 0,214 | 0,291 / 0,310 | 0,409 / 0,454 | 0,431 / 0,496 | 0,439 / 0,501 |
| Prueba, media / mediana | 0,159 / 0,139 | 0,185 / 0,173 | 0,215 / 0,230 | 0,196 / 0,193 | 0,191 / 0,167 |

Lectura:

- **Los horizontes largos no bajan la calibración: la suben.** El Dice crece con el horizonte en
  seis de los siete casos. Alerces 2024 llega a su máximo a 72 h (0,656) y después se mantiene.
  Acortar todos los casos a 72 h bajaría la media de 0,439 a 0,409.
- **El sesgo pasa de déficit a exceso.** A 24 h todos los casos de calibración salvo Cholila
  queman entre el 2 % y el 77 % del área observada. Al final del horizonte, cuatro de siete
  queman de más. El modelo es lento el primer día y no se detiene después: le faltan el Día 1
  explosivo y la supresión, no un horizonte más corto.
- **Cholila a 24 h (0,563) es un artefacto:** son 7 detecciones tempranas con poca área. Desde
  48 h sigue el patrón general.
- **En prueba, el único caso al que el horizonte largo perjudica es Epuyén 2019.** Su Dice tiene
  el máximo a 48 h (0,326) y cae a 0,128 a medida que el sesgo sube a 14,6. Toda la diferencia
  entre el tope de 72 h (0,215) y el vigente (0,191) viene de ese caso. Es el límite de supresión
  ya declarado (`ESTADO-RESEARCH.md` §6.2). El Turbio no mejora con ningún corte.
- **El horizonte no se reelige con esta tabla.** La regla (crecimiento FIRMS, tope de 120 h) se
  fijó antes del primer barrido, y elegirla ahora mirando el Dice de prueba violaría la regla de
  parada. La tabla es un análisis de sensibilidad: dice que la métrica principal no depende del
  corte de manera que favorezca al modelo.

## Contrato productivo

El nombre `modelo-v0` puede usarse en configuración, documentación y despliegue para seleccionar
este snapshot. Internamente, la ejecución sigue resolviendo la receta `lw-100-001` y los builders
vigentes. Promover un futuro `modelo-v1` exigirá:

1. una receta nueva o una modificación explícita de insumos;
2. casos y paquetes congelados;
3. banco físico aprobado;
4. métricas de calibración, validación cruzada y prueba;
5. comparación contra modelo-v0;
6. una justificación que no use el holdout para elegir parámetros.

## Límites de uso

Modelo-v0 no promete reproducir supresión, igniciones secundarias ni ráfagas subhorarias. El
conjunto de prueba es pequeño y heterogéneo. La promoción significa “baseline productivo,
auditable y físicamente verificado”, no “modelo universalmente validado”.

- Sin pavesas. No se usan ni globales (X) ni condicionadas a una regla previa (Y): ninguna
  variable disponible antes de pronosticar separa los incendios en que ayudan de los que desbordan
  (`diagnostico-e2e/notas/X-pavesas-calibracion.md`, `Y-pavesas-condicionadas.md`).
