# Plan: ensamble local, Railway liviano

## Objetivo

Railway sólo corre el P-24 del cron y guarda lo que el mapa dibuja. El ensamble GEFS (31
miembros, ~35 min y ~1,7 GB por corrida) se corre a mano en la computadora local y se sube
sólo su producto (`ensemble_agreement.json`) al pronóstico vivo. El volumen de Railway pasa de
37 GB a pocos GB y deja de crecer.

## Lo que ya está (2026-11-07, en main)

- Cron `*/30 5-10,18-23 * * *` UTC; un pronóstico por racimo de pasadas (`RACIMO_H`).
- Sleep en api y runner, con latido a `/health` durante `/simulate`.
- `podar`: al terminar un pronóstico borra `ensamble/` y los insumos salvo `wind-field.json` e
  `ignicion.*`.

## Hechos que fijan el diseño

- El mapa sólo lee `ensemble_agreement.json` de `output_dir`
  (`GET /simulations/{id}/ensemble-agreement`); `/operativo/estado` marca `ensamble: true`
  si ese archivo existe (`servicio.py`). Subir el archivo **es** registrarlo.
- Hoy la capa sólo se ve si `operativo.calcular_ensamble` está prendido
  (`client-map.tsx:394`): apagar el cálculo en Railway la escondería.
- `correr_ensamble` necesita los insumos congelados del pronóstico: estáticos recortados a la
  caja (reproducibles en local: `data/operativo/estaticos/2026/` existe), la tabla de
  combustibles y la semilla `phi.tif` (sale de las detecciones de la base de Railway: hay que
  traerla). Más metadatos: `pasada`, `ciclo_gfs`, `caja`, `t0`, `tstart_s`.
- La api no tiene dominio público. `railway ssh config` deja un host OpenSSH: `scp` sube y
  baja archivos y `ssh host 'uv run python scripts/…'` corre scripts allá. Sin endpoint nuevo.
- Ya hubo ensambles de la demo de Puerto Patriada corridos en local
  (`scripts/demo_ensamble.py`): sirven de referencia para validar la ruta local.

## Grafo de dependencias

```
T1 cron sin ensamble + capa por archivo ──┐
T2 podar conserva phi.tif ──┬─────────────┼─> CHECKPOINT A (Railway liviano)
T3 limpieza única ──────────┘             │
                                          v
T4 exportar paquete desde Railway ──> T5 correr local ──> T6 subir y registrar ──> T7 skill
                                                                     └──> CHECKPOINT B (punta a punta)
```

T1, T2 y T3 son independientes entre sí; T3 va después de T2 para no borrar `phi.tif`.

## Fase 1: Railway liviano

**T1. El cron nunca corre el ensamble; la capa se ve si el archivo existe.**
Sacar la rama `calcular_ensamble` de `servicio._correr` (`correr_ensamble` queda para uso
local). En el frontend, la capa depende de `pronostico.ensamble` y no de `calcular_ensamble`;
el toggle del admin en `producto-panel.tsx` se va (o pasa a "mostrar", ver preguntas).
- Acepta: un tick no llama a `correr_ensamble` aunque el flag esté prendido; un pronóstico
  con `ensemble_agreement.json` muestra la capa con el flag apagado.
- Verifica: pytest de `tick`/`_correr` con `correr_ensamble` parcheado para fallar; playwright
  con el stub (`frontend/e2e/stub-api.mjs`) devolviendo `ensamble: true` y flag apagado.

**T2. `podar` conserva `phi.tif`.** Es la semilla (unos MB), lo único del congelado que no se
puede rehacer sin la base de Railway.
- Acepta/verifica: `test_podar_deja_solo_lo_que_el_mapa_vuelve_a_leer` incluye `phi.tif`.

**T3. Limpieza única del volumen.** `scripts/podar_volumen.py --dry-run|--aplicar`, corrido
en Railway por ssh: para cada pronóstico aplica `podar`; borra `ensamble/` de toda salida
(incluida la demo; su `ensemble_agreement.json` queda); borra las 6 carpetas de insumos de
simulaciones de AOI completo (~29 GB) según la respuesta a la pregunta 1.
- Acepta: `--dry-run` lista qué borra y cuánto; tras `--aplicar`, `du /app/data` < ~6 GB.
- Verifica: test del criterio de borrado sobre un árbol en `tmp_path`; en Railway, el
  dashboard sigue mostrando pronósticos vivos y demo, viento, isócronas y el ensamble de
  Patriada.

