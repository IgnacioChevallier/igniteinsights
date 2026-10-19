# A. Inventario de hipótesis y perillas probadas

Corte: 2026-10-17. Alcance: sólo lectura de documentos, de `benchmarks/recetas/*.json` (120 recetas) y de `benchmarks/iteraciones/` (sólo para saber si una receta tiene corridas). No se corrió ELMFIRE ni el benchmark, no se hizo commit y no se editó nada más.

## Cómo leer este inventario

**Abreviaturas de fuentes** (todas bajo `docs/resultados/` salvo que se indique):

- **AUD** = `AUDITORIA-FISICA.md`
- **RIESGOS** = `RIESGOS_Y_SUPOSICIONES.md`
- **PEND** = `PENDING_PARAMETERS.md` (raíz del repo)
- **MOD** = `MODELO-V0.md`
- **DIA1** = `DIA-1-PROPUESTA.md`
- **HUM** = `HUMEDAD-ALTURA-PROPUESTA.md`
- **LYQ** = `LO-YA-QUEMADO-PROPUESTA.md`
- **ENS** = `ENSAMBLE-BACKTESTS-CONSOLIDADO.md`
- **ENSP** = `ENSAMBLE-METEOROLOGICO-POC.md`
- **MAPAS** = `COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`
- **V3** = `docs/historico/RESULTADOS-CSS-BAP.md` (referencia histórica; se usa sólo donde es la única fuente de un número)

**Convenciones de números:**

- **Dice** = media / mediana de calibración (7 incendios, Las Golondrinas incluida salvo que se diga). Los números de prueba se indican aparte.
- **Alarma** = sesgo fuera de [0,5; 2] sin contar el caso límite (Las Golondrinas). AUD:1028-1030 marca ⚠ con esa regla.
- **Versiones de protocolo, no comparables entre sí:** v3 = con los bugs de la interfaz; v4 = hallazgos 1, 2, 3 y 5 corregidos; v5 = además dosel (hallazgo 4); v6 = además CBH de literatura, remanente, pérdida previa. Cuando un número no dice versión y viene de AUD loops C–E, es v4. "h54" = Alerces 2023 horizonte 54 h.
- **"Corrida"** = existe `metricas.json` en `benchmarks/iteraciones/`. Tener corrida no implica que un doc la reporte (ver §4).

## 1. Tabla de hipótesis y perillas

