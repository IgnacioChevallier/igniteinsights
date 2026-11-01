# Resultados y estado vigente

Índice de `docs/resultados/`. El informe de tesis (`../informe`) toma de acá sus fuentes: la
sección 1 es lo que puede citarse como resultado vigente; la 2, el respaldo de esas cifras; la 3,
antecedentes que no describen el estado actual. Ante cualquier diferencia, manda
`ESTADO-RESEARCH.md`.

## 1. Para el informe

**Estado y modelo**

- `ESTADO-RESEARCH.md`: fuente canónica del estado, los límites declarados y lo pendiente.
- `MODELO-V0.md`: snapshot promovido, resultados por caso y contrato del gate productivo.
- `METRICAS.md`: catálogo de las métricas (qué mide cada una, qué aporta, qué no dice y su valor
  vigente), incluidos P-24 y el acuerdo del ensamble.
- `PENDING_PARAMETERS.md`: qué quedó congelado en modelo-v0 y qué se declaró como límite. Desde el
  2026-10-31 no queda nada abierto.
- `RIESGOS_Y_SUPOSICIONES.md`: qué supone modelo-v0, cómo afecta a los resultados y qué dato lo
  reduciría.
- `HISTORIA-BUSQUEDA.md`: cómo se llegó a modelo-v0, loop por loop, con las recetas y las cifras de
  calibración.

**Mapas de combustible** (la contribución de la tesis; las decisiones del crosswalk están en
`docs/crosswalk/`)

- `COMPARACION-MAPAS-MODELO-V0.md`: protocolo de la comparación final, congelado antes de correr.
- `COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`: tablas y conclusión de la comparación final.

**Pronóstico operativo y día 1**

- `DIA-1-PROPUESTA.md`: el déficit del día 1, el protocolo P-24 (pronóstico desde el perímetro
  observado) y el diagnóstico de copa con CFIS (§7).
- `P24-PRONOSTICO-GFS.md`: P-24 con el pronóstico GFS que se tenía en cada reinicio, como lo usa el
  dashboard.
- `DIAGNOSTICO-PRECISION-E2E.md`: diagnóstico de la precisión de modelo-v0 sin reabrirlo; su
  encabezado indexa las notas de trabajo.
- `LO-YA-QUEMADO-PROPUESTA.md`: reasignación del combustible ya quemado y la ingesta histórica de
  FIRMS en la app.

**Producto**

- `docs/dashboard-producto.md`: el dashboard como producto (roles, reloj de demostración, camino
  único del pronóstico, despliegue). En inglés, como el resto de la documentación de la app.

**Incertidumbre y ensamble**

- `DECISIONES-TESIS-TRANSPARENCIA-INCERTIDUMBRE.md`: afirmación central de la tesis, alcance
  operacional y semántica del acuerdo del ensamble.
- `ENSAMBLE-METEOROLOGICO-POC.md`: método del ensamble meteorológico GEFS.
- `ENSAMBLE-BACKTESTS-CONSOLIDADO.md`: los 23 backtests contemporáneos, consolidados.
- `PROTOCOLO-EVALUACION-ACUERDO-ENSAMBLE.md`: protocolo de la evaluación con usuarios, pendiente.

## 2. Respaldo de las cifras

- `AUDITORIA-FISICA.md`: bitácora física completa (hallazgos de interfaz y loops A–M).
- `IGN-26-VALIDACION.md`: diseño y evolución del benchmark.
- `HUMEDAD-ALTURA-PROPUESTA.md`: humedad y altura en la lenga, cerrado como límite; lo resumen
  `RIESGOS_Y_SUPOSICIONES.md` §4 y el crosswalk (§5.5).
- `diagnostico-e2e/notas/`: notas de trabajo A–AE, cada una con su diseño y sus fuentes. Las
  indexan `DIAGNOSTICO-PRECISION-E2E.md` y `ESTADO-RESEARCH.md`; los datos que producen están en
  `diagnostico-e2e/datos/`.

## 3. Antecedentes

- `COMPARACION-MAPAS-V5.md`: comparación de mapas sobre el benchmark v5, superada por la de
  modelo-v0.
- `docs/historico/`: planes, propuestas y resultados superados. `docs/out-of-scope/`: lo que se
  decidió dejar fuera. Ninguno describe el estado actual.
