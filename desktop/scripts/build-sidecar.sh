#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
target_triple="$(rustc -vV | awk '$1 == "host:" { print $2 }')"

UV_TOOL_DIR=/private/tmp/tsuzu-uv-tools UV_CACHE_DIR=/private/tmp/tsuzu-uv-cache \
PYINSTALLER_CONFIG_DIR=/private/tmp/tsuzu-pyinstaller-config \
uvx --from pyinstaller pyinstaller \
  --noconfirm --clean --onefile \
  --name "tsuzu-core-${target_triple}" \
  --distpath "${repo_root}/desktop/src-tauri/binaries" \
  --workpath "${repo_root}/desktop/.sidecar-build/work" \
  --specpath "${repo_root}/desktop/.sidecar-build" \
  --paths "${repo_root}/src" \
  "${repo_root}/desktop/sidecar_entry.py"