| # | Hipótesis / perilla | Loop o doc (archivo:línea) | Receta(s) | Resultado | Estado |
|---|---|---|---|---|---|
| 1 | Clima por banda horaria: `&MONTE_CARLO NUM_METEOROLOGY_TIMES` (ELMFIRE dejaba el clima congelado en la banda 0) | AUD:97-122 (hallazgo 1); loop A AUD:321 | Ninguna (corrección de interfaz, afecta a todas) | Banco: TOA sin viento 0 m → 1.063 m. base-001 v3→v4: +0,05 media, +0,10 mediana; Epuyén +0,31 (AUD:1074-1075) | adoptado (corrección) |
| 2 | `phi` como distancia en metros; ELMFIRE usa ±1 | AUD:124-154 (hallazgo 2); AUD:1074 | Ninguna (corrección) | Banco, avance / velocidad calculada: métrico 0,65 sin viento y 0,53 a 10 mph; ±1: 0,99 y 1,01. Sin viento, 3,6 ha frente a 9,0 ha en 3 h (AUD:138-144) | adoptado (corrección) |
| 3 | Dirección del viento interpolada como ángulo plano (170°/190° pasa por 350°→10°); `wd_for_elmfire` | AUD:156-175 (hallazgo 3); AUD:1081 | Ninguna (corrección) | Banco: crudo, centroide 54 m hacia 173° (el fuego no va al norte); corregido, cabeza a 360°, 822 m (AUD:161-164). Calibración: 0–1,6 % de los intervalos horarios afectados, sin medir aparte (AUD:289) | adoptado (corrección) |
| 4 | WAF bajo dosel con CH sin dato (CC ≥ 15 % y CH = 0 o −9999) | AUD:176-198 (hallazgo 4); loop I AUD:600-650 | Ninguna (corrección; v5) | Celdas quemables sin viento: 0,1–2,6 % según paquete (AUD:181). Efecto en Dice ≤ 0,001 (AUD:198, 647-649) | adoptado (corrección) |
| 5 | Grilla de clima más alta que ancha: la franja norte lee la fila de otra latitud (relleno al este en `write_namelist`) | AUD:200-262 (hallazgo 5); loop H AUD:576-598 | Ninguna (corrección; v5) | Banco: 0 m sin relleno, 879 m con relleno (AUD:590-591). Calibración v4: |Δws| 0,02–0,12 mph, "prácticamente sin efecto" (AUD:225). Harness A `ventanas-firms`: 54 % (legacy-ccsbap) y 51 % (humedad-m6-obs-001) de las celdas quemadas caen en la franja (AUD:232-233) | adoptado (corrección; afecta la app y el harness A, no la calibración) |
| 6 | Capa "sin ignición" (−9999) leída como quemada por `phi ≤ 0` | AUD:334-336 (loop B) | Ninguna (latente) | Ningún paquete la tenía | adoptado (corrección) |
| 7 | Sospechas descartadas: unidades de slp, orientación v3, humedad en % vs fracción, tabla de combustibles, escala del dosel, "la copa nunca se activa", convención de wd, TOA relativo, encadenado, georreferencia, DT_INTERPOLATE, orientación y hora del GFS, conversión ERA5, hora de FIRMS, alineación DEM, bordes del DEM, semilla con dominio entero (22 filas) | AUD:264-289 | Ninguna | Cada una con su experimento y sin efecto o falso positivo. "La copa nunca se activa" se refutó: con CROWN 1 el banco da 9,75× el área de CROWN 0 (AUD:274) | descartado |
| 8 | Horizonte de Alerces 2023 a 54 h (regla §2.9: el área FIRMS deja de crecer) | AUD:403-407 (loop C); AUD:1075 | calibracion-v4-h54 (protocolo, no receta) | Sesgo base 2,72 → 1,55 (AUD:1075). Se mantiene en la calibración de MOD | adoptado (protocolo) |
| 9 | ADJ uniforme 0,5 / 0,7 / 0,9 / 1,2 | AUD:376-383 (0,5 y 0,7, horizonte 72 h); AUD:412-419 (0,9 y 1,2, h54) | adj-050-001, adj-070-001, adj-090-001, adj-120-001 | Dice media/mediana: 0,5 → 0,187/0,130; 0,7 → 0,264/0,223 (72 h). 0,9 → 0,336/0,406, 1 alarma; 1,2 → 0,379/0,414, 1 alarma (h54) | descartado |
| 10 | ADJ 1,1 (candidata de loop C) | AUD:416, 421-424; superada en AUD:499-507 | adj-110-001 | h54: 0,373/0,430, 0 alarmas. Robustez a la ignición (21 corridas): 0,458/0,479, 3 alarmas (AUD:450). Superada por LW 100 % (loop E) | descartado (superado por lw-100-001) |
| 11 | ADJ 1,3 (receta de V3) | AUD:1096; robustez v3 en AUD:451 | adj-130-001 | Robustez v3: 0,398/0,454, 5 alarmas (AUD:451). "Con la interfaz corregida, sobra el ADJ" (AUD:1096) | descartado |
| 12 | ADJ 1,15 + LW 100 % (receta de V3) | AUD:1043-1044; AUD:418; AUD:425-429 | lw100-adj115-001 | v3: 0,372/0,411, 0 alarmas. v4: 0,389/0,405, 2 alarmas (AUD:1043-1044) | descartado (el ADJ extra sobra con la interfaz corregida) |
| 13 | ADJ 0,3; 0,6; 0,8; 1,4; 2,0 (barrido) | AUD:372 (el barrido de loop B se interrumpió por disco lleno); sin tabla en AUD | adj-030-001, adj-060-001 (sin corrida), adj-080-001, adj-140-001, adj-200-001 (con corrida) | Sin números en los docs. adj-030 y adj-060 no tienen ninguna carpeta de iteración | propuesto-no-corrido (030 y 060); corrida sin reporte (080, 140, 200) |
| 14 | ADJ por grupo: SH 1,5 / 2,0 / 2,5 y TU 1,3 (sólo en v3) | V3:358, 430-433, 462 ("descartada"), 865 | adj-sh-150-001, adj-sh-200-001, adj-sh-250-001, adj-tu-130-001 | v3: "+0,03 a +0,06, con alarmas. No identificable: la velocidad no sigue a la composición" (V3:865) | descartado |
| 15 | LW 100 % (humedad viva leñosa) | AUD:486-524 (loop E); AUD:1056-1058 | lw-100-001 (receta final) | v4 calibración: 0,381/0,452, 0 alarmas (AUD:493). Robustez (21): 0,460/0,480, 3 alarmas (AUD:514). v6: 0,439/0,501, 0 alarmas (AUD:846-847). Validación cruzada 7 de 7 pliegues (AUD:500) | adoptado |
| 16 | LW 95 % y LW 90 % | AUD:494-495 | lw-095-001, lw-090-001 | LW 95: 0,389/0,443, 2 alarmas. LW 90: 0,395/0,424, 2 alarmas (AUD:494-495) | descartado |
| 17 | LW 80 %, 150 % y 200 % | Sin reporte en los docs (corridas en `los-alerces-2023/cadena-96h` para lw-150 y lw-200) | lw-080-001, lw-150-001, lw-200-001 | Sin números en los docs. El motivo de lw-150 es el centro de la banda medida por Bianchi & Defossé (`lw-150-001.json`) | corrida sin reporte (no adoptado; la receta final es LW 100 %) |
| 18 | LW 105 % y LW 95 % "con todo" (la combinación completa) | AUD:826 | lw105-full-gr2-001, lw95-full-gr2-001 (y lw105-lit-altorem2-001) | Con todo: LW 95 → 0,444/0,524, 1 alarma; LW 105 → 0,431/0,485, 0 alarmas (AUD:826). Alerces 2016 se pasa, sesgo 1,69 (motivo de lw105-full-gr2) | descartado |
| 19 | Dosel coherente: sin dosel en GR/GS/SH, como LANDFIRE (sospecha 6) | AUD:394-397 (loop C); AUD:1079 (loop L); AUD:726 (loop K, v5); AUD:1120-1126 | dosel-coherente-001; lw100-dosel-coherente-001 | v4: 0,365/0,417, 3 alarmas (AUD:419). Efecto medio ±0; Patriada +0,10, Alerces 2016 −0,12 (AUD:1079). Se documenta como incoherencia de insumos, no como corrección (AUD:397) | descartado |
| 20 | Sin dosel sólo en SH4; sin dosel sólo en SH8 | AUD:817 (SH4); AUD:1282-1287 (SH8, cualitativo) | lw100-sin-dosel-sh4-001; lw100-sin-dosel-sh8-001 | SH4: 0,385/0,452, 1 alarma (AUD:817). SH8: "sin él, Alerces 2023 y 2024 se pasan" (AUD:1286-1287), sin número | descartado |
| 21 | Pérdida previa de Hansen (lossyear): sin dosel donde Hansen marca pérdida antes del año del incendio | AUD:798-800, 839-841 (loop L); AUD:846-858 (v6) | lw100-perdida-001 (sin tabla propia); `dosel_sin_perdida_previa` en lw100-remsh3/8-perdida-001 y en las variantes lit-*-perd | Parte de la calibración v6: 0,439/0,501 con todo (AUD:846-847) | adoptado (v6) |
| 22 | CBH uniforme como factor del CBH derivado (×0,25, ×0,35, ×0,5) | AUD:532-551 (×0,25, diagnóstico, loop F); AUD:818 (×0,5, loop L) | cbh-025-001 (diag), lw100-cbh025-001, lw100-cbh035-001, lw100-cbh050-001 | ×0,5: 0,399/0,439, 0 alarmas (AUD:818), no adoptado. ×0,25 (v4): Cholila 0,528/0,90 (de 0,255); Alerces 2016 0,338/1,76; Alerces 2023 h54 0,400/2,50 ⚠ (AUD:537-542) | descartado (×0,25 es diagnóstico, no candidata) |
| 23 | CBH de literatura por tipo de bosque (TL6 6 m, TL5 4 m, TU5/TU3/TL8 1,5 m, TL2 1 m; CBD de pino 0,16) | AUD:819, 839-847; AUD:1006-1007; limitación 11 del crosswalk | lw100-cbh-lit-001; lw100-cbh-lit-shsc-001 (shsc agrega SH sin copa) | Loop L: 0,414/0,495, 1 alarma (2,03) (AUD:819). Se adopta en v6 (AUD:839-847). PEND:31 lo deja con confianza media salvo pino | adoptado |
| 24 | CBH de TU5 (caña) a 2,5 m en vez de 1,5 m | AUD:869-871 | lw100-full-gr2-tu25-001 | Alerces 2016 vuelve a 0,427, pero Cholila cae a 0,313. "No hay un valor que sirva a los dos" (AUD:869-871) | descartado |
| 25 | TL8 → TU5 (copa del matorral de TL8) | AUD:1135-1137 | diag-tl8-tu5-001; diag-lw100-tl8-tu5-001 | Epuyén 0,500 → 0,503 con v5 (AUD:1136). En v3 era +0,05 (AUD:1136) | descartado (sin efecto) |
| 26 | Copa desactivada (CROWN_FIRE_MODEL 0) | Receta `benchmarks/recetas/copas-off-001.json:7-10`. Corridas: `benchmarks/iteraciones/{los-alerces-2023/cadena-96h, epuyen-2025/cadena-96h-interior, epuyen-2025/cadena-96h-lago}/copas-off-001/metricas.json`. Ningún doc la reporta | copas-off-001 | Dice idéntico al de base-001 en las tres: 0,484; 0,135; 0,107 (sesgos 1,05 / 0,21 / 0,20). Las corridas son de los commits 482f1f5 (base, 2026-09-21) y 1c07b67 (copas-off, 2026-09-27), con manifiesto `sucio: true`, antes de la auditoría aplicada el 2026-09-30 (AUD:1087). V3:230 y `docs/historico/RESULTADOS.md:308` ya registraban TOA idéntico con CROWN 0 y 1 antes de los fixes | descartado (preliminar, pre-auditoría; no concluyente) |
| 27 | Diagnóstico de copa fuera de línea (Opción 3 de DIA1): CFIS (Cruz et al. 2004) contra Van Wagner + Rothermel, que es lo que hace ELMFIRE | DIA1:348-408 (opción 3); DIA1:680-715 (§7.4); DIA1:729-770 (§7.6) | Ninguna (sin corrida ELMFIRE; `scripts/benchmark.py copa`) | Día 1: copa en 68–100 % de las celdas con CFIS, 0,5–30 % con Van Wagner. Alerces 2023: CFIS 0,99 vs VW 0,005; Epuyén: 1,00 vs 0,30 (DIA1:684-690) | límite (no se abre un modelo-v1 por copa, DIA1:729-770) |
| 28 | Rugosidad z0 = 0,13 × altura del dosel, en vez del escalar 0,22 m | V3:870, 879-882; PEND:27 | z0-dosel-001 | v3: −0,02 (V3:870). Alerces 2023: 0,442 vs 0,457 (V3:882). z0 0,22 m queda congelada (PEND:27) | descartado |
| 29 | Viento ×1,3 y ×1,6 sobre el clima; ERA5 ×1,3 al empaquetar (loop D) | V3:864; AUD:430-433 (`viento-130` sobre ERA5 v4); AUD:462-482 (loop D); AUD:1080 | viento-130-001, viento-160-001, combo-adj130-v130-001, extremo-001 (envolvente, no calibración) | v3 GFS: +0,026 (×1,3) y +0,051 (×1,6), peor con ERA5 (V3:864). v4 ERA5 ×1,3: Epuyén 0,455/1,30 frente a 0,466/1,30 del GFS (AUD:431). Loop D: −0,004 media, Alerces 2016 −0,04 (AUD:1080). "v4w queda como sensibilidad" (AUD:481-482) | descartado (sensibilidad) |
| 30 | Atlas de viento WindNinja (16 direcciones, 90 m) | V3:867; AUD:563 (loop G, v4); AUD:966 (loop M, v6); AUD:747 (loop K) | viento-atlas-001; lw100-atlas-001; adj130-atlas-001 | v3: −0,011 GFS, +0,020 ERA5 (V3:867). v4: 0,380/0,480, 0 alarmas (AUD:563). v6: 0,417/0,483 frente a base 0,439/0,501 (AUD:966). Ayuda en laderas (Alerces 2016 +0,056 en v4, AUD:569-570) | descartado (neutro o negativo en la media) |
| 31 | Rotación empírica del viento (30°, 45°, 60°) | V3:868; AUD:553-575 (loop G); AUD:747 (test Alerces 2015) | rotacion-030-001 y -045-001 (sin corrida), rotacion-060-001, lw100-rot030-001, adj130-rot030/045/060-001 | v3: +0,002 (V3:868). v4 con +30°: 0,393/0,473, 1 alarma (Epuyén 2,09) (AUD:562, 567). No está claro qué receta produjo el +0,002 de V3 | descartado (corrección empírica, no física; AUD:567-568) |
| 32 | WindNinja con flujos diurnos (`viento_diurno`: dirección, velocidad o ambos) | AUD:948-984 (loop M) | lw100-diurno-001, lw100-diurno-002, lw100-diurno-dir-001, lw100-diurno-vel-001 | Ambos (diurno-002): 0,426/0,487, 0 alarmas. Sólo dirección: 0,411/0,487. Sólo velocidad: 0,450/0,490, 0 alarmas (AUD:963-969). No se adopta: mediana más baja y Alerces 2023 con sesgo 1,97 (AUD:974-982) | descartado (medido, no adoptado) |
| 33 | Viento de la estación El Bolsón en vez del GFS (Las Golondrinas) | RIESGOS:231-234 | Ninguna (prueba con estación) | Dice 0,029 → 0,020: la ráfaga de 29 mph dura una hora (RIESGOS:232-234). Salvedad (W): 118 de las 145 horas de Meteostat son relleno, no SYNOP | descartado |
| 34 | Orientación del terreno: `aspecto_mas_180` (bug de `raster_aligner` en v3) | V3:886 | aspecto-corregido-001 | base-001 Alerces 2023: 0,425 → 0,457; Alerces 2016: 0,301 → 0,433 (V3:886) | adoptado (corrección) |
| 35 | Estepa CCS-BAP (OT Herb-Subarb) → GR2; y sobre 1.300 m → NB9 (altoandina) | AUD:715-718 (loop K, diagnóstico); AUD:820-821 (loop L); AUD:986-990 (loop M); AUD:1138-1142, 1288-1294 | diag-lw100-gr3-nb-001; lw100-gr3-gr1-001; lw100-gr3-gr2-001; lw100-x-alto-001; lw100-lit-altorem2-001 | Prueba Alerces 2015 con GR3 → NB9: falso positivo 1.284 → 907 ha, Dice 0,298 → 0,342 (AUD:715-718). Calibración: GR1 0,381/0,459; GR2 0,379/0,457; sobre 1.300 m → NB9 0,390/0,447; 0 alarmas en las tres (AUD:820-821). Hay una ambigüedad en AUD:821 (ver §4) | adoptado (GR2, y sobre 1.300 m → NB9) |
| 36 | Lenga achaparrada (OFL Le) → SH3 | HUM:277-281; AUD:822 | lw100-x-lach3-001 | Calibración: 0,373/0,448, 1 alarma (AUD:822). Cholila 0,280 → 0,213 (HUM:277-281) | descartado (SH8 se mantiene, HUM:41) |
| 37 | Lenga achaparrada → TL6 (el modelo del bosque de lenga) | HUM:265-276 (§4.1 c) | Ninguna (no corrida) | Argumento: la región la ve arder la mitad que sus vecinas, pero el dato choca con el resultado de SH3 (HUM:277-287). TL6 queda entre SH3 y SH8 | propuesto-no-corrido (rechazado por argumento) |
| 38 | Humedad de la hojarasca bajo dosel de lenga (ajuste de Δm1 por altura o cobertura) | HUM:246-251 (§4.1 a) | Ninguna | No hay valor medido con qué fijarlo. El único microclima medido suma ~+1 pp al m1 (HUM:248-250) | propuesto-no-corrido (rechazado: sin dato) |
| 39 | Bosque de lenga de altura con un modelo más lento (TL6 más lento) | HUM:252-264 (§4.1 b) | Ninguna | Calibración: TL6 con sesgo 0,99. Un modelo más lento sacaría 1.351 ha de acierto para arreglar un caso de prueba (HUM:252-264) | propuesto-no-corrido (rechazado) |
| 40 | Remanente de disturbio → SH3 (con pérdida previa) | AUD:822-823; AUD:1177-1179 | lw100-remsh3-001; lw100-remsh3-perdida-001; lw100-lit-altoremsh3-perd-001 (y variantes gr1/gr2) | Remanente → SH3 + pérdida previa: 0,398/0,493, 0 alarmas (AUD:823). Combinación completa: 0,440/0,501, 0 alarmas (AUD:827) | adoptado |
| 41 | Remanente → SH8 | AUD:1177-1180 | lw100-remsh8-001; lw100-remsh8-perdida-001; lw100-lit-altoremsh8-perd-gr1-001 | lw100-remsh8-001: Patriada 0,489 frente a 0,496 (no pasa el criterio fijado antes de correr); sesgo 0,92 frente a 0,70; Alerces 2016 igual (AUD:1178-1180) | descartado |
| 42 | Pérdida previa como remanente SH3 o SH2 | AUD:912-923 (loop M) | lw100-perdsh3-001; lw100-perdsh2-001 | sh3: 0,417/0,502, 1 alarma; Patriada 0,334 ⚠. sh2: 0,403/0,497, 1 alarma; Patriada 0,233 ⚠ (AUD:919-920). "Patriada ardió rápido… y como matorral se frena de más" (AUD:922-923) | descartado |
| 43 | Remanente → GS2 | Sin reporte en los docs | lw100-x-rem2-001 | Sin números en los docs. El remanente adoptado es SH3 (PEND:30) | corrida sin reporte (no adoptado) |
| 44 | Quema reciente de 0–2 años → NB9 o GR1 | AUD:825 | lw100-full-rec1nb-001; lw100-full-rec2gr1-001 | "+0,000 | 0 alarmas" (AUD:825) | descartado (sin efecto) |
| 45 | Quema por edad: 1–5 años → GR1, 6–15 años → SH3, con la capa de Hansen más MCD64A1/dNBR | LYQ:390-420 (LYQ-1, §9); LYQ:565-600 (LYQ-3, §11); RIESGOS:361-362 | lw100-quema-edad-001 (LYQ-1); lw100-quema-edad-002 (LYQ-3) | LYQ-1: 0,440/0,505 frente a 0,439/0,501 (Δ media +0,001; Δ mediana +0,004). LYQ-3: peor caso Alerces 2023 con −0,006 (RIESGOS:361-362) | adoptado en la app (no cambia modelo-v0) |
| 46 | Supresión (`&SUPPRESSION`): contención de 30 %/día, 60 %/día y la plantilla de 120 %/día | AUD:925-946 (loop M); RIESGOS:41-55 | lw100-supresion-30-001; lw100-supresion-60-001; lw100-supresion-001 (120 %, sin carpeta de iteración) | 30 %: 0,411/0,471, 0 alarmas. 60 %: 0,368/0,410, 1 alarma. 120 %: la cadena de ventanas no completa (AUD:931-934). Sólo mejora Alerces 2024 (AUD:942). Base: 0,439/0,501 | límite (no adoptada; MOD: "no promete reproducir supresión") |
| 47 | Pavesas con la plantilla de hindcast | AUD:806-808, 831-833 (loop L) | lw100-pav-001; lw100-cbh050-pav-001 | "No encienden ni un foco": TOA idéntico byte a byte en Alerces 2016 (AUD:831) | descartado |
| 48 | Pavesas fuertes: 10 % copa / 1 % superficie; intermedia 3 % / 0,3 % | AUD:824, 831-833 (loop L) | lw100-cbh050-pavx10-001; lw100-cbh050-pavx3-001 | 10 %/1 % con CBH × 0,5: 0,415/0,468, 2 alarmas (AUD:824). Cholila sube de 0,425 a 0,514, pero Alerces 2023 y Epuyén se pasan (AUD:831-833). La variante x3 no tiene número | descartado |
| 49 | Humedad muerta uniforme: −2, −4, −6 puntos en m1/m10/m100; −6 sólo en m1 | PEND:25; V3:879-880; V3:433 (m6 en v3) | humedad-m2-001; humedad-m4-001; humedad-m6-001; humedad-m1-m6-001; combo-adj130-hm2/hm4-001; combo-adj160-hm4-001 | v3: "el delta uniforme no tiene soporte" (V3:879). El −6 sólo en m1 da 2/3 del efecto del −6 completo; m10/m100 son insensibles (V3:880). Sin reporte en v4 | descartado |
| 50 | Humedad con gradiente de altura (`altura-001`: T llevada al DEM con −6,5 °C/km) | RIESGOS:267-276; AUD:782-784; HUM:41 | altura-001 | Dice ±0,01. Alerces 2015: 0,276/0,99 frente a 0,255/0,96; falso positivo 818 → 817 ha (AUD:782-784) | límite (cerrado como límite el 2026-10-12, HUM:41; AUD:1143-1149) |
| 51 | Fosberg (tablas de Rothermel/Fosberg con corrección por altura) | V3:866; RIESGOS:271-275 | fosberg-001 | ±0,01 (V3:866) | descartado |
| 52 | Humedad con historial de secado (retardo τ = 1 h, 120 h de historia) | V3:880 (que cita `docs/historico/RESULTADOS.md` §8) | humedad-retardo-001; retardo-adj130-001 | m100 baja a ~11 % sin cambiar el resultado (V3:880). Sin número en v4 | descartado (sin efecto, v3) |
| 53 | Humedad viva herbácea LH 30 % frente a 60 % (y barrido 30–120 %) | AUD:664-676 (loop J); AUD:1264-1275 (§6.3); PEND:24 | lh-060-001 (sin resultado propio) | Anillo CCS-BAP 12 h: LH/LW 30 % 14.120 ha; 60 % 13.241 ha. Factor entre 30 % y 120 % = 2,53 (AUD:1267-1275). LH 30 % es la convención declarada (PEND:24) | adoptado (LH 30 %); LH 60 % descartado |
| 54 | Paso de tiempo `dt_s` / `dtmax_s` a la mitad (15 s / 150 s) | PEND:26; V3:869 | paso-mitad-001 | +0,003 de Dice (V3:869). Convergido | adoptado (convergencia: 30 s / 300 s) |
| 55 | Mapas de combustible: CCS-BAP frente a MapBiomas frente a WorldCover | MAPAS (tabla :5-20; conclusión :209-217); AUD:1229-1260 (loop J, §7.1) | fuels-mapbiomas-001; fuels-worldcover-001 y -002; lw-100-mapbiomas-001; lw-100-worldcover-001; lw-100-worldcover2021-001; legacy-mapbiomas; legacy-worldcover | Calibración: CCS-BAP 0,510; WorldCover 0,131; MapBiomas 0,430. Prueba: CCS-BAP 0,191; WorldCover 0,272; MapBiomas 0,284 (MAPAS:209-217). Sin fuga temporal (6 incendios): 0,415 / 0,118 / 0,378. Harness B tras el loop J, IoU: 0,046 / 0,010 / 0,035 (AUD:1245-1252) | adoptado: CCS-BAP. WorldCover descartado. MapBiomas, no inferior (MAPAS:191-207) |
| 56 | Ignición ±500 m y ±2 h (robustez de la semilla) | AUD:435-452 (loop C); AUD:508-517 (loop E); AUD:874-886 (loop L) | Protocolos `-ign-*` y `-v6*-ign-*` sobre lw-100-001 | v4 lw-100-001: 0,460/0,480, 3 alarmas (AUD:514). v6: 0,461/0,497, 2 alarmas; gana a base en 12 de 21 (AUD:880-884) | adoptado (criterio de robustez; no es un parámetro) |
| 57 | Ensamble meteorológico GEFS: c00 más 30 perturbados, sólo clima | ENS:250-258 (veredicto); ENS:304-321 (mejora predictiva); ENSP:37 | Ninguna receta (`scripts/run_ensemble_backtest_*.py`); 23 de 23 backtests | Sin mejora predictiva. ≥ 0,80: Δ IoU ≤ 0,003, Patriada empeora (−0,0008 y −0,0030). ≥ 0,10: más recall, pero menos IoU en 4 de 4 incendios a 12 h (ENS:304-321) | límite (capa de acuerdo con limitaciones; no se promueve) |
| 58 | SMN WRF 4 km como escenario regional independiente | ENSP:30, 52-64, 145-147, 256-265; `docs/resultados/DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md:95-98` | Ninguna; sólo prototipo `scripts/weather_ensemble_poc.py download-smn` | Una hora descargada y recortada a 66 × 50 (ENSP:145-147). Sin corrida ELMFIRE (ver §3c). Puerta en estaciones (W, 2026-10-18): 1 de 3 estaciones, no pasa | descartado (puerta de estaciones) |
| 59 | P-24: pronóstico desde la última pasada VIIRS (reinicio en cada pasada) | DIA1:612-648 (§7.2); DIA1:717-727 (§7.5); RIESGOS:199-203 | lw-100-obs-001; pronostico-v6 y pronostico-oraculo-v6 (12 casos) | Mediana de ΔDice contra la cadena v0: +0,107 a 12 h (6 de 6 incendios) y +0,141 a 24 h (5 de 6). Contra persistencia: +0,062 y +0,107. Semilla oráculo: +0,168 y +0,163 (DIA1:612-648) | adoptado (protocolo operativo; no cambia modelo-v0) |
| 60 | Sesgo del día 1 y semilla FIRMS frente a oráculo | DIA1:649-678 (§7.3); RIESGOS:128-156 | Cadena v0 frente a P-24 | Sesgo a 24 h (FIRMS / oráculo): Alerces 2016 1,16 / 1,01; Epuyén 2,06 / 2,68; Patriada 0,47 / 0,51; Alerces 2024 0,28 / 0,35. Las 2–6 h antes de la primera pasada no son pronosticables (RIESGOS:205-206) | límite (declarado) |
| 61 | Opción 2 de DIA1: ajuste de velocidad asimilado por ventana (`ADJ_k` = r_obs / r_sim, con tope [1/4, 4]) | DIA1:295-347 (§3); condición en DIA1:559-562 (§6); decisión en DIA1:722-724 (§7.5) | Propuesta `lw-100-obs-adj-001` (nunca creada); `adj_asimilado` no existe en el código | Nunca corrida. §7.5 la descarta porque "el ΔDice no es chico" y el error tardío es supresión (DIA1:722-724), sin correr la variante. Ver §3a | propuesto-no-corrido |
| 62 | Opción 4 de DIA1: viento sostenido inferido de la ráfaga (ERA5 `fg10`, GFS `GUST`) | DIA1:432-476 (§5.2); requisito en DIA1:446; decisión en DIA1:563-567 | Ninguna | Nunca corrida. Requiere antes comparar ráfagas con estaciones (DIA1:446) | propuesto-no-corrido |
| 63 | Opción 5 de DIA1: fluctuaciones de viento de ELMFIRE (`WIND_FLUCTUATIONS`) | DIA1:477-511 (§5.3); decisión en DIA1:563-567 | Ninguna | Nunca corrida. Impacto esperado bajo: ≈ +3 % de velocidad media (DIA1:490-496) | propuesto-no-corrido |
| 64 | Opción 6 de DIA1: pavesas con inventario independiente de focos secundarios | DIA1:512-544 (§5.4); requisito en DIA1:530-534; decisión en DIA1:563-567 | Ninguna (distinta de las pavesas de la plantilla, filas 47–48) | Nunca corrida. Requiere un inventario externo que no existe (DIA1:530-534) | propuesto-no-corrido |
| 65 | Copa vía insumos: CBH "equivalente" o humedad foliar por celda (`FMC_FILENAME`) | DIA1:745-752 (§7.6) | Ninguna | Rechazado por argumento: "meten valores sin sentido físico" (DIA1:745-752) | propuesto-no-corrido |
| 66 | Modelo de iniciación de copa alternativo dentro de ELMFIRE (CFIS o viento abierto) | DIA1:396-400 (§3); DIA1:729-770 (§7.6); RIESGOS:208-211 | Ninguna | ELMFIRE 2025.0212 tiene un solo criterio de iniciación y no se cambia la versión (DIA1:396-397) | propuesto-no-corrido |

