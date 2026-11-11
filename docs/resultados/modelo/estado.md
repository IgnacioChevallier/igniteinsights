# Estado de la investigación

Fecha de cierre: 2026-11-01.

## Estado

La investigación de este repositorio está cerrada. `modelo-v0` es la receta promovida y P-24 es
el protocolo operativo de pronóstico desde la última observación VIIRS. No quedan decisiones de
calibración abiertas.

## Decisiones vigentes

| Tema | Decisión | Evidencia |
|---|---|---|
| Modelo | `lw-100-001` promovida como `modelo-v0` | [modelo](modelo.md) |
| Validación | banco de pruebas inmutable, prueba no usada para ajustar | [validación](validacion.md) |
| Combustible | CCS-BAP; MapBiomas queda como comparador competitivo | [comparación](../combustibles/resultados.md) |
| Combustibles | tabla CCS-BAP → FBFM40 vigente | [correspondencia](../../crosswalk.md) |
| Pronóstico | reiniciar en cada pasada VIIRS con P-24 | [P-24](../pronostico/p24.md) |
| Meteorología | usar el último GFS disponible al reinicio | [P-24](../pronostico/p24.md) |
| Incertidumbre | mostrar acuerdo GEFS, no probabilidad | [ensamble](../ensamble.md) |
| Áreas quemadas | aplicar la regla LYQ-3 en preparaciones nuevas | [áreas quemadas](../pronostico/areas-quemadas.md) |

## Resultados principales

- `modelo-v0`: Dice 0,439/0,501 en calibración y 0,191/0,167 en prueba.
- P-24 con pronóstico GFS disponible: mejora a la cadena en 4/4 incendios a 12 h (+0,117) y en
  3/4 a 24 h (+0,153).
- CCS-BAP: 0,415 de Dice medio en los seis casos sin fuga temporal, frente a 0,378 de MapBiomas y
  0,118 de WorldCover.
- Ensamble GEFS: técnicamente reproducible y útil para comunicar sensibilidad, sin mejora
  predictiva consistente frente a `c00`.
- LYQ-3: incorpora quemas posteriores al mapa sin regresión agregada.

## Interpretación

La salida representa propagación potencial bajo las condiciones modeladas y sin acciones de
combate. No es una predicción de la cicatriz final ni una probabilidad calibrada por píxel. Los
límites vigentes están resumidos en [`limites.md`](limites.md).

## Fuentes canónicas

- Configuración promovida: `benchmarks/modelos/modelo-v0.json`.
- Evidencia reproducible: `benchmarks/casos/`, `benchmarks/recetas/` y
  `benchmarks/iteraciones/`.
- Diagnósticos y tablas derivadas: `benchmarks/diagnosticos/`.

