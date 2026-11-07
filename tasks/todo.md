# Todo: ensamble local, Railway liviano

Plan: `tasks/plan.md`.

## Fase 1: Railway liviano
- [ ] T1 El cron nunca corre el ensamble; la capa se ve si existe `ensemble_agreement.json`
- [ ] T2 `podar` conserva `phi.tif`
- [ ] T3 `scripts/podar_volumen.py` (dry-run → aplicar en Railway)
- [ ] CHECKPOINT A: make check, deploy sano, volumen medido, dashboard revisado

## Fase 2: ensamble local
- [ ] T4 `scripts/ensamble_exportar.py` (último vivo listo o `--id`)
- [ ] T5 `scripts/ensamble_local.py` (valida contra el ensamble demo de Patriada)
- [ ] T6 subir con scp + `scripts/ensamble_registrar.py`
- [ ] T7 skill `.claude/skills/ensamble-local/`
- [ ] CHECKPOINT B: ensamble real visible en Railway; actualizar `docs/dashboard-producto.md`

## Preguntas abiertas
- [ ] ¿Borrar las 6 carpetas de AOI completo (~29 GB) sin chequear la base?
- [ ] ¿Toggle del admin: eliminar o "mostrar ensamble"?
