# Auditoría física de la integración con ELMFIRE

Fecha de cierre: 2026-09-30.

## Pregunta

¿La aplicación entregaba a ELMFIRE los datos, unidades y convenciones esperados por el solver?

## Hallazgos corregidos

| Hallazgo | Efecto | Corrección |
|---|---|---|
| La cantidad de bandas meteorológicas no se declaraba | ELMFIRE usaba la banda inicial durante toda la corrida | escribir `NUM_METEOROLOGY_TIMES` |
| `phi.tif` contenía distancias en metros | el frente avanzaba aproximadamente a la mitad de la velocidad calculada | generar el campo con la convención ±1 esperada |
| la dirección del viento se interpolaba como un escalar | transiciones como 350°→10° recorrían el arco largo | interpolar mediante componentes y normalizar el ángulo |
| había cobertura de dosel sin altura válida | algunas celdas quedaban prácticamente sin viento | anular cobertura cuando la altura no es válida |
| una grilla meteorológica más alta que ancha se indexaba mal | la franja norte podía leer otra fila | completar la grilla y validar cobertura/dimensiones |

Los cinco problemas fueron corregidos antes de congelar `modelo-v0`. Los resultados anteriores a
esas correcciones no se usan para elegir el modelo ni para informar desempeño vigente.

## Verificación

- El banco de pruebas físicas valida velocidad, pendiente, viento, unidades y orientación.
- GFS reprodujo 4/4 ventanas y ERA5 3/3 ventanas byte a byte desde artefactos congelados.
- Los builders validan CRS, dimensiones, cobertura, códigos de combustible y valores nodata antes
  de ejecutar ELMFIRE.
- El benchmark registra hashes de insumos, namelist, salidas, versión de código y solver.

## Consecuencias

La auditoría modificó la interfaz con ELMFIRE, no la formulación de Rothermel. Después de las
correcciones se volvieron a medir combustibles, humedad, dosel y casos históricos. Las
limitaciones que permanecen —viento regional, supresión, pavesas y transferencia— están en
[`limites.md`](limites.md).

## Trazabilidad

- Builders: `app/elmfire/builder/`.
- Pruebas físicas: `scripts/pruebas_fisicas.py` y `tests/test_elmfire_convenciones.py`.
- Preparación corregida: `scripts/preparar_benchmark.py`.
- Manifiestos: `benchmarks/iteraciones/`.
- Bitácoras experimentales: `benchmarks/diagnosticos/e2e/`.

