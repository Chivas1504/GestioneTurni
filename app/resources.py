from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path


def app_icon() -> QIcon:
    icon_path = resource_path("assets/gestione_turni.ico")

    if not icon_path.is_file():
        return QIcon()

    return QIcon(str(icon_path))
