# Diagnóstico de precisión

Fecha de cierre: 2026-10-31.

## Pregunta

¿Por qué la predicción no alcanza mayor superposición espacial con los incendios observados?

## Respuesta

El error dominante es de **forma y dirección**, no sólo de área. En P-24, igualar el área
predicha con la observada casi no modifica el Dice: el crecimiento rodea la semilla con una
elongación cercana a 1,5, mientras el observado alcanza 2,9–3,2, y el rumbo difiere unos 60°.

## Evidencia resumida

| Componente | Resultado | Lectura |
|---|---|---|
| Área/velocidad | error de área cercano a ×4 en P-24 | importante, pero no explica por sí solo el Dice |
| Forma | Dice a área igualada cambia aproximadamente −0,01 | ajustar velocidad no corrige la geometría |
| Rumbo | error mediano 58–67° | el viento regional no representa bien valles y laderas |
| Referencia | techo aproximado 0,7–0,9; corregir islas cambia 0,439→0,440 | no explica la brecha principal |
| Combustible | es la palanca medida más grande en calibración | CCS-BAP mejora frente a WorldCover; MapBiomas sigue competitivo |
| GEFS | dispersión menor que el error del GFS contra estaciones | el ensamble meteorológico está subdispersado |
| Semilla | el filtro conexo corrige Cholila; la mediana casi no cambia | no es la causa general |

## Decisiones cerradas

- P-24 se puntúa sin el anillo ya observado alrededor de la semilla.
- Se mantiene la reconstrucción del perímetro FIRMS y se filtran detecciones desconectadas.
- No se incorpora SMN WRF: la comparación contra estaciones no mostró una mejora consistente.
- No se abre una receta por copa, `CROWN_RATIO`, humedad por especie o ajuste secuencial de
  velocidad con la evidencia disponible.
- El ensamble paramétrico queda fuera del alcance.

## Consecuencia

P-24 mejora consistentemente frente a continuar la cadena, pero el nivel absoluto de acierto
sigue siendo modesto y la ventaja frente a persistencia cae en prueba. El producto debe mostrar
escenarios potenciales y límites, no presentar un perímetro como exacto.

## Trazabilidad

Los cálculos, revisiones y datos intermedios están en `benchmarks/diagnosticos/e2e/`. Los scripts
`diagnostico_*.py` reproducen cada frente evaluado.

