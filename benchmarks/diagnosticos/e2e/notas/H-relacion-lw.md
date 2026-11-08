# H. Unidad del viento U en la relación largo/ancho (L/W) de Anderson (1983)

## Veredicto

ELMFIRE 2025.0212 NO se aparta. Los coeficientes 0,2566 y 0,1548 son la forma de Anderson para U en **m/s**. La forma en **mph** usa 0,1147 y 0,0692. La premisa "si fuera mph, el factor sería 1/88" parte de un supuesto que no vale: con 0,2566 la unidad correcta es m/s.

## Evidencia

**Código de ELMFIRE (leído localmente, `.../upstream/elmfire/build/source/`)**
- `elmfire_level_set.f90:1738-1742`: `WSMFEFF = WSMFEFF_COEFF * PHIMAG ** B_COEFF_INVERSE`, tope `MIN(WSMFEFF, 0.9*KWPM2_TO_BTUPFT2MIN*IR)` y `LOW = MIN(0.936*EXP(0.2566*WSMFEFF*WSMFEFF_LOW_MULT) + 0.461*EXP(-0.1548*WSMFEFF*WSMFEFF_LOW_MULT) - 0.397, MAX_LOW)`.
- `elmfire_init.f90:852-855`: `PHIWTERM = C*(β/βop)^-E`, `B_COEFF_INVERSE = 1/B`, `WSMFEFF_COEFF = (1/PHIWTERM)^(1/B)`. Es la inversión de φw = C·U^B·(β/βop)^-E de Rothermel (1972), con U en ft/min. El tope 0,9·IR usa IR en Btu/ft²/min (`KWPM2_TO_BTUPFT2MIN`, línea 1669), que es la condición de Rothermel para U en ft/min. WSMFEFF está en ft/min. Esto lo deduje de la forma de las ecuaciones; no abrí Rothermel 1972.
- `elmfire_namelists.f90:599` y `:620`: `MAX_LOW = 8.0` y `WSMFEFF_LOW_MULT = 5.07955E-3`. Ambos están en el grupo `&SIMULATOR` (lista en 581-585). 5,07955E-3 ≈ 0,3048/60 (ft/min a m/s). En `level_set.f90:1669` existe además `FTPMIN_TO_MPS = 0.3048/60`.

**Relación entre las dos formas**
- 0,1147/0,2566 = 0,4470 y 0,0692/0,1548 = 0,4470, que es mph a m/s (0,44704). Por lo tanto exp(0,2566·U_m/s) = exp(0,1147·U_mph), y lo mismo con el segundo término. Es la misma ecuación.

**Código abierto (clonado y leído)**
- behave, `src/behave/fireSize.cpp:20-21,97`: convierte el viento a mph (`SpeedUnits::MilesPerHour`, "wind speed is now miles per hour") y calcula `.936*exp(.1147*U)+.461*exp(-.0692*U)-.397`, con tope 8 (líneas 98-102). Es la implementación de Missoula Fire Lab (firelab/behave, commit d4acc8a).
- pyretechnics (grupo de Lautenberger), `src/pyretechnics/surface_fire.py:581-583`: `0.936*exp(0.1147*U_mph) + 0.461*exp(-0.0692*U_mph) - 0.397`, con `min(8.0, ...)`. La documentación (`org/pyretechnics.org:3876-3878`) dice "effective wind speed in mph". En 3868-3870 da Rothermel 1991, `L/W = 1 + 0.25·U_mph`.
- Documentación de FARSITE/FlamMap (https://owfflammaphelp62.firenet.gov/LegacyFARSITE/Tech_Elliptical_Dimensions.htm): usan el modelo de Anderson (1983) con viento a media llama y restan 0,397. La página no da la ecuación ni la unidad.

**Fuentes que NO pude abrir** (no se citan como confirmadas)
- Anderson 1983 INT-305: la búsqueda sólo dio el registro bibliográfico (BHL), y BHL devolvió 403.
- Finney 1998 RMRS-RP-4.
- Andrews 2018 RMRS-GTR-371: 403.
- Alexander 1985: no la abrí.
- Cell2Fire, ForeFire y la discusión del repo de ELMFIRE sobre `WSMFEFF_LOW_MULT`: no los revisé.
- El código fuente de FARSITE/FlamMap no está publicado.

Por eso la unidad "mph para 0,1147 / m/s para 0,2566" queda establecida por dos implementaciones independientes (behave, pyretechnics) más la identidad numérica de las constantes. Los textos primarios no los pude confirmar. Conviene verificar INT-305 a mano antes de citarlo en la tesis.

## Tabla L/W (tope 8)

U es el viento efectivo a media llama.

| U (mph) | A: m/s, convención de ELMFIRE (equivale a 0,1147 en mph) | B: mph metido en 0,2566 (hipótesis errónea, factor 1/88) | Rothermel 1991 (1+0,25·U) |
|---|---|---|---|
| 1 | 1,08 | 1,21 | 1,25 |
| 2 | 1,18 | 1,50 | 1,50 |
| 4 | 1,43 | 2,46 | 2,00 |
| 6 | 1,77 | 4,15 | 2,50 |
| 8 | 2,21 | 7,03 | 3,00 |
| 10 | 2,78 | 8,00 | 3,50 |

Alexander 1985 (viento a 10 m en km/h): no incluido, porque no abrí la fuente y no pongo coeficientes de memoria.

## Conclusiones

- **(a)** Anderson original (forma mph) y behave/pyretechnics usan mph con 0,1147/0,0692. La forma 0,2566/0,1548 es esa misma ecuación en m/s. Ver la evidencia y las fuentes no abiertas arriba.
- **(b)** ELMFIRE es consistente: ft/min a m/s mediante `WSMFEFF_LOW_MULT` = 0,3048/60. Ni bug físico ni apartamiento. Sí es un default documentado en el namelist. Lo que no hay es un comentario en el código que explique la elección.
- **(c)** Sin diferencia que corregir. Sólo en un escenario hipotético de unidad equivocada (columna B) los incendios saldrían mucho más alargados. Con viento efectivo de unos 10 mph en combustibles abiertos (GR, SH) saldría L/W 8 en vez de 2,8. Bajo dosel con WAF 0,07-0,09, un viento libre de 20 mph da unos 1,4-1,8 mph a media llama y L/W ≈ 1,1-1,2 con la convención correcta, contra 1,3-1,4 con la errónea. Cabe precisar que WSMFEFF es un viento **efectivo** (viento más pendiente), así que puede ser mayor que el viento a media llama.
- **(d)** Sí es posible sin tocar ELMFIRE: `WSMFEFF_LOW_MULT` y `MAX_LOW` son keywords de `&SIMULATOR`. Un grep en `app/` no encontró que `namelist_writer.py` los emita, así que hoy corre con los defaults. Si se quisiera explorar sensibilidad al aspecto, bastaría añadirlos al writer. No hay motivo físico para cambiarlos.
