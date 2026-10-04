# Modelo v0

> Estado: **aprobado internamente para producción** el 2026-10-04. Snapshot ejecutable:
> `benchmarks/modelos/modelo-v0.json`.

## Identidad

`modelo-v0` es la promoción de la receta `lw-100-001` sobre la partición v6. No es una receta
nueva y no duplica corridas. El snapshot fija:

- SHA de la receta;
- once casos y sus paquetes por SHA;
- partición calibración/prueba;
- resultados del gate;
- commit de código del cierre físico;
- limitaciones y regla de reapertura.

Validación local:

```bash
uv run python scripts/benchmark.py modelo modelo-v0
```

## Gate

| Criterio | Resultado |
|---|---|
| Interfaz física | Cinco hallazgos de ELMFIRE y orientación del terreno corregidos |
| Inmutabilidad | Receta, casos, manifiestos y métricas referenciados por SHA-256 |
| Calibración | 0,439 de media, 0,501 de mediana; sin alarmas salvo el caso límite |
| Validación cruzada | 0,416 de media y 0,496 de mediana fuera de muestra |
| Prueba | 0,191/0,167 y dos alarmas; informativo, no usado para ajustar |
| Robustez a la ignición | 0,461/0,497 sobre 21 perturbaciones |
| Reproducción ejecutable | GFS 4/4 y ERA5 3/3 ventanas iguales byte a byte |
| Regla de parada | Sólo bug físico o evidencia externa nueva |

La verificación ejecutable del 2026-10-04 reprodujo
`epuyen-2025/calibracion-v6` (GFS) y
`los-alerces-2016/calibracion-era5-v6` (ERA5) con la receta congelada. Todas las ventanas
coincidieron con sus artefactos registrados.

## Contrato productivo

El nombre `modelo-v0` puede usarse en configuración, documentación y despliegue para seleccionar
este snapshot. Internamente, la ejecución sigue resolviendo la receta `lw-100-001` y los builders
vigentes. Promover un futuro `modelo-v1` exigirá:

1. una receta nueva o una modificación explícita de insumos;
2. casos y paquetes congelados;
3. banco físico aprobado;
4. métricas de calibración, validación cruzada y prueba;
5. comparación contra modelo-v0;
6. una justificación que no use el holdout para elegir parámetros.

## Límites de uso

Modelo-v0 no promete reproducir supresión, igniciones secundarias ni ráfagas subhorarias. El
conjunto de prueba es pequeño y heterogéneo. La promoción significa “baseline productivo,
auditable y físicamente verificado”, no “modelo universalmente validado”.
