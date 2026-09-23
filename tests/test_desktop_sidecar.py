import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tsuzu.source import create_source
from tsuzu.desktop_sidecar import _ensure_selected_vault
from tsuzu.vault import ActiveVaultLocator

SIDECAR = Path(__file__).parents[1] / "desktop" / "src-tauri" / "binaries" / "tsuzu-core-aarch64-apple-darwin"


class DesktopSidecarTests(unittest.TestCase):
    def test_initializes_only_an_empty_explicit_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "Vault"
            vault.mkdir()
            locator = ActiveVaultLocator(root / "Core" / "control")

            _ensure_selected_vault(locator, vault)

            self.assertEqual(locator.resolve_active_vault().root_ref, vault.resolve())

    def test_refuses_to_bind_an_existing_nonempty_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "Vault"
            vault.mkdir()
            (vault / "keep.txt").write_text("existing user data")
            locator = ActiveVaultLocator(root / "Core" / "control")

            with self.assertRaisesRegex(SystemExit, "not empty"):
                _ensure_selected_vault(locator, vault)

            self.assertEqual((vault / "keep.txt").read_text(), "existing user data")
            self.assertEqual(locator.inspect_locator().status, "MISSING")

    @unittest.skipUnless(SIDECAR.is_file(), "build the Tauri sidecar to enable this integration check")
    def test_compiled_sidecar_commits_a_draft_and_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_local = root / "app-local"
            drafts = app_local / "capture-drafts"
            draft_id = "00000000-0000-4000-8000-000000000001"
            source_root = drafts / "sources" / draft_id
            (source_root / "payload").mkdir(parents=True)
            (drafts / "layout.json").write_text('{"format":"tsuzu-capture-draft-v1"}')
            manifest = create_source(
                "temporary sidecar integration check",
                kind="TEXT",
                capture_method="LOCAL_TEXT",
                object_id=draft_id,
                captured_at="2026-09-23T00:00:00.000Z",
            )
            (source_root / "source.md").write_text("---\n" + json.dumps(manifest) + "\n---\n")
            (source_root / "payload" / "original").write_text("temporary sidecar integration check")
            vault = root / "Vault"
            command = [
                str(SIDECAR),
                "--app-local-root", str(app_local),
                "--core-root", str(root / "Core"),
                "--vault-root", str(vault),
            ]

            run = subprocess.run(command, capture_output=True, text=True, check=True)

            receipts = json.loads(run.stdout)
            committed = next(record for record in receipts if record["status"] == "COMMITTED")
            self.assertTrue((source_root / "core-receipt.json").is_file())
            self.assertTrue((vault / "canonical" / "sources" / committed["source_id"] / "source.md").is_file())

            reopened = subprocess.run(command, capture_output=True, text=True, check=True)
            replay = json.loads(reopened.stdout)
            self.assertEqual(replay[0]["status"], "ALREADY_COMMITTED")
            self.assertEqual(replay[0]["source_id"], committed["source_id"])


if __name__ == "__main__":
    unittest.main()
