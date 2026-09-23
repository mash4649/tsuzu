"""Codex command-hook entry point; stdout is reserved for hook JSON."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tsuzu.codex_hook import CodexPromptHook  # noqa: E402


def main() -> None:
    try:
        event = json.load(sys.stdin)
        default = Path.home() / "Library" / "Application Support" / "TSUZU" / "codex-hooks"
        enabled = os.environ.get("TSUZU_CODEX_PASSIVE_RECALL", "1") == "1"
        data_root = Path(os.environ.get("TSUZU_CODEX_DATA_ROOT", default)).expanduser()
        configured_core = os.environ.get("TSUZU_CORE_ROOT")
        core_root = Path(configured_core).expanduser() if configured_core else None
        if not data_root.is_absolute() or (core_root is not None and not core_root.is_absolute()):
            print("{}")
            return
        result = CodexPromptHook(data_root, ROOT, passive_enabled=enabled, core_root=core_root).handle(event)
        print(json.dumps(result.hook_output, separators=(",", ":")))
    except Exception:
        print("{}")


if __name__ == "__main__":
    main()
