# Todo: ensamble local, Railway liviano

Plan: `tasks/plan.md`.

## Fase 1: Railway liviano
- [x] T1 El cron nunca corre el ensamble; la capa se ve si existe `ensemble_agreement.json`
- [x] T2 `podar` conserva `phi.tif`
- [x] T3 `scripts/podar_volumen.py` (dry-run → aplicar en Railway): 34 GB → 0,7 GB (2026-11-07)
- [x] CHECKPOINT A: deploy sano, volumen medido; /estado, isócronas, ToA, ignición, viento y
      ensamble de Patriada responden. La poda rompía el viento (el endpoint pedía ws/wd): arreglado.

## Fase 2: ensamble local
- [x] T4 `scripts/ensamble_exportar.py` (último vivo listo o `--id`; phi.tif va en el JSON)
- [ ] T5 `scripts/ensamble_local.py`: escrito; falta correrlo contra el ensamble demo de Patriada
- [x] T6 `scripts/ensamble_registrar.py` (contrato por stdin; rechazo probado en Railway)
- [x] T7 skill `.claude/skills/ensamble-local/`
- [ ] CHECKPOINT B: ensamble real visible en Railway (`docs/dashboard-producto.md` ya actualizado)

## Preguntas cerradas
- [x] Carpetas de AOI completo: borradas las 5 sin referencia y también 29a699db.
- [x] Toggle del admin: queda como "visible para clientes".