## 2. Recetas por familia

Las 120 recetas se asignaron a una familia cada una, sin repetir (verificado por script sobre `benchmarks/recetas/*.json`). La última columna cuenta cuántas tienen `metricas.json` en `benchmarks/iteraciones/`.

| Familia | Recetas (n) | Con corrida | Qué variaban | Resultado si algún doc lo reporta |
|---|---:|---:|---|---|
| Base y referencias | 4 (base-001, legacy-ccsbap, legacy-mapbiomas, legacy-worldcover) | 4 | Punto de partida; config de `RESULTADOS.md` (corte 2026-09-19) | base-001 v3: 0,312/0,340 (AUD:1043). v4: 0,359/0,444 (AUD:414) |
| Mapas de combustible | 6 | 6 | Fuente CCS-BAP, MapBiomas o WorldCover; año | Ver fila 55 (MAPAS) |
| ADJ uniforme | 12 | 10 | ADJ de 0,3 a 2,0 | Ver filas 9–13. Sin corrida: adj-030 y adj-060 |
| ADJ por grupo (SH, TU) | 4 | 4 | ADJ de 1,3 para TU; 1,5 / 2,0 / 2,5 para SH | v3: "+0,03 a +0,06, con alarmas" (V3:865). Descartado |
| ADJ combinado con otra perilla | 5 | 5 | ADJ con viento, humedad, LW o envolvente | lw100-adj115 (v3 0,372/0,411; v4 0,389/0,405, 2 alarmas). extremo-001 sin número |
| LW (humedad viva leñosa) | 6 | 6 | LW de 80 % a 200 % | LW 100 %: 0,381/0,452 (v4), adoptado. LW 95 y 90: 2 alarmas cada una. LW 80, 150 y 200 sin número |
| Humedad (muerta, altura, Fosberg, retardo, LH) | 12 | 12 | Delta −2/−4/−6; sólo m1; altura; Fosberg; retardo; LH 60 %; ADJ 1,3 combinado | Delta uniforme: sin soporte (PEND:25). Altura ±0,01 (RIESGOS:274-276). Fosberg ±0,01 (V3:866). Retardo sin efecto (V3:880). LH 60 %: anillo 13.241 frente a 14.120 ha (AUD:1269-1270) |
| Dosel, copa y CBH | 15 | 15 | Copa desactivada; CBH × 0,25 / 0,35 / 0,5; CBH de literatura; dosel coherente; sin dosel en SH4 / SH8; pérdida previa; TU5 a 2,5 m; z0 | CBH de literatura: adoptado (loop L). CBH × 0,5: 0,399/0,439 (no adoptado). Copa desactivada: igual que base en 3 iteraciones pre-auditoría (fila 26) |
| Combustible: crosswalk, remanente, quema, pérdida previa | 28 | 28 | Estepa → GR1 / GR2 / NB9; lenga achaparrada → SH3; remanente → SH2 / SH3 / SH8 / GS2; quema 0–2 años; pérdida previa; TL8 → TU5; diagnósticos | Adoptado: Estepa → GR2 y sobre 1.300 m → NB9; remanente → SH3 + pérdida previa (0,398/0,493). Descartado: lach3 (Cholila 0,213), remsh8 (Patriada 0,489 frente a 0,496), perdsh2/sh3 (1 alarma), quema 0–2 años (+0,000) |
| Viento (factor, rotación, atlas, diurno) | 16 | 14 | ×1,3 y ×1,6; ERA5 ×1,3; rotación 30°/45°/60°; atlas; diurno (dirección, velocidad, ambos) | Ver filas 29–34. Sin corrida: rotacion-030-001 y rotacion-045-001 |
| Topografía (orientación) | 1 | 1 | `aspecto_mas_180` | Corrección: Alerces 2023 0,425 → 0,457 (V3:886). Adoptado |
| Supresión | 3 | 2 | Contención 0 / 30 / 60 %/día; la plantilla de 120 %/día no completa la cadena | 30 %: 0,411/0,471. 60 %: 0,368/0,410, 1 alarma. Descartado o límite (fila 46) |
| Pavesas | 4 | 4 | Plantilla de hindcast; 10 %/1 %; 3 %/0,3 %; con CBH × 0,5 | Plantilla: TOA idéntico en Alerces 2016. 10 %/1 %: 0,415/0,468, 2 alarmas (fila 47–48) |
| Observación / pronóstico | 3 | 3 | Semilla observada FIRMS; humedad m6 con semilla observada | P-24: +0,107 a 12 h y +0,141 a 24 h de ΔDice contra la cadena (fila 59) |
| Numérica | 1 | 1 | `dt_s` 15 s y `dtmax_s` 150 s | +0,003 de Dice; convergido (fila 54) |
| **Total** | **120** | **115** | | |

