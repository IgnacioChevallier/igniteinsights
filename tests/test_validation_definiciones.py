"""Las reglas que hacen confiable al benchmark: fuga temporal, inmutabilidad, peras con peras."""
import json
from datetime import datetime

import pytest

from app.validation import almacen
from app.validation import definiciones as d


def _caso(anio=2023, contiguo=True):
    t = datetime.fromisoformat
    ventanas = [d.Ventana(t("2023-02-04T18:00:00+00:00"), 24),
                d.Ventana(t("2023-02-05T18:00:00+00:00" if contiguo
                            else "2023-02-07T18:00:00+00:00"), 24)]
    return d.Caso("los-alerces-2023", "cadena", anio, ventanas, {})


def _receta(**kw):
    base = dict(id="r", padre=None, motivo="m",
                combustible={"fuente": "ccsbap", "anio": "anterior_al_fuego"},
                semilla="prediccion")
    return d.Receta(**(base | kw))


def test_fuga_temporal_rechazada():
    r = _receta(combustible={"fuente": "mapbiomas", "anio": 2024})
    with pytest.raises(ValueError, match="fuga temporal"):
        r.validar(_caso())


def test_anterior_al_fuego_resuelve_por_incendio():
    r = _receta(combustible={"fuente": "mapbiomas", "anio": "anterior_al_fuego"})
    assert r.anio_combustible(_caso(2023)) == 2022
    assert r.anio_combustible(_caso(2026)) == 2024
    assert _receta().anio_combustible(_caso(2023)) == 2017


def test_sin_anterior_la_fuga_se_declara():
    combustible = {"fuente": "worldcover", "anio": "anterior_al_fuego"}
    with pytest.raises(ValueError, match="ningún año"):
        _receta(combustible=combustible).anio_combustible(_caso(2016))
    r = _receta(combustible=combustible | {"sin_anterior": "primero_publicado"})
    assert r.anio_combustible(_caso(2016)) == 2020
    assert r.factores(_caso(2016))["fuga_temporal"] is True
    assert r.anio_combustible(_caso(2023)) == 2021
    assert "fuga_temporal" not in r.factores(_caso(2023))
    ultimo = _receta(combustible=combustible | {"sin_anterior": "ultimo_publicado"})
    assert ultimo.anio_combustible(_caso(2016)) == 2021
    assert ultimo.anio_combustible(_caso(2021)) == 2020


def test_prediccion_exige_ventanas_contiguas():
    with pytest.raises(ValueError, match="contiguas"):
        _receta().validar(_caso(contiguo=False))
    _receta(semilla="observacion").validar(_caso(contiguo=False))


def test_perillas_inventadas_rechazadas():
    with pytest.raises(ValueError, match="perillas"):
        _receta(parametros={"FOLIAR_MOISTURE_CONTENT": 90}).validar(_caso())


def test_receta_editada_despues_de_correr(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "RAIZ", tmp_path)
    caso, r = _caso(), _receta()
    destino = d.ruta_iteracion(caso.id, r.id)
    destino.mkdir(parents=True)
    (destino / "manifiesto.json").write_text(json.dumps({"receta_sha": r.sha()}))
    d.exigir_receta_intacta(r, caso)
    r.parametros = {"lw_moisture_pct": 90}
    with pytest.raises(ValueError, match="receta nueva"):
        d.exigir_receta_intacta(r, caso)


def _manifiesto(caso="c", receta="r", factores=None, insumos=None, namelist="n"):
    return {"caso": caso, "receta": receta, "caso_sha": "x", "git": {"sha": "g"},
            "factores": factores or {"combustible": "ccsbap2017"},
            "ventanas": [{"n": 0, "insumos": insumos or {"fbfm40.tif": "a", "ws.tif": "w"},
                          "namelist_sha": namelist}]}


def test_comparar_rechaza_peras_con_manzanas():
    with pytest.raises(ValueError, match="peras|sólo se comparan"):
        d.comparar(_manifiesto("c1", "r1"), _manifiesto("c2", "r2"))


def test_comparar_separa_declarado_de_no_declarado():
    a = _manifiesto(receta="r1")
    b = _manifiesto(receta="r2", factores={"combustible": "worldcover2021"},
                    insumos={"fbfm40.tif": "b", "ws.tif": "OTRO"})
    diff = d.comparar(a, b)
    assert diff["declarados"] == {"combustible": ("ccsbap2017", "worldcover2021")}
    assert diff["no_declarados"] == [{"ventana": 0, "insumo": "ws.tif"}]


def test_almacen_guarda_inmutable_y_materializa(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "RAIZ", tmp_path / "objetos")
    origen = tmp_path / "phi.tif"
    origen.write_bytes(b"datos")
    sha = almacen.guardar(origen)
    origen.write_bytes(b"pisado")          # re-escribir el original no toca el objeto
    assert almacen.abrir(sha).read_bytes() == b"datos"
    almacen.materializar({"phi.tif": sha}, tmp_path / "trabajo")
    assert (tmp_path / "trabajo" / "phi.tif").read_bytes() == b"datos"
    with pytest.raises(PermissionError):
        (tmp_path / "trabajo" / "phi.tif").write_bytes(b"x")


def test_reescribir_no_toca_el_objeto_del_almacen(tmp_path, monkeypatch):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    from app.validation import cadena

    monkeypatch.setattr(almacen, "RAIZ", tmp_path / "objetos")
    origen = tmp_path / "ws.tif"
    with rasterio.open(origen, "w", driver="GTiff", height=2, width=2, count=2, dtype="float32",
                       crs="EPSG:32719", transform=from_origin(0, 0, 30, 30)) as dst:
        dst.write(np.full((2, 2, 2), 10.0, dtype="float32"))
    sha = almacen.guardar(origen)
    almacen.materializar({"ws.tif": sha}, tmp_path / "trabajo")
    cadena._reescribir(tmp_path / "trabajo" / "ws.tif", lambda a: a * 1.5)
    with rasterio.open(tmp_path / "trabajo" / "ws.tif") as src:
        assert src.count == 2 and float(src.read().max()) == 15.0
    assert almacen.sha256(almacen.abrir(sha)) == sha


def test_modelo_de_humedad_desconocido_rechazado():
    with pytest.raises(ValueError, match="modelo de humedad"):
        _receta(parametros={"modelo_humedad": "magia"}).validar(_caso())
    _receta(parametros={"modelo_humedad": "fosberg", "humedad_m1_delta": -2,
                        "adj_grupos": {"SH": 1.3}}).validar(_caso())
