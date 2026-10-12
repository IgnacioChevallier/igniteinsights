# Estado del research

> Fuente canónica desde el 2026-10-04. Reemplaza las secciones de “estado actual” y “próximos
> pasos” dispersas en documentos anteriores. La bitácora física completa permanece en
> `docs/resultados/AUDITORIA-FISICA.md`.

## 1. Estado

La fase de ajuste de receta está **cerrada**. La receta `lw-100-001` sobre los protocolos v6 fue
promovida a **`modelo-v0`**, el primer snapshot que pasa el gate productivo. Su identidad
inmutable está en `benchmarks/modelos/modelo-v0.json`.

Convención:

- **receta:** configuración experimental que puede aplicarse a distintos casos;
- **iteración:** receta × caso, con manifiesto, insumos y salidas por hash;
- **modelo:** receta, casos, resultados y criterios congelados después de pasar un gate.

Promover una receta no cambia ni renombra sus iteraciones históricas. `modelo-v0` referencia
`lw-100-001`; no existe una “receta modelo-v0”.

## 2. Configuración de modelo-v0

- ELMFIRE 2025.0212.
- Protocolos v6.
- CCS-BAP del último año anterior al incendio.
- Humedad viva leñosa (LW): 100 %.
- ADJ: 1,0.
- Estepa → GR2; vegetación altoandina sobre 1.300 m → NB9.
- Remanente de disturbio reciente → SH3.
- CBH por tipo de bosque y CBD de pino de 0,16 kg/m³.
- Sin dosel donde Hansen registra pérdida anterior al incendio.
- Alerces 2023 puntuado a 54 h, cuando el área FIRMS deja de crecer.

## 3. Evidencia congelada

La partición tiene siete incendios de calibración y cuatro de prueba. Las Golondrinas se conserva
en las tablas, pero es un caso límite meteorológico y no participa de la restricción de sesgo.

| Conjunto | n | Dice medio | Mediana | Alarmas |
|---|---:|---:|---:|---:|
| Calibración | 7 | 0,439 | 0,501 | 0 sin el caso límite |
| Validación cruzada | 7 | 0,416 | 0,496 | — |
| Prueba | 4 | 0,191 | 0,167 | 2 |
| Robustez de ignición | 21 | 0,461 | 0,497 | 2 |

La reproducción ejecutable del cierre comparó byte a byte un caso GFS (4/4 ventanas iguales)
y uno ERA5 (3/3 ventanas iguales) contra sus artefactos congelados.

La validación cruzada vigente fue regenerada el 2026-10-04 con las cinco recetas que tienen
iteraciones completas sobre los siete casos v6. Reemplaza el valor 0,437/0,490 que había quedado
escrito durante el loop M con otro conjunto de recetas completas.

El resultado de prueba es deliberadamente descriptivo: no se usa para volver a elegir LW, ADJ,
crosswalk, CBH ni viento.

## 4. Qué quedó demostrado

1. La interfaz original con ELMFIRE tenía errores materiales; los cinco hallazgos de la auditoría,
   la orientación del terreno y los problemas de preparación asociados están corregidos y
   cubiertos por pruebas físicas.
2. Con la interfaz correcta no hace falta un ajuste global de velocidad: ADJ queda en 1.
3. LW 100 % es la única perilla regional adoptada.
4. El crosswalk y el dosel v6 mejoran la calibración y reducen las alarmas, aunque no resuelven
   la transferencia a todos los regímenes de incendio.
5. La comparación controlada v5 muestra que CCS-BAP supera a WorldCover en los incendios sin
   fuga temporal y empata globalmente con MapBiomas. Esa comparación todavía no usa el crosswalk
   final de modelo-v0 y, por eso, no es el cierre definitivo de mapas.

## 5. Qué no queda pendiente como receta

- ADJ, LW, paso temporal, rugosidad, orientación, CBH/CBD y tratamiento de pérdida previa ya
  tienen una decisión.
- Pavesas, supresión, ERA5 ×1,3, dosel abierto en matorral, WindNinja completo y las alternativas
  de estepa fueron medidos y no adoptados.
- m10/m100 carece de una base física completa, pero resultó insensible en este benchmark.

No queda otro barrido justificable con los mismos datos. La regla de parada de modelo-v0 es:
**sólo se reabre por un bug físico o por evidencia externa nueva**, no por mejorar un caso de
prueba.

## 6. Límites y trabajo futuro

- Día 1 explosivo: ráfagas subhorarias, copa o pavesas no representadas.
- Supresión: El Turbio y Epuyén 2019 no son reproducidos por el módulo disponible.
- Viento de superficie: una estación cercana a Alerces 2016 o Cholila permitiría contrastar
  ERA5 con WindNinja.
- Las Golondrinas: evento meteorológico ausente en GFS.
- Ingesta histórica de la app: FIRMS NRT no sustituye las fuentes SP.

Estos puntos se reportan como límites. No bloquean la comparación de mapas condicionada a
modelo-v0.

## 7. Comparación final de mapas

La comparación predefinida en `docs/resultados/COMPARACION-MAPAS-MODELO-V0.md` fue ejecutada
sobre los once casos. Los controles CCS-BAP reprodujeron modelo-v0 byte a byte.

- Sin fuga temporal (6 incendios): Dice 0,415 CCS-BAP, 0,118 WorldCover y 0,378 MapBiomas.
- Calibración sin el límite: 0,510 CCS-BAP, 0,131 WorldCover y 0,430 MapBiomas.
- Prueba: 0,191 CCS-BAP, 0,272 WorldCover y 0,284 MapBiomas.

WorldCover queda descartado como fuente principal. CCS-BAP permanece en modelo-v0; MapBiomas es
competitivo y no hay evidencia para afirmar superioridad general de CCS-BAP sobre él, pero sí
no inferioridad: con 95 % de confianza (Hodges-Lehmann, cota exacta de Wilcoxon), CCS-BAP no
pierde más de 0,098 de Dice en los seis casos sin fuga, dentro de un margen de 0,130 (la mitad
de la ventaja de MapBiomas sobre WorldCover, fijado después de ver los datos). El holdout
no se usa retrospectivamente para cambiar el modelo. Resultado completo:
`docs/resultados/COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`.

## 8. Mapa documental

- `docs/resultados/`: estado vigente, modelo promovido, auditoría y comparaciones.
- `docs/crosswalk/`: tablas activas y decisiones de combustible/dosel.
- `docs/historico/`: planes, propuestas y resultados superados que se conservan como registro.
- raíz: documentación operativa o transversal que no pertenece a esas categorías.