Fuera de las recetas, el ensamble GEFS (fila 57) corrió 23 backtests sin pasar por `benchmarks/recetas/`.

## 3. Nunca probado o sólo argumentado

Verificación con `grep` sobre `app/`, `scripts/`, `tests/`, `benchmarks/recetas/` y `docs/`, y con la existencia de carpetas en `benchmarks/iteraciones/` y `data/ensemble-poc/`.

### (a) ADJ adaptativo por ventana o asimilado: no corrido

- **Código:** `grep -rn -i "asimilad|adj_asimil|ADJ_k|adaptativ|assimil"` en `app/`, `scripts/` y `tests/` no devuelve nada que implemente el ajuste. No existe `adj_asimilado` en `app/validation/definiciones.py`.
- **Recetas:** ninguna en `benchmarks/recetas/` menciona "asimil". La receta `lw-100-obs-adj-001` que DIA1:326-331 anuncia no existe; sólo hay `lw-100-obs-001`, `humedad-m6-obs-001` y `semilla-observacion-001`.
- **Docs:** sólo aparece como propuesta en DIA1:295-347 y como no adopción en DIA1:722-724.
- **Lo que sí existe:** ADJ estático uniforme (filas 9–13) y ADJ estático por grupo (fila 14, v3). Ninguno es adaptativo.
- **Pendiente:** la condición de DIA1:559-562 ("sólo si el ΔDice de P-24 queda chico en k ≥ 1") nunca se evaluó con una corrida de la opción.

