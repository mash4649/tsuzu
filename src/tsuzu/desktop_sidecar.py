"""Minimal packaged Tauri ingress entry point; intentionally excludes host adapters."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tsuzu.desktop_ingress import DesktopDraftIngress
from tsuzu.index import IndexManager
from tsuzu.vault import ActiveVaultLocator


def main() -> None:
    parser = argparse.ArgumentParser(prog="tsuzu-core")
    parser.add_argument("--app-local-root", required=True)
    parser.add_argument("--core-root", required=True)
    parser.add_argument("--vault-root", required=True)
    args = parser.parse_args()

    core_root = Path(args.core_root).expanduser()
    vault_root = Path(args.vault_root).expanduser()
    if not core_root.is_absolute() or not vault_root.is_absolute() or core_root.is_symlink():
        raise SystemExit("Core and Vault roots must be absolute real paths")
    if any((core_root / name).is_symlink() for name in ("control", "queue", "index")):
        raise SystemExit("Core state directories must not be symlinks")
    locator = ActiveVaultLocator(core_root / "control")
    _ensure_selected_vault(locator, vault_root)

    index = IndexManager(core_root / "index", locator)
    index.open()
    try:
        results = DesktopDraftIngress(args.app_local_root, core_root / "queue", locator, index).process_all()
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, sort_keys=True))
    finally:
        index.close()


def _ensure_selected_vault(locator: ActiveVaultLocator, vault_root: Path) -> None:
    health = locator.inspect_locator()
    if health.status == "MISSING":
        if vault_root.is_symlink():
            raise SystemExit("selected Vault must not be a symlink")
        vault_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if any(vault_root.iterdir()):
            raise SystemExit("selected Vault is not empty; refusing to initialize it")
        locator.initialize(vault_root, operation_id="tauri-first-run")
    elif health.status != "HEALTHY" or locator.resolve_active_vault().root_ref != vault_root.resolve():
        raise SystemExit("selected Core already points to another or unhealthy Vault")


if __name__ == "__main__":
    main()
