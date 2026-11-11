# Resultados de la comparación de mapas condicionada a modelo-v0

## Pregunta y método

¿Qué cambia al sustituir únicamente el mapa de combustible superficial de `modelo-v0` por
WorldCover o MapBiomas?

Los once casos, clima, ignición, topografía, dosel, humedad, parámetros y referencias se
mantuvieron por hash. Sólo cambió `fbfm40.tif`; no se recalibró una receta por producto. La
métrica principal fue Dice contra la cicatriz, acompañada por sesgo de área y forma a área
igualada. Los casos donde WorldCover es posterior al incendio se informan como fuga temporal y
no sostienen la conclusión.

Recetas: `lw-100-001`, `lw-100-worldcover-001` y `lw-100-mapbiomas-001`.

## Resultados

11 de 11 incendios con los tres mapas.

Controles CCS-BAP reproducidos byte a byte: 11/11.

Los Alerces 2023 usa el protocolo `v6m2`: la primera corrida `v6m` se rechazó porque fue ejecutada durante una prueba de concurrencia MPI y no reprodujo el control. `v6m2` es la repetición limpia, íntegramente serial.

| Incendio | Conjunto | Clima | CCS-BAP Dice / sesgo / forma | WorldCover Dice / sesgo / forma | MapBiomas Dice / sesgo / forma |
|---|---|---|---|---|---|
| los-alerces-2023 | calibracion | GFS | 0,528 / 1,86 / 0,455 (ccsbap2017) | 0,100 / 0,08 / 0,100 ⚠ (worldcover2021) | 0,373 / 0,68 / 0,373 (mapbiomas2022) |
| epuyen-2025 | calibracion | GFS | 0,501 / 1,41 / 0,449 (ccsbap2017) | 0,060 / 0,06 / 0,060 ⚠ (worldcover2021) | 0,319 / 1,34 / 0,276 (mapbiomas2024) |
| los-alerces-2024 | calibracion | GFS | 0,635 / 1,35 / 0,617 (ccsbap2017) | 0,048 / 0,03 / 0,048 ⚠ (worldcover2021) | 0,565 / 1,12 / 0,565 (mapbiomas2023) |
| puerto-patriada-2026 | calibracion | GFS | 0,496 / 0,70 / 0,496 (ccsbap2017) | 0,028 / 0,02 / 0,028 ⚠ (worldcover2021) | 0,418 / 0,50 / 0,418 (mapbiomas2024) |
| las-golondrinas-2021 (límite) | calibracion | GFS | 0,012 / 0,02 / 0,012 ⚠ (ccsbap2017) | 0,007 / 0,01 / 0,007 ⚠ (worldcover2020) | 0,010 / 0,01 / 0,010 ⚠ (mapbiomas2020) |
| los-alerces-2016 | calibracion | ERA5 | 0,389 / 1,69 / 0,400 (ccsbap2013) | 0,553 / 2,28 / 0,631 ⚠ ‡ (worldcover2020) | 0,467 / 1,37 / 0,490 (mapbiomas2015) |
| cholila-2015 | calibracion | ERA5 | 0,513 / 0,87 / 0,513 (ccsbap2013) | 0,000 / 0,00 / 0,000 ⚠ ‡ (worldcover2020) | 0,436 / 0,63 / 0,436 (mapbiomas2014) |
| el-turbio-2025 | prueba | GFS | 0,122 / 1,08 / 0,115 (ccsbap2017) | 0,449 / 2,88 / 0,211 ⚠ (worldcover2021) | 0,388 / 3,81 / 0,355 ⚠ (mapbiomas2024) |
| puerto-cafe-2025 | prueba | GFS | 0,207 / 0,30 / 0,207 ⚠ (ccsbap2017) | 0,021 / 0,08 / 0,021 ⚠ (worldcover2021) | 0,204 / 0,31 / 0,204 ⚠ (mapbiomas2024) |
| epuyen-2019 | prueba | ERA5 | 0,128 / 14,60 / 0,346 ⚠ (ccsbap2017) | 0,113 / 16,57 / 0,390 ⚠ ‡ (worldcover2020) | 0,203 / 8,80 / 0,382 ⚠ (mapbiomas2018) |
| los-alerces-2015 | prueba | ERA5 | 0,309 / 1,48 / 0,275 (ccsbap2013) | 0,504 / 2,68 / 0,410 ⚠ ‡ (worldcover2020) | 0,342 / 1,68 / 0,240 (mapbiomas2014) |