### (b) Ensamble con perturbación de parámetros (PERTURB_ADJ, humedad, combustible): no corrido

- **Código:** `grep -rn "PERTURB|perturb"` en `app/`, `scripts/` y `benchmarks/recetas/` no encuentra uso. La única aparición de `PERTURB_ADJ` es la fórmula de ELMFIRE citada en DIA1:309.
- **Ensamble GEFS:** perturba sólo el clima (ENSP:37, c00 y p01–p30). `scripts/weather_ensemble_poc.py` copia `adj.tif` y `fuel_models.csv` sin cambios (líneas 50-51 y 353-355). `app/ensemble/` no toca LW, ADJ, humedad ni combustible.
- **Única perturbación que no es de clima:** la ignición (±500 m y ±2 h, 21 corridas: AUD:435-452, 508-517, 874-886). Es perturbación de la semilla, no de parámetros.
- **Sólo citado:** Pyrecast "perturbando viento, humedades y pavesas" (DIA1:131-133, Lautenberger 2023). No se implementó.

### (c) SMN WRF 4 km como meteorología principal: no corrido (sólo prototipo)

- **Código:** `app/ensemble/sources.py:376-439` tiene el adaptador SMN, etiquetado "escenario regional SMN WRF". `scripts/weather_ensemble_poc.py:747-748` tiene el subcomando `download-smn`.
- **Docs:** ENSP:30 dice que nunca entra al denominador GEFS. ENSP:52-64 describe la fuente y ENSP:59 señala que los ciclos varían entre fuentes (00/06/12/18 o 00/12). ENSP:145-147 reporta una sola hora descargada y recortada a 66 × 50. ENSP:256-265 trae el comando para 24 h, pero no hay evidencia de que se haya ejecutado.
- **Ausencias:** no hay recetas SMN en `benchmarks/recetas/` (cero coincidencias de "WRF" o "SMN"). No existe `data/ensemble-poc/2026101200/smn-wrf` (sólo hay `gefs/` e `inputs/` con c00 y p01–p30). Ningún doc reporta una corrida de ELMFIRE con SMN.
- **Posterior (2026-10-18):** la puerta de estaciones del frente 4 se midió sin ELMFIRE
  ([W-viento-estaciones](W-viento-estaciones.md)). WRF no pasa (1 de 3 estaciones), así que la
  ingesta como meteorología principal queda descartada.

