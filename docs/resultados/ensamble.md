# Ensamble meteorológico GEFS

Fecha de corte: 2026-10-31.

## Pregunta

¿Un ensamble de meteorología GEFS aporta una representación útil de la sensibilidad del incendio
y mejora la predicción respecto del miembro de control `c00`?

## Método

Se ejecutaron los 31 miembros GEFS en 23 reinicios P-24 de cuatro incendios. Combustible, dosel,
perímetro y parámetros de `modelo-v0` permanecieron fijos; sólo cambió la meteorología.

Para cada píxel se calcula la fracción de miembros válidos que lo quemaron. Se evaluaron tres
umbrales:

- `≥ 0,10`: propagación posible dentro del ensamble;
- `≥ 0,50`: escenario central;
- `≥ 0,80`: zona de alto acuerdo.

El valor es **acuerdo entre simulaciones**, no probabilidad calibrada de quema. Los reinicios de
un mismo incendio están correlacionados, por lo que la lectura principal usa medianas por
incendio y es descriptiva.

## Resultado

### Integridad y viabilidad

- 23/23 reinicios completaron 31/31 miembros sin sustituciones ni fallos científicos.
- Todos los ciclos estaban publicados antes del reinicio VIIRS.
- Una corrida serial tarda cerca de una hora incluyendo descarga y materialización.
- El solver consume aproximadamente 430 CPU·s y alcanza 1,4 GiB de RAM por reinicio.
- La política de retención deja cerca de 1,6 GiB por caso.

La infraestructura es reproducible y viable fuera de línea. Para una latencia operativa habría
que paralelizar miembros.

### Sensibilidad meteorológica

Las bandas nunca fueron vacías ni uniformes, pero son angostas frente al error total del modelo:
la diferencia de área entre `≥ 0,10` y `≥ 0,80` equivale al 4–14 % del área de `c00`.

`≥ 0,10` mejora el recall en los cuatro incendios, pero agrega falsos positivos y todavía deja
crecimiento observado fuera de la envolvente. Por eso representa sólo la sensibilidad a la
meteorología considerada, no todos los lugares a los que puede llegar el fuego.

### Habilidad predictiva frente a `c00`

| Umbral | 12 h | 24 h | Lectura |
|---|---|---|---|
| `≥ 0,10` | IoU mejora en 0/4 | mejora en 1/4 | más recall a costa de área y precisión |
| `≥ 0,50` | mejora en 2/4 | mejora en 1/4 | prácticamente equivalente a `c00` |
| `≥ 0,80` | mejora en 2/4 | mejora en 3/4 | diferencias de IoU ≤ 0,003 |

Ninguna banda mejora de forma consistente al miembro de control.

## Decisión

Se adopta la capa **Acuerdo del ensamble** como comunicación de sensibilidad meteorológica, no
como mejora predictiva ni como probabilidad de quema. Permanece apagada por defecto.

La interfaz debe mostrar miembros válidos/esperados, ciclo, horizonte y fecha de generación. Se
exige un mínimo de 24/31 miembros y nunca se sustituyen miembros o ciclos silenciosamente.

`modelo-v0` y sus parámetros no cambian. SMN WRF se considera un escenario regional separado y
no entra en el denominador GEFS.

## Límites

- Sólo varía la meteorología; no representa incertidumbre de combustible, dosel, perímetro o
  física del modelo.
- No incluye supresión.
- Cuatro incendios no permiten generalizar la habilidad predictiva.
- La dispersión GEFS es menor que el error observado del GFS contra estaciones locales.
- La banda `≥ 0,10` no es una envolvente exhaustiva del incendio real.

## Trazabilidad

- Consolidado: `data/ensemble-poc/calibration-backtests-consolidated.{json,csv}`.
- Auditoría: `data/ensemble-poc/calibration-backtests-uniform-integrity-audit.json`.
- Ejecución: `scripts/run_ensemble_backtest_queue.py` y
  `scripts/run_ensemble_backtest_case.py`.
- Consolidación: `scripts/consolidate_ensemble_backtests.py`.
- Diagnósticos complementarios: `benchmarks/diagnosticos/e2e/`.
