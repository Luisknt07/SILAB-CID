"""Empaqueta fuentes docentes; excluye bases, secretos y entornos."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

KIT_FILENAME = "kit-aplicaciones-logisticas-ia.zip"
KIT_DIRNAME = "andina-distribucion"
SOURCE_DIR = Path(__file__).resolve().parent / "contenido"
_ALLOWED_SUFFIXES = {".py", ".html", ".csv", ".md", ".txt", ".json"}
_EXCLUDED_PARTS = {"__pycache__", ".venv", ".qa", "node_modules", ".git"}
_EXCLUDED_NAMES = {".env", ".secreto-local", "db.sqlite3", "opencode.json"}


def source_files():
    for path in sorted(SOURCE_DIR.rglob("*")):
        relative = path.relative_to(SOURCE_DIR)
        if (
            not path.is_file()
            or path.is_symlink()
            or _EXCLUDED_PARTS.intersection(relative.parts)
            or path.name in _EXCLUDED_NAMES
        ):
            continue
        if path.suffix not in _ALLOWED_SUFFIXES and path.name not in {
            "LICENSE",
            ".gitignore",
        }:
            continue
        yield relative.as_posix(), path.read_bytes()


def build_zip() -> bytes:
    """Retorna bytes para ContentFile; misma fuente produce el mismo paquete."""
    files = list(source_files())
    if not files:
        raise ValueError("Faltan las fuentes del kit docente.")
    manifest = (
        "\n".join(f"{sha256(data).hexdigest()}  {name}" for name, data in files) + "\n"
    )
    files.append(("MANIFIESTO_SHA256.txt", manifest.encode("utf-8")))
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files):
            item = ZipInfo(f"{KIT_DIRNAME}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()