### (d) Opciones de copa distintas de Van Wagner (CROWN_FIRE_MODEL, CRITERIO, FMC_FILENAME, etc.): no, salvo apagar la copa

- **`CROWN_FIRE_MODEL`:** sólo se probó 0 y 1. El 0 está en `benchmarks/recetas/copas-off-001.json:10` (corridas sin reporte, fila 26). El 1 es el default de `app/elmfire/builder/namelist_writer.py:61` y se escribe explícito en `:421`. `scripts/pruebas_fisicas.py:527-528` compara 1 contra 0 en el banco.
- **`CRITERIO`:** cero coincidencias en `app/`, `scripts/`, `benchmarks/` y `docs/`.
- **`FMC_FILENAME`:** cero usos en `app/`, `scripts/` y `benchmarks/recetas/`. Sólo se menciona como clave disponible en `&INPUTS` (DIA1:747) y se descarta por argumento (DIA1:745-752).
- **CFIS:** existe sólo como diagnóstico fuera de línea (`app/validation/copa.py`; DIA1:680-715). ELMFIRE no lo usa.

### (e) Velocidad de propagación empírica entre pasadas VIIRS por combustible: no existe

- La única velocidad empírica por combustible es una quema experimental: un frente de 40 m en 30 s, 4.800 m/h en pico bajo ráfaga, con llama de 3 a 4 m (`docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md:633`). Es la PT-37 (Cerro Jones, 2011) y se contrasta con los modelos SH8, SH4, GS3, SH9 y SH5 (IGN-20B:644-646; AUD:1199-1216; `scripts/paso4_quema_a4.py`). Es una sola quema, no pasadas VIIRS.
- Por incendio sí hay crecimiento observado entre pasadas (DIA1:649-678; RIESGOS:128-156), sin desagregar por combustible.
- Una búsqueda de "ROS", "m/h" y "entre pasadas" en `scripts/` no encontró ningún cálculo de velocidad por combustible.

