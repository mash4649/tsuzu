import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tsuzu.vault import (
    ActiveVaultLocator,
    LocatorError,
    StaleGenerationError,
)


class ActiveVaultLocatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "vault-a"
        self.root.mkdir()
        self.state = Path(self.temp.name) / "control"
        self.locator = ActiveVaultLocator(self.state)

    def tearDown(self):
        self.temp.cleanup()

    def test_single_resolution_and_body_free_receipt(self):
        self.locator.initialize(self.root, operation_id="init-a")

        handle = self.locator.resolve_active_vault()
        self.assertEqual(handle.root_ref, self.root.resolve())
        self.assertEqual(handle.generation, 1)
        self.assertEqual(self.locator.compare_generation(handle), "CURRENT")
        self.assertEqual(self.locator.inspect_locator().status, "HEALTHY")

        receipt = (self.state / "locator-receipts.jsonl").read_text()
        self.assertIn("init-a", receipt)
        self.assertNotIn(str(self.root), receipt)

    def test_missing_and_corrupt_locator_fail_closed(self):
        self.assertEqual(self.locator.inspect_locator().status, "MISSING")
        with self.assertRaises(LocatorError):
            self.locator.resolve_active_vault()

        self.state.mkdir(exist_ok=True)
        (self.state / "active-vault.json").write_text("not-json")
        self.assertEqual(self.locator.inspect_locator().status, "CORRUPT")
        with self.assertRaises(LocatorError):
            self.locator.resolve_active_vault()

    def test_cutover_rejects_stale_expected_generation_and_old_handle(self):
        self.locator.initialize(self.root, operation_id="init-a")
        old = self.locator.resolve_active_vault()
        root_b = Path(self.temp.name) / "vault-b"
        root_b.mkdir()
        candidate = self.locator.prepare_candidate(root_b)

        switched = self.locator.switch_active_vault(1, candidate, "switch-b")
        self.assertEqual(switched.generation, 2)
        self.assertEqual(self.locator.compare_generation(old), "STALE")
        with self.assertRaises(StaleGenerationError):
            self.locator.assert_current(old)
        with self.assertRaises(StaleGenerationError):
            self.locator.switch_active_vault(1, candidate, "stale-switch")

    def test_rollback_is_monotonic(self):
        self.locator.initialize(self.root, operation_id="init-a")
        old = self.locator.resolve_active_vault()
        root_b = Path(self.temp.name) / "vault-b"
        root_b.mkdir()
        candidate = self.locator.prepare_candidate(root_b)
        self.locator.switch_active_vault(1, candidate, "switch-b")

        rolled_back = self.locator.rollback_active_vault(
            2, old, "rollback-a"
        )
        self.assertEqual(rolled_back.generation, 3)
        self.assertEqual(rolled_back.vault_id, old.vault_id)
        self.assertEqual(self.locator.resolve_active_vault().generation, 3)

    def test_symlink_root_is_rejected(self):
        target = Path(self.temp.name) / "real-vault"
        target.mkdir()
        link = Path(self.temp.name) / "linked-vault"
        os.symlink(target, link)
        report = self.locator.preflight_vault(link)
        self.assertFalse(report.supported)
        self.assertIn("symlink", report.reason)

    def test_unsupported_filesystem_blocks_initialization(self):
        with mock.patch("tsuzu.vault.os.link", side_effect=OSError("unsupported")):
            report = self.locator.preflight_vault(self.root)
            self.assertFalse(report.supported)
            with self.assertRaises(LocatorError):
                self.locator.initialize(self.root, operation_id="blocked")

    def test_locator_schema_has_no_user_body(self):
        self.locator.initialize(self.root, operation_id="init-a")
        record = json.loads((self.state / "active-vault.json").read_text())
        self.assertEqual(record["locator_schema_version"], "1.0.0")
        self.assertIn("active", record)
        self.assertIn("capabilities", record)
        self.assertNotIn("body", record)
        self.assertNotIn("content", record)
        self.assertNotIn("credential", record)

    def test_unavailable_root_is_degraded(self):
        self.locator.initialize(self.root, operation_id="init-a")
        self.root.rmdir()
        health = self.locator.inspect_locator()
        self.assertEqual(health.status, "DEGRADED")
        self.assertFalse(health.capabilities_supported)


if __name__ == "__main__":
    unittest.main()
