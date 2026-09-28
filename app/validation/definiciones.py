"""Caso, receta e iteración: qué se corre, con qué modelo, y qué cambió entre dos corridas.

- **Caso** `benchmarks/casos/<incendio>/<protocolo>.json`: un incendio con un protocolo
  (semilla inicial, ventanas, referencias). Su paquete congelado vive en
  `<protocolo>.paquete.json`: cada archivo, por sha256.
- **Receta** `benchmarks/recetas/<id>.json`: la versión del modelo, global. Declara su
  padre, el motivo y lo que cambia: combustible, parámetros, política de semilla.
- **Iteración** = receta × caso. Su manifiesto registra además lo que no se declara
  (commit, hashes de cada insumo y salida), y con eso se detecta lo que cambió sin avisar.

Sólo se comparan peras con peras: recetas distintas sobre el mismo caso, o la misma
receta sobre casos distintos.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

RAIZ = Path("benchmarks")

# Años publicados de cada insumo de combustible. Una receta puede pedir un año fijo o
# "anterior_al_fuego", que resuelve al último publicado antes del incendio: así la misma
# receta se aplica a incendios de años distintos sin fuga temporal.
ANIOS_COMBUSTIBLE = {
    "worldcover": (2020, 2021),
    "ccsbap": (2013, 2017),
    "mapbiomas": tuple(range(1985, 2025)),   # Colección 2
}
# Las únicas perillas que una receta puede tocar: los kwargs de
# namelist_writer.write_namelist que no son rutas, y el ADJ uniforme. Ningún keyword de
# namelist nuevo sale de acá (CLAUDE.md).
PARAMETROS = {"dt_s", "dtmax_s", "dtdump_s", "crown_fire_model",
              "lh_moisture_pct", "lw_moisture_pct",
              # transformaciones de rásters que ELMFIRE ya lee (app/validation/cadena.py)
              "adj", "adj_grupos", "factor_viento", "humedad_muerta_delta",
              "humedad_m1_delta", "modelo_humedad", "rotacion_viento", "z0_desde_dosel",
              "aspecto_mas_180"}
MODELOS_HUMEDAD = {"retardo", "fosberg", "altura"}
POLITICAS_SEMILLA = {"prediccion", "observacion"}


def _sha_json(datos: dict) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Ventana:
    """`t0` es la hora de la banda 0 del clima; la simulación arranca `tstart_s` después
    (el `SIMULATION_TSTART` que ancla el fuego al reloj) y dura `horas`."""
    t0: datetime
    horas: int
    tstart_s: float = 0.0

    @property
    def inicio(self) -> datetime:
        return self.t0 + timedelta(seconds=self.tstart_s)

    @property
    def fin(self) -> datetime:
        return self.inicio + timedelta(hours=self.horas)


@dataclass
class Caso:
    incendio: str
    protocolo: str
    anio_fuego: int
    ventanas: list[Ventana]
    datos: dict   # el JSON completo: semilla, referencias, caja, clima

    @property
    def id(self) -> str:
        return f"{self.incendio}/{self.protocolo}"

    @property
    def contiguo(self) -> bool:
        return all(a.fin == b.inicio for a, b in zip(self.ventanas, self.ventanas[1:]))

    @property
    def ruta_paquete(self) -> Path:
        return RAIZ / "casos" / self.incendio / f"{self.protocolo}.paquete.json"

    def paquete(self) -> dict:
        """{"comunes": {nombre: sha}, "ventanas": [{nombre: sha}, ...]}"""
        if not self.ruta_paquete.exists():
            raise FileNotFoundError(f"{self.id} sin paquete: correr `benchmark.py empaquetar`")
        return json.loads(self.ruta_paquete.read_text())

    def sha(self) -> str:
        """Identidad del caso: su definición más su paquete congelado."""
        paquete = self.paquete() if self.ruta_paquete.exists() else {}
        return _sha_json({"caso": self.datos, "paquete": paquete})

    @classmethod
    def cargar(cls, caso_id: str) -> "Caso":
        incendio, protocolo = caso_id.split("/")
        datos = json.loads((RAIZ / "casos" / incendio / f"{protocolo}.json").read_text())
        ventanas = [Ventana(datetime.fromisoformat(v["t0"]), int(v["horas"]),
                            float(v.get("tstart_s", 0.0))) for v in datos["ventanas"]]
        if not ventanas:
            raise ValueError(f"{caso_id}: sin ventanas")
        return cls(incendio, protocolo, int(datos["anio_fuego"]), ventanas, datos)


@dataclass
class Receta:
    id: str
    padre: str | None
    motivo: str
    combustible: dict            # {"fuente": ..., "anio": int | "anterior_al_fuego"}
    semilla: str
    parametros: dict = field(default_factory=dict)

    def sha(self) -> str:
        return _sha_json(self.__dict__)

    def anio_combustible(self, caso: Caso) -> int:
        """Resuelve el año y aplica la regla de fuga: el mapa tiene que ser anterior al
        incendio, o ya ve la cicatriz que se quiere predecir."""
        fuente, anio = self.combustible["fuente"], self.combustible["anio"]
        publicados = ANIOS_COMBUSTIBLE[fuente]
        if anio == "anterior_al_fuego":
            previos = [a for a in publicados if a < caso.anio_fuego]
            if not previos:
                raise ValueError(f"{fuente}: ningún año publicado antes de {caso.anio_fuego}")
            return max(previos)
        if anio not in publicados:
            raise ValueError(f"{fuente} {anio}: año no publicado")
        if anio >= caso.anio_fuego:
            raise ValueError(f"fuga temporal: {fuente} {anio} no es anterior al incendio "
                             f"({caso.anio_fuego}) de {caso.id}")
        return anio

    def validar(self, caso: Caso) -> None:
        if self.combustible.get("fuente") not in ANIOS_COMBUSTIBLE:
            raise ValueError(f"{self.id}: fuente de combustible desconocida")
        if self.semilla not in POLITICAS_SEMILLA:
            raise ValueError(f"{self.id}: semilla '{self.semilla}' no es {POLITICAS_SEMILLA}")
        extras = set(self.parametros) - PARAMETROS
        if extras:
            raise ValueError(f"{self.id}: perillas no permitidas {sorted(extras)}")
        modelo = self.parametros.get("modelo_humedad")
        if modelo is not None and modelo not in MODELOS_HUMEDAD:
            raise ValueError(f"{self.id}: modelo de humedad '{modelo}' no es {MODELOS_HUMEDAD}")
        if self.semilla == "prediccion" and not caso.contiguo:
            raise ValueError(f"{self.id}: sembrar con lo predicho exige ventanas contiguas, "
                             f"y {caso.id} no las tiene")
        self.anio_combustible(caso)

    def factores(self, caso: Caso) -> dict:
        """Lo declarado, ya resuelto contra el caso: lo que se compara entre recetas."""
        return {"combustible": f"{self.combustible['fuente']}{self.anio_combustible(caso)}",
                "semilla": self.semilla, **self.parametros}

    @classmethod
    def cargar(cls, receta_id: str) -> "Receta":
        datos = json.loads((RAIZ / "recetas" / f"{receta_id}.json").read_text())
        return cls(id=receta_id, padre=datos.get("padre"), motivo=datos["motivo"],
                   combustible=datos["combustible"], semilla=datos["semilla"],
                   parametros=datos.get("parametros", {}))


def ruta_iteracion(caso_id: str, receta_id: str) -> Path:
    return RAIZ / "iteraciones" / caso_id / receta_id


def cargar_manifiesto(caso_id: str, receta_id: str) -> dict | None:
    ruta = ruta_iteracion(caso_id, receta_id) / "manifiesto.json"
    return json.loads(ruta.read_text()) if ruta.exists() else None


def cargar_metricas(caso_id: str, receta_id: str) -> dict | None:
    ruta = ruta_iteracion(caso_id, receta_id) / "metricas.json"
    return json.loads(ruta.read_text()) if ruta.exists() else None


def deltas(ma: dict, mb: dict) -> list[dict]:
    """Por ventana, (a, b) de cada métrica que las dos iteraciones puntuaron."""
    return [
        {"n": va["n"], **{f"{ref}.{clave}": (va[ref][tipo].get(clave), vb[ref][tipo].get(clave))
                          for ref, tipo in (("firms", "incremento"), ("cicatriz", "acumulado"))
                          if ref in va and ref in vb
                          for clave in ("dice", "recall", "precision", "sesgo_area")}}
        for va, vb in zip(ma["ventanas"], mb["ventanas"])]


def exigir_receta_intacta(receta: Receta, caso: Caso) -> None:
    """Una receta con iteraciones corridas es inmutable: editarla reescribiría la historia
    de todo lo que ya se puntuó con ella. Se crea otra receta con esta como padre."""
    manifiesto = cargar_manifiesto(caso.id, receta.id)
    if manifiesto and manifiesto["receta_sha"] != receta.sha():
        raise ValueError(f"la receta {receta.id} cambió después de correr sobre {caso.id}; "
                         "crear una receta nueva con padre "
                         f"'{receta.id}' en vez de editarla")


# Qué insumos puede mover cada factor declarado. Todo lo demás que cambie de hash sin que
# lo cubra un factor es un cambio NO declarado.
_INSUMOS_POR_FACTOR = {
    "combustible": {"fbfm40.tif"},
    "adj": {"adj.tif"},
    "adj_grupos": {"adj.tif"},
    "humedad_m1_delta": {"m1.tif"},
    "factor_viento": {"ws.tif"},
    "rotacion_viento": {"wd.tif"},
    "z0_desde_dosel": {"ws.tif"},
    "aspecto_mas_180": {"asp.tif"},
    "humedad_muerta_delta": {"m1.tif", "m10.tif", "m100.tif"},
    "modelo_humedad": {"m1.tif", "m10.tif", "m100.tif"},
}


def comparar(a: dict, b: dict) -> dict:
    """Diff de dos manifiestos de iteración: factores declarados y hashes que cambiaron.

    Rechaza lo que no es peras con peras. Entre casos distintos sólo se comparan métricas:
    los insumos difieren todos, por construcción.
    """
    mismo_caso, misma_receta = a["caso"] == b["caso"], a["receta"] == b["receta"]
    if not (mismo_caso or misma_receta):
        raise ValueError("sólo se comparan recetas distintas sobre el mismo caso, o la misma "
                         f"receta sobre casos distintos: {a['caso']}/{a['receta']} contra "
                         f"{b['caso']}/{b['receta']}")
    declarados = {k: (a["factores"].get(k), b["factores"].get(k))
                  for k in sorted(set(a["factores"]) | set(b["factores"]))
                  if a["factores"].get(k) != b["factores"].get(k)}
    salida: dict[str, Any] = {
        "tipo": "recetas" if mismo_caso else "casos", "declarados": declarados,
        "codigo": None if a["git"]["sha"] == b["git"]["sha"]
        else (a["git"]["sha"], b["git"]["sha"]),
        "no_declarados": []}
    if not mismo_caso:
        return salida
    if a["caso_sha"] != b["caso_sha"]:
        salida["no_declarados"].append({"ventana": None, "insumo": "paquete del caso"})
    # Lo que un factor declarado puede mover. `elmfire.data` refleja cualquier parámetro,
    # y la semilla de una ventana hereda todo lo anterior en una cadena `prediccion`.
    esperados = set()
    for factor in declarados:
        esperados |= _INSUMOS_POR_FACTOR.get(factor, {"elmfire.data"})
    for va, vb in zip(a["ventanas"], b["ventanas"]):
        heredado = va["n"] > 0 and bool(declarados)
        # El namelist lleva las rutas de la iteración: se compara sin ellas.
        ia = va["insumos"] | {"elmfire.data": va["namelist_sha"]}
        ib = vb["insumos"] | {"elmfire.data": vb["namelist_sha"]}
        for nombre in sorted(set(ia) | set(ib)):
            if ia.get(nombre) == ib.get(nombre):
                continue
            if nombre in esperados or (nombre == "phi.tif" and heredado):
                continue
            salida["no_declarados"].append({"ventana": va["n"], "insumo": nombre})
    return salida
