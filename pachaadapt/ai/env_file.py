"""Carga mínima de un archivo .env sin dependencias de terceros ni salida a logs."""
from __future__ import annotations

import re
from pathlib import Path
from typing import MutableMapping

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_env_file(path: Path, environ: MutableMapping[str, str]) -> None:
    """Añade variables de archivo solo si no están definidas ya en el proceso.

    Admite líneas KEY=VALUE, comillas sencillas/dobles y comentarios de línea.
    No expande variables ni ejecuta shell, para que los valores no se evalúen.
    """
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not _NAME.fullmatch(name) or name in environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        environ[name] = value