**Todos (sin el límite)** (10 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,383 | 0,443 | 0,387 |
| WorldCover | 0,188 | 0,080 | 0,190 |
| MapBiomas | 0,372 | 0,381 | 0,374 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 7 / 3 / 0 | 0,344 | 0,195 | 0,306 | +0,427 +0,441 +0,587 +0,468 -0,164 +0,513 -0,328 +0,185 +0,014 -0,194 |
| WorldCover | forma | 6 / 4 / 0 | 0,754 | 0,198 | 0,270 | +0,355 +0,390 +0,569 +0,468 -0,231 +0,513 -0,096 +0,185 -0,044 -0,135 |
| MapBiomas | dice | 5 / 4 / 1 | 1,000 | 0,011 | 0,036 | +0,154 +0,182 +0,070 +0,078 -0,078 +0,077 -0,266 +0,002 -0,075 -0,033 |
| MapBiomas | forma | 6 / 3 / 1 | 0,508 | 0,013 | 0,044 | +0,082 +0,173 +0,052 +0,078 -0,090 +0,077 -0,240 +0,002 -0,036 +0,035 |

**Calibración (sin el límite)** (6 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,510 | 0,507 | 0,488 |
| WorldCover | 0,131 | 0,054 | 0,144 |
| MapBiomas | 0,430 | 0,427 | 0,426 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 5 / 1 / 0 | 0,219 | 0,379 | 0,455 | +0,427 +0,441 +0,587 +0,468 -0,164 +0,513 |
| WorldCover | forma | 5 / 1 / 0 | 0,219 | 0,344 | 0,429 | +0,355 +0,390 +0,569 +0,468 -0,231 +0,513 |
| MapBiomas | dice | 5 / 1 / 0 | 0,219 | 0,081 | 0,078 | +0,154 +0,182 +0,070 +0,078 -0,078 +0,077 |
| MapBiomas | forma | 5 / 1 / 0 | 0,219 | 0,062 | 0,078 | +0,082 +0,173 +0,052 +0,078 -0,090 +0,077 |

**Prueba** (4 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,191 | 0,167 | 0,236 |
| WorldCover | 0,272 | 0,281 | 0,258 |
| MapBiomas | 0,284 | 0,273 | 0,295 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 2 / 2 / 0 | 1,000 | -0,080 | -0,090 | -0,328 +0,185 +0,014 -0,194 |
| WorldCover | forma | 1 / 3 / 0 | 0,625 | -0,022 | -0,070 | -0,096 +0,185 -0,044 -0,135 |
| MapBiomas | dice | 0 / 3 / 1 | 0,250 | -0,093 | -0,054 | -0,266 +0,002 -0,075 -0,033 |
| MapBiomas | forma | 1 / 2 / 1 | 1,000 | -0,060 | -0,017 | -0,240 +0,002 -0,036 +0,035 |

**GFS (sin el límite)** (6 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,415 | 0,498 | 0,390 |
| WorldCover | 0,118 | 0,054 | 0,078 |
| MapBiomas | 0,378 | 0,381 | 0,365 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 5 / 1 / 0 | 0,219 | 0,297 | 0,434 | +0,427 +0,441 +0,587 +0,468 -0,328 +0,185 |
| WorldCover | forma | 5 / 1 / 0 | 0,219 | 0,312 | 0,372 | +0,355 +0,390 +0,569 +0,468 -0,096 +0,185 |
| MapBiomas | dice | 4 / 1 / 1 | 0,375 | 0,037 | 0,074 | +0,154 +0,182 +0,070 +0,078 -0,266 +0,002 |
| MapBiomas | forma | 4 / 1 / 1 | 0,375 | 0,025 | 0,065 | +0,082 +0,173 +0,052 +0,078 -0,240 +0,002 |

**ERA5** (4 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,335 | 0,349 | 0,384 |
| WorldCover | 0,292 | 0,308 | 0,358 |
| MapBiomas | 0,362 | 0,389 | 0,387 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 2 / 2 / 0 | 1,000 | 0,042 | -0,075 | -0,164 +0,513 +0,014 -0,194 |
| WorldCover | forma | 1 / 3 / 0 | 0,625 | 0,026 | -0,090 | -0,231 +0,513 -0,044 -0,135 |
| MapBiomas | dice | 1 / 3 / 0 | 0,625 | -0,027 | -0,054 | -0,078 +0,077 -0,075 -0,033 |
| MapBiomas | forma | 2 / 2 / 0 | 1,000 | -0,003 | -0,001 | -0,090 +0,077 -0,036 +0,035 |

**Sin fuga temporal de WorldCover (sin el límite)** (6 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,415 | 0,498 | 0,390 |
| WorldCover | 0,118 | 0,054 | 0,078 |
| MapBiomas | 0,378 | 0,381 | 0,365 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 5 / 1 / 0 | 0,219 | 0,297 | 0,434 | +0,427 +0,441 +0,587 +0,468 -0,328 +0,185 |
| WorldCover | forma | 5 / 1 / 0 | 0,219 | 0,312 | 0,372 | +0,355 +0,390 +0,569 +0,468 -0,096 +0,185 |
| MapBiomas | dice | 4 / 1 / 1 | 0,375 | 0,037 | 0,074 | +0,154 +0,182 +0,070 +0,078 -0,266 +0,002 |
| MapBiomas | forma | 4 / 1 / 1 | 0,375 | 0,025 | 0,065 | +0,082 +0,173 +0,052 +0,078 -0,240 +0,002 |

**Con fuga temporal de WorldCover** (4 incendios)

| | Media Dice | Mediana Dice | Media forma |
|---|---|---|---|
| CCS-BAP | 0,335 | 0,349 | 0,384 |
| WorldCover | 0,292 | 0,308 | 0,358 |
| MapBiomas | 0,362 | 0,389 | 0,387 |

| CCS-BAP contra | Métrica | Gana / pierde / empata | p (signos) | Δ media | Δ mediana | Δ por incendio |
|---|---|---|---|---|---|---|
| WorldCover | dice | 2 / 2 / 0 | 1,000 | 0,042 | -0,075 | -0,164 +0,513 +0,014 -0,194 |
| WorldCover | forma | 1 / 3 / 0 | 0,625 | 0,026 | -0,090 | -0,231 +0,513 -0,044 -0,135 |
| MapBiomas | dice | 1 / 3 / 0 | 0,625 | -0,027 | -0,054 | -0,078 +0,077 -0,075 -0,033 |
| MapBiomas | forma | 2 / 2 / 0 | 1,000 | -0,003 | -0,001 | -0,090 +0,077 -0,036 +0,035 |

### Día 1 (ventana 0): Dice y sesgo contra el incremento FIRMS; ha predichas

| Incendio | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|
| los-alerces-2023 | 0,262 / 0,62 / 482 ha | 0,048 / 0,04 / 30 ha | 0,130 / 0,23 / 182 ha |
| epuyen-2025 | 0,056 / 0,03 / 83 ha | 0,008 / 0,00 / 12 ha | 0,029 / 0,01 / 43 ha |
| los-alerces-2024 | 0,185 / 0,11 / 138 ha | 0,008 / 0,00 / 5 ha | 0,109 / 0,06 / 75 ha |
| puerto-patriada-2026 | 0,132 / 0,07 / 410 ha | 0,004 / 0,00 / 12 ha | 0,045 / 0,02 / 135 ha |
| las-golondrinas-2021 | 0,004 / 0,02 / 224 ha | 0,003 / 0,01 / 151 ha | 0,003 / 0,01 / 103 ha |
| los-alerces-2016 | 0,137 / 0,08 / 156 ha | 0,415 / 0,26 / 526 ha | 0,094 / 0,05 / 102 ha |
| cholila-2015 | 0,553 / 1,70 / 468 ha | 0,000 / 0,00 / 0 ha | 0,553 / 1,42 / 387 ha |
| el-turbio-2025 | 0,254 / 0,15 / 67 ha | 0,439 / 0,37 / 172 ha | 0,622 / 0,59 / 272 ha |
| puerto-cafe-2025 | 0,095 / 0,12 / 422 ha | 0,014 / 0,06 / 185 ha | 0,066 / 0,11 / 354 ha |
| epuyen-2019 | 0,256 / 0,54 / 427 ha | 0,289 / 3,15 / 2.521 ha | 0,284 / 0,48 / 376 ha |
| los-alerces-2015 | 0,107 / 0,11 / 158 ha | 0,348 / 0,57 / 837 ha | 0,106 / 0,09 / 128 ha |

Día 1, CCS-BAP contra WorldCover (sin el límite): gana 6, pierde 4, empata 0, p = 0,754, Δ media 0,046

Día 1, CCS-BAP contra MapBiomas (sin el límite): gana 6, pierde 2, empata 2, p = 0,289, Δ media -0,000

### ¿Cada mapa ve la cicatriz? % de GR + NB dentro / en el anillo de 2 km

| Incendio | Año del fuego | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| los-alerces-2023 | 2023 | 3 / 24 (2017) | 13 / 45 (2021) | 3 / 27 (2022) |
| epuyen-2025 | 2025 | 5 / 27 (2017) | 24 / 42 (2021) | 16 / 36 (2024) |
| los-alerces-2024 | 2024 | 0 / 33 (2017) | 7 / 41 (2021) | 1 / 31 (2023) |
| puerto-patriada-2026 | 2026 | 4 / 34 (2017) | 18 / 56 (2021) | 12 / 44 (2024) |
| las-golondrinas-2021 | 2021 | 9 / 39 (2017) | 33 / 56 (2020) | 14 / 38 (2020) |
| los-alerces-2016 | 2016 | 2 / 25 (2013) | 95 / 50 (2020) | 13 / 39 (2015) |
| cholila-2015 | 2015 | 2 / 41 (2013) | 96 / 66 (2020) | 14 / 50 (2014) |
| el-turbio-2025 | 2025 | 0 / 23 (2017) | 66 / 54 (2021) | 20 / 37 (2024) |
| puerto-cafe-2025 | 2025 | 1 / 42 (2017) | 3 / 46 (2021) | 3 / 47 (2024) |
| epuyen-2019 | 2019 | 7 / 30 (2017) | 86 / 71 (2020) | 22 / 21 (2018) |
| los-alerces-2015 | 2015 | 1 / 43 (2013) | 80 / 61 (2020) | 12 / 51 (2014) |

### Dónde: por grupo de CCS-BAP dentro de la cicatriz (última ventana)


Sin fuga temporal (2021+, sin el límite): aciertos / sobrantes en ha

| Grupo CCS-BAP | Observado | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| GR | 351 | 219 / 814 | 11 / 92 | 125 / 480 |
| GS | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SH | 8.232 | 3.659 / 4.329 | 964 / 2.010 | 3.460 / 4.295 |
| TU | 9.963 | 2.919 / 2.156 | 268 / 290 | 2.237 / 2.726 |
| TL | 3.003 | 1.134 / 1.458 | 88 / 209 | 947 / 2.018 |
| NB | 168 | 0 / 0 | 8 / 336 | 39 / 315 |

Con fuga temporal (2015-2019): aciertos / sobrantes en ha

| Grupo CCS-BAP | Observado | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| GR | 172 | 109 / 6.390 | 105 / 7.008 | 108 / 2.946 |
| GS | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SH | 4.122 | 2.317 / 11.410 | 2.032 / 12.335 | 2.002 / 7.428 |
| TU | 4.749 | 2.338 / 4.622 | 894 / 3.689 | 1.968 / 3.014 |
| TL | 1.655 | 1.059 / 1.322 | 598 / 1.443 | 972 / 1.230 |
| NB | 118 | 0 / 0 | 9 / 264 | 37 / 258 |

## No inferioridad frente a MapBiomas

Δ = CCS-BAP − MapBiomas por incendio. Estimador de Hodges-Lehmann y cota inferior unilateral exacta al 95 % (Wilcoxon de rangos con signo). CCS-BAP es no inferior si la cota supera −0,130: la mitad de la ventaja media de MapBiomas sobre WorldCover en los casos sin fuga (0,378 − 0,118). El margen se fijó después de ver las diferencias por incendio; por eso la cota se lee también por sí misma: su valor absoluto es el margen más chico que los datos sostienen, sin depender de esa elección.

| Conjunto | Métrica | n | Δ HL | Cota inferior | Nivel exacto | No inferior |
|---|---|---|---|---|---|---|
| Sin fuga (6) | dice | 6 | 0,074 | -0,098 | 95,3 % | sí |
| Sin fuga (6) | forma | 6 | 0,052 | -0,094 | 95,3 % | sí |
| Todos sin el límite | dice | 10 | 0,022 | -0,075 | 95,8 % | sí |
| Todos sin el límite | forma | 10 | 0,027 | -0,063 | 95,8 % | sí |
| Calibración | dice | 6 | 0,078 | -0,000 | 95,3 % | sí |
| Calibración | forma | 6 | 0,077 | -0,006 | 95,3 % | sí |
| Prueba | dice | 4 | -0,065 | — | — % | n insuficiente |
| Prueba | forma | 4 | -0,027 | — | — % | n insuficiente |

Sensibilidad: sin El Turbio, la cota de Dice en los casos sin fuga pasa a 0,002 (n = 5).


## Conclusión

En los seis casos sin fuga temporal, CCS-BAP obtiene Dice medio 0,415, frente a 0,118 de WorldCover y 0,378 de MapBiomas. Supera a WorldCover en 5/6 incendios y a MapBiomas en 4/6, con un empate. La dirección favorece claramente a CCS-BAP frente a WorldCover, pero la muestra es demasiado pequeña para significación en el test de signos (p = 0,219). Frente a MapBiomas, la ventaja es pequeña y tampoco concluyente (p = 0,375).

En calibración, CCS-BAP conserva la mayor media (0,510 contra 0,131 y 0,430). En prueba ocurre lo contrario: 0,191 contra 0,272 y 0,284. El Turbio explica buena parte de esa inversión. Como el conjunto de prueba no puede usarse para elegir el mapa después de observarlo, el resultado no cambia modelo-v0.

Cierre: WorldCover queda descartado como fuente principal; además de la fuga temporal en 2015–2019, falla fuertemente en la mayoría de los casos posteriores. CCS-BAP sigue siendo el mapa de modelo-v0. MapBiomas queda como el comparador competitivo: no hay evidencia suficiente para afirmar que CCS-BAP lo supera de forma general. Un eventual cambio exige un modelo-v1 predefinido y datos independientes nuevos, no otro ajuste sobre estos once incendios.

No inferioridad: con 95 % de confianza, CCS-BAP no pierde contra MapBiomas más de 0,098 de Dice en los casos sin fuga (0,075 con los diez), dentro del margen de 0,130. La afirmación que se sostiene es "no inferior a MapBiomas", no "equivalente": la cota depende casi entera de El Turbio, y una pérdida de hasta 0,1 de Dice no es despreciable. El conjunto de prueba (4) es demasiado chico para una cota exacta al 95 %.
