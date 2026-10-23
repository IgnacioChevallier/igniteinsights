# V · Humedad viva por especie (frente 6 de DIAGNOSTICO-PRECISION-E2E)

> 2026-10-22. Sin ELMFIRE. Cierra el frente 6 sin abrir receta.

## 1. Pregunta y condición

El frente 6 pedía un LW por celda (`MLW_FILENAME`, que en 2025.0212 existe, con piso de 60 %; skill
`elmfire`, `interface-gotchas.md`) a partir de una serie medida por especie que no se haya usado
para calibrar. La calibración usó de Bianchi y Defossé (2015) la banda de 110 % y eligió 100 % global
(AUDITORIA-FISICA, loop E).

Lo que no se usó es la **Tabla 2** del paper: el LFMC medio por especie, con n = 70 muestras a lo
largo de la temporada. La serie mensual sólo está en la Fig. 2a, que no se pudo leer.

| Especie | LFMC medio | Clase CCS-BAP → modelo |
|---|---:|---|
| Caña colihue | 74,9 % | Caña → SH9; sotobosque de coihue y mixtos → TU5 |
| Ñire | 135,6 % | Ñire → TU3; ñire bajo y lenga achaparrada → SH8; remanente → SH3 (por analogía) |
| Laura, radal, ciprés | 144,5; 151,9; 153,1 % | Ciprés → TU5; matorral maqui-radal-ciprés → SH4 |

## 2. Efecto esperado con Rothermel (`copa.rothermel`)

Condiciones: m1/m10/m100 = 6/8/10 %, LH 30 %, viento a media llama de 88 y 352 ft/min. La razón no
depende del viento. Se compara la ROS con el LW de la especie contra la ROS con LW 100 %, y eso se
cruza con F6 (ROS del modelo / ROS observada entre pasadas VIIRS, `F-error.md` §6):

| Clase | LW | ROS / ROS(100 %) | F6 hoy | F6 esperado |
|---|---:|---:|---:|---:|
| SH9 caña | 75 | 1,27 | — | — |
| TU5 coihue y mixtos | 75 | 1,18 | 0,49 | ≈ 0,58 |
| TU5 ciprés | 153 | 0,75 | 0,49 | ≈ 0,37 |
| TU3 ñire | 136 | 0,80 | 0,63 | ≈ 0,50 |
| SH8 | 136 | 0,70 | 0,76 | ≈ 0,53 |
| SH4 | 145–150 | 0,33–0,34 | 0,88 | ≈ 0,29 |
| SH3 | 136 | 0,78 | (no llega) | — |

## 3. Veredicto: no se abre

- El modelo ya va más lento que lo observado en todas las clases (F6: 0,49–0,88). Con el LW por
  especie, 5 de 7 clases con vivo leñoso se alejan todavía más. SH4, la clase en la que el modelo
  más se acerca, cae a un tercio.
- Sólo mejora el sotobosque de colihue: +18 % en TU5 de coihue y +27 % en la caña. No alcanza para
  acercarse a 1.
- Las medias de la Tabla 2 son de temporada, no del día de fuego. El mismo paper ubica los grandes
  incendios por debajo de 110 %, así que como valores absolutos son húmedos.
- Normalizar el orden entre especies a una media de 100 % sería una perilla [K]: F6 no resuelve un
  orden de ROS entre combustibles (±0,6 m/min), así que no hay contra qué validarlo.

Sólo reabriría la pregunta una serie del día de fuego por especie, por ejemplo de la Fig. 2a en los
meses de los incendios. Aun así, con F6 el único candidato es bajar el LW de la colihue, y eso es la
misma dirección que ya cubre la calibración global.

Doc que contradice al código: IGN-20-CROSSWALK (línea 317) y IGN-20B-FINAL §6.3 dicen que no existe
un ráster de humedad viva. Se anota en AUDITORIA-FISICA §7.4 y no se edita el doc de combustibles.
