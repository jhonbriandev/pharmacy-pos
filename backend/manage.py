#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para tareas administrativas."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "No se pudo importar Django. Verifica que el entorno virtual este "
            "activado y que las dependencias esten instaladas:\n"
            "    python -m venv .venv\n"
            "    .\\.venv\\Scripts\\Activate.ps1\n"
            "    pip install -r requirements-dev.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