### Otras ideas sólo argumentadas (sin corrida)

- Opciones 4, 5 y 6 de DIA1 (filas 62–64).
- Lenga achaparrada → TL6 y las dos alternativas de lenga de altura (filas 37–39).
- Copa vía insumos y modelo de iniciación alternativo (filas 65–66).
- Dosel más reciente que Hansen 2000 (AUD:1127-1129): dice que la cobertura tiene 17–25 años más, pero no hay corrida con dosel más nuevo.
- CBH de inventario regional (PEND:31; RIESGOS:41): sin dato.
- Estación en Trevelin o Cholila (RIESGOS:236-249): sin serie para las fechas.

## 4. Inconsistencias y ambigüedades detectadas

1. **AUD:821** dice "sí, GR2, por la alarma" para la fila Estepa, pero GR1 y GR2 tienen 0 alarmas en esa misma tabla (AUD:820-821). AUD:986-990 justifica GR2 por carga y `mex`, no por alarmas. Lectura adoptada aquí: GR2 por el argumento de carga.
2. **Dos cifras para la misma configuración final:** "todo junto" 0,440/0,501 (AUD:827, sobre v5) y lw-100-001 sobre v6 con 0,439/0,501 (AUD:846-847). El doc no dice si son la misma configuración de insumos; no lo verifiqué.
3. **Opción 2 de DIA1:** la condición de decisión (DIA1:559-562) depende de un resultado que nunca se midió, y §7.5 (DIA1:722) la descarta sin correrla.
4. **Comparabilidad de ADJ:** los valores de 0,5 y 0,7 (AUD:380-381) son de horizonte 72 h, y los de 0,9 y 1,2 (AUD:415-417) son de h54. No son comparables directamente.
5. **Copa desactivada (fila 26):** hay 3 iteraciones con resultados, pero ningún doc las reporta, y son anteriores a los fixes.
6. **Rotación:** `rotacion-030-001` y `rotacion-045-001` no tienen iteraciones. El +0,002 de V3:868 no dice qué receta lo produjo.
7. **Supresión de 120 %/día:** `lw100-supresion-001` no tiene carpeta de iteración. AUD:931-934 dice que la cadena no completa, así que no hay métricas que guardar.
8. **ADJ 0,3 y 0,6:** `adj-030-001` y `adj-060-001` no tienen iteración. AUD:372 dice que el barrido de loop B se interrumpió por disco.
9. **Recetas corridas sin mención por ID:** 115 recetas tienen corrida. De ellas, 86 no aparecen por ID en AUD y 65 no aparecen en ningún doc de `docs/` ni en `PENDING_PARAMETERS.md`. Una corrida no garantiza que haya reporte.

## 5. Fuentes no leídas

- `docs/resultados/COMPARACION-MAPAS-V5.md`, `docs/resultados/ESTADO-RESEARCH.md` y `docs/crosswalk/*` (sólo se consultaron las citas dentro de AUD).
- `docs/historico/RESULTADOS.md` (sólo para la cita de `docs/historico/RESULTADOS.md:308` y §8).
