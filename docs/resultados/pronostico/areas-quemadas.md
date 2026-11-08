# Tratamiento de áreas quemadas

Fecha de corte: 2026-10-12.

## Pregunta

¿Cómo evitar que la aplicación trate una quema reciente, ausente del mapa base de combustibles,
como si conservara su cobertura anterior?

El problema afecta la preparación de simulaciones nuevas, no la definición de `modelo-v0`: el
mapa CCS-BAP es estático y no contiene las quemas posteriores a su fecha de elaboración.

## Regla adoptada

La aplicación combina la pérdida forestal anual de Hansen con quemas provenientes de dNBR y
MCD64A1. La reasignación se hace sobre una copia del mapa preparado:

- quemas de 1 a 5 años pasan a GR1;
- bosque TL/TU quemado hace 6 a 15 años pasa a SH3;
- matorral y pastizal conservan su clase después de los 5 años;
- una quema del año de la simulación no cuenta ni oculta quemas anteriores.

Para bosque, Hansen tiene prioridad. Otras fuentes sólo se aplican si registran una quema
posterior al último año disponible de Hansen. Así se evita confundir plantaciones posteriores a
2000 con superficie no forestal.

La ingesta FIRMS histórica combina las fuentes SP y NRT y elimina las detecciones NRT ya cubiertas
por SP.

## Evidencia

La señal regional de MCD64A1 respalda una carga fina baja durante los primeros años:

| Edad de la cicatriz | Reincendio relativo, 2006–2026 | Sin 2026 | Lectura |
|---|---:|---:|---|
| 1–2 años | 0,83 | 1,31 | evidencia débil |
| 3–5 años | 0,20 | 0,29 | menor continuidad; respalda GR1 |
| 6–15 años | 3,88 | 1,41 | vuelve a arder; respalda SH3 en bosque |

La prueba final `LYQ-3` comparó la regla contra `modelo-v0` en siete casos:

| Resultado agregado | modelo-v0 | LYQ-3 | Δ |
|---|---:|---:|---:|
| Dice medio | 0,439 | 0,439 | 0,000 |
| Dice mediano | 0,501 | 0,501 | 0,000 |

No aparecieron alarmas nuevas y la peor variación individual fue −0,006 en Los Alerces 2023.
La regla pasa el criterio de no regresión.

Una variante intermedia que aplicaba las fuentes sin distinguir bosque perdió 0,048 de Dice en
Epuyén y fue descartada. También permitió detectar y corregir un desplazamiento de unos 18,6 km
en MCD64A1 causado por interpretar incorrectamente su CRS.

## Decisión

La aplicación adopta `LYQ-3` —Hansen más las otras fuentes y la regla por edad— para preparar
simulaciones. `modelo-v0` no cambia: el benchmark demuestra que la regla no introduce una
regresión, no que estime con precisión el combustible real de cada cicatriz.

## Límites

- MCD64A1 trabaja aproximadamente a 500 m y ensancha bordes.
- Hay pocas observaciones independientes para quemas de 1 a 5 años.
- La autocorrelación espacial limita la interpretación del reincendio.
- El dosel de quemas recientes puede seguir reflejando Hansen 2000 o ETH 2020.
- La capa debe regenerarse cada temporada.

## Trazabilidad

- Regla: `fuels_builder.reassign_burns_by_age` y `reassign_burns_in_raster`.
- Construcción de la capa: `scripts/exportar_mcd64a1.py` y `scripts/anio_quema.py`.
- Prueba de la premisa: `scripts/premisa_lo_ya_quemado.py`.
- Pruebas: `tests/test_burn_age_fuels.py` y `tests/test_firms_sources.py`.
- Receta evaluada: `lw100-quema-edad-002`.
