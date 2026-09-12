from __future__ import annotations

import sys
from typing import TypedDict


class RuntimeInfo(TypedDict):
    language: str
    major: int
    minor: int
    storage: str
    stdlib_only: bool


def runtime_info() -> RuntimeInfo:
    """Return the implementation baseline used by the local TSUZU runtime."""

    return {
        "language": "python",
        "major": sys.version_info.major,
        "minor": sys.version_info.minor,
        "storage": "sqlite3",
        "stdlib_only": True,
    }
