"""Qué borra la poda única del volumen de Railway."""
from scripts.podar_volumen import a_borrar


def test_poda_operativas_y_huerfanas_y_respeta_lo_referenciado_y_lo_que_corre(tmp_path):
    ins, sal = tmp_path / "inputs", tmp_path / "outputs"
    for d in ("operativo-a", "operativo-corriendo", "vieja-usada", "vieja-huerfana"):
        (ins / d).mkdir(parents=True)
        for f in ("ws.tif", "phi.tif", "wind-field.json"):
            (ins / d / f).write_text("x")
    for d in ("operativo-a", "operativo-corriendo"):
        (sal / d / "ensamble" / "fuentes").mkdir(parents=True)
        (sal / d / "ensemble_agreement.json").write_text("x")

    sobra = a_borrar(ins, sal, referenciadas={str(ins / "vieja-usada")}, corriendo={"corriendo"})

    assert sorted(str(p.relative_to(tmp_path)) for p in sobra) == [
        "inputs/operativo-a/ws.tif",
        "inputs/vieja-huerfana",
        "outputs/operativo-a/ensamble",
    ]
