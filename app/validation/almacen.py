"""Almacén direccionado por contenido: cada archivo del benchmark se guarda por su sha256.

Es lo que hace inmutable una iteración: su manifiesto (en git) sólo lista hashes, y con
el almacén se reconstruye byte a byte el directorio que ELMFIRE leyó y el que escribió.

`guardar` **copia** y deja el objeto en sólo lectura. No usa hardlink hacia el almacén
porque GDAL abre en modo `w` truncando el mismo inodo: re-escribir el original
corrompería en silencio el objeto. Del almacén hacia afuera sí se usan hardlinks
(`materializar`), y como el objeto es de sólo lectura, cualquier intento de escribirlo
falla en voz alta.

# ponytail: almacén sólo local, sin respaldo; sumar un bucket detrás de guardar/abrir
# cuando el visor tenga que funcionar desplegado.
"""
import hashlib
import os
import shutil
from pathlib import Path

RAIZ = Path("data/benchmark/objetos")


def _raiz() -> Path:
    """`data/` está montado en /app/data dentro del contenedor y es relativo afuera."""
    absoluta = Path("/app") / RAIZ
    return absoluta if absoluta.exists() else RAIZ


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def abrir(sha: str) -> Path:
    ruta = _raiz() / sha[:2] / sha
    if not ruta.exists():
        raise FileNotFoundError(f"objeto {sha} ausente del almacén")
    return ruta


def guardar(ruta: Path) -> str:
    sha = sha256(ruta)
    destino = _raiz() / sha[:2] / sha
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_suffix(".tmp")
        shutil.copyfile(ruta, temporal)
        os.chmod(temporal, 0o444)
        temporal.replace(destino)
    return sha


def guardar_dir(directorio: Path) -> dict[str, str]:
    """Nombre relativo → sha de cada archivo del directorio (recursivo)."""
    return {
        str(p.relative_to(directorio)): guardar(p)
        for p in sorted(directorio.rglob("*")) if p.is_file()
    }


def materializar(archivos: dict[str, str], destino: Path) -> None:
    """Reconstruye un directorio desde {nombre: sha}, con hardlinks al almacén."""
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, sha in archivos.items():
        ruta = destino / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.unlink(missing_ok=True)
        ruta.hardlink_to(abrir(sha))
