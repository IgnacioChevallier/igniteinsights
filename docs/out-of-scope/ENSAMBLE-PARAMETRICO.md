# Ensamble paramétrico para P-24

> Estado: **fuera de alcance**, por decisión del usuario del 2026-10-19.
> Origen: frente 5 de `docs/resultados/DIAGNOSTICO-PRECISION-E2E.md` §3.

## Por qué no entra

- **La tesis no lo necesita.** La afirmación central es comunicar el acuerdo entre simulaciones
  meteorológicas, y esa capa ya existe con GEFS (`ENSAMBLE-BACKTESTS-CONSOLIDADO.md`). La tesis
  declara que **no** afirma "una probabilidad calibrada de que cada píxel se queme"
  (`DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md` §2). El ensamble paramétrico existe justamente
  para medir esa calibración: cobertura y relación spread-skill.
- **No ataca el error dominante.** Lo que decide el Dice es la forma: el crecimiento predicho es
  casi isótropo y está mal orientado. El diagnóstico lo dejó como límite estructural: no es abrigo
  bajo dosel (nota I), no es la reconstrucción de la semilla (U) y no es el viento de WRF (W). Un
  ensamble alrededor de ese crecimiento sólo ensancharía la banda.
- **Es caro.** Hay que escribir código para perturbar los miembros por receta, y son unas 460
  corridas, una por vez en la VM (del orden de 12 h).

## Qué queda en la tesis en su lugar

La sub-dispersión de GEFS se declara como limitación de la capa de acuerdo. La dispersión de
entrada entre miembros es de 3–11° en dirección y de 7–15 % en rapidez, contra un desvío del GFS
frente a estaciones de −14° a +30° (S5 y W). Un acuerdo alto entre miembros no quiere decir, por
lo tanto, que el perímetro sea cierto.

## Diseño conservado (por si se reabre)

- **Miembros.** 20, con σ fijados de antemano desde lo medido, sin ajuste:
  - ln ADJ ~ N(0; 0,4) (Cruz y Alexander 2013);
  - WD ±25° (el desvío contra estaciones);
  - m1 ±1 punto.

  El ADJ va por miembro en la receta, porque el Monte Carlo de ELMFIRE 2025.0212 sólo aplica
  deltas aditivos globales (`docs/referencias/ELMFIRE-COMO-FUNCIONA.md` §8).
- **Criterios.**
  - Cobertura P10–P90 del crecimiento observado ≥ 0,8, por separado en los reinicios con sesgo < 1
    y con sesgo > 1.
  - Spearman entre el ancho de la banda y \|ln sesgo\| ≥ 0,3.
  - Comparación contra GEFS en los mismos 23 reinicios.
- **Alcance.** No toca modelo-v0.