### CHECKPOINT A
`make check` verde; deploy sano (`environment-status`); volumen medido; el dashboard revisado
a mano en modo demo y vivo. Revisión humana antes de la fase 2.

## Fase 2: ensamble local

**T4. Exportar el paquete de un pronóstico.** `scripts/ensamble_exportar.py [--id ID]`
(por defecto el último pronóstico vivo `listo`) imprime JSON: `id`, `simulacion_id`, `nombre`,
`pasada`, `ciclo_gfs`, `caja`, `t0`, `tstart_s`, ruta de `phi.tif` y `output_dir`.
- Acepta: con `--id` de la demo también funciona; sin pronósticos vivos sale con un mensaje
  claro y código ≠ 0.
- Verifica: test de la función pura que arma el JSON desde un `Pronostico`.

**T5. Correr el ensamble en local.** `scripts/ensamble_local.py paquete.json phi.tif`:
recorta los estáticos locales a la caja (reusa `_recortar`, `ESTATICOS`, la tabla de
combustibles), pone `phi.tif`, llama a `correr_ensamble` contra el runner local y deja
`ensemble_agreement.json` en `data/ensamble-local/<id>/`. Reanudable; uno por vez (el runner
aguanta una corrida).
- Acepta: sobre un pronóstico demo de Patriada reproduce el `ensemble_agreement.json` que ya
  existe (mismo acuerdo celda a celda, salvo miembros GEFS caídos).
- Verifica: esa comparación, documentada en la salida del script.

**T6. Subir y registrar.** `scp` del JSON a `outputs/operativo-<id>/` y
`scripts/ensamble_registrar.py <id>` en Railway: valida el contrato (`layer.id ==
"ensemble_agreement"`, miembros ≥ mínimo) y escribe el manifiesto en
`simulation_runs.elmfire_config["ensamble"]`.
- Acepta: `/operativo/estado` da `ensamble: true` para ese pronóstico y la capa se dibuja.
- Verifica: test del validador; en Railway, la capa en el dashboard.

**T7. Skill `.claude/skills/ensamble-local/`.** Los pasos de punta a punta: `railway ssh
config`, exportar, bajar `phi.tif`, `make dev-simulation`, correr, subir, registrar,
verificar. Incluye: un ELMFIRE por vez (VM de 7,75 GB), ~35 min por corrida, y que el ciclo
GEFS viejo (> 4 días) sale del archivo histórico.
- Acepta: alguien sin contexto la sigue y sube un ensamble.

### CHECKPOINT B
Un ensamble real corrido en local y visible sobre el último pronóstico vivo (o uno demo si no
hay incendios activos). Actualizar `docs/dashboard-producto.md` (§ ensamble y deploy).

## Riesgos

- **Estáticos locales distintos de los de Railway** (otra fuente de combustibles, otro año):
  el ensamble saldría de otra grilla. Mitigación: T5 compara el perfil (CRS, transform,
  tamaño) de lo recortado con el de `phi.tif` y aborta si difieren.
- **Fuera de temporada no hay pronósticos vivos:** T4 acepta `--id` para la demo.
- **`podar` ya corrió sobre pronósticos sin `phi.tif`** (desde hoy hasta T2): esos no se pueden
  ensamblar en local. Hoy no hay incendios activos, así que el costo es nulo si T2 sale pronto.

## Preguntas abiertas

1. Las 6 carpetas de insumos de AOI completo (~29 GB, 2026-09-28 a 11-01): ¿se borran sin
   mirar, o primero se chequea si el dashboard todavía muestra esas simulaciones (su capa de
   viento lee `ws.tif`/`wd.tif` de ahí)?
2. El toggle del admin "calcular ensamble": ¿se elimina (la capa aparece cuando hay ensamble)
   o queda como "mostrar ensamble"?
