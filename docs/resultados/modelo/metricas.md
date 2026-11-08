# Métricas de evaluación

## Métricas espaciales

Sea `P` el crecimiento predicho y `O` el observado, sin incluir la semilla:

- **Dice:** `2·|P∩O| / (|P|+|O|)`. Métrica principal; 1 es superposición perfecta.
- **IoU:** `|P∩O| / |P∪O|`.
- **Recall:** proporción del área observada alcanzada por el modelo.
- **Precisión:** proporción del área predicha que coincide con la referencia.
- **Sesgo de área:** `|P| / |O|`; se declara alarma fuera de `[0,5; 2]`.

Dice e IoU siempre se leen junto al sesgo: una geometría enorme puede alcanzar gran parte de la
referencia y aun así ser inútil.

## Tiempo y forma

- **t\*:** hora en que la simulación alcanza el área observada.
- **Dice a área igualada:** superposición al cortar la simulación en t\*; separa forma de
  velocidad.
- **Error de llegada:** diferencia temporal respecto de detecciones FIRMS.
- **Elongación y rumbo:** describen si el crecimiento tiene la forma y dirección observadas.

## Agregación

La unidad de análisis es el incendio. Las ventanas o reinicios del mismo evento están
correlacionados y se agregan antes de comparar incendios. Se informan media y mediana; con muestras
pequeñas no se interpreta la ausencia de significación como equivalencia.

## Aplicación por experimento

| Pregunta | Métrica principal | Comparador |
|---|---|---|
| Modelo completo | Dice final + sesgo | referencia dNBR truncada al horizonte |
| P-24 | Dice del crecimiento a 12/24 h | cadena y persistencia |
| Mapas de combustible | Dice final y forma | CCS-BAP, MapBiomas y WorldCover con todo lo demás fijo |
| Ensamble GEFS | ΔIoU, recall, área y falsos positivos | miembro `c00` |
| Áreas quemadas | no regresión en Dice y alarmas | `modelo-v0` |

Los valores vigentes se publican en los documentos de resultados, no se duplican aquí.

## Implementación

- Puntuación base: `app/validation/puntuacion.py`.
- P-24: `app/validation/pronostico.py`.
- CLI y agregación: `scripts/benchmark.py`.
- Pruebas: `tests/test_validation_metricas.py` y `tests/test_validation_pronostico.py`.

