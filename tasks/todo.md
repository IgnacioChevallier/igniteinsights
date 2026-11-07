# Todo: ensamble local, Railway liviano

Plan: `tasks/plan.md`.

## Fase 1: Railway liviano
- [x] T1 El cron nunca corre el ensamble; la capa se ve si existe `ensemble_agreement.json`
- [x] T2 `podar` conserva `phi.tif`
- [x] T3 `scripts/podar_volumen.py` (dry-run → aplicar en Railway): 34 GB → 0,7 GB (2026-11-07)
- [x] CHECKPOINT A: deploy sano, volumen medido; /estado, isócronas, ToA, ignición, viento y
      ensamble de Patriada responden. La poda rompía el viento (el endpoint pedía ws/wd): arreglado.

## Fase 2: ensamble local
- [x] T4 `scripts/ensamble_exportar.py` (último vivo listo o `--id`; los insumos congelados van en
      el JSON: con los estáticos locales, viejos, Patriada quemaba ~450 ha de más)
- [x] T5 `scripts/ensamble_local.py`: reproduce el ensamble demo de Patriada (31/31 miembros,
      19 min; diferencia simétrica 0,0 / 0,4 / 0,0 ha en ≥0,1 / 0,5 / 0,8)
- [x] T6 `scripts/ensamble_registrar.py` (contrato por stdin; rechazo probado en Railway)
- [x] T7 skill `.claude/skills/ensamble-local/`
- [x] CHECKPOINT B: Patriada 05-01 19:20 registrado desde local el 2026-11-07; `/operativo/estado`
      da `ensamble: true` y el endpoint sirve el contrato nuevo. Sin incendios vivos: se usó la demo.

## Preguntas cerradas
- [x] Carpetas de AOI completo: borradas las 5 sin referencia y también 29a699db.
- [x] Toggle del admin: queda como "visible para clientes".
