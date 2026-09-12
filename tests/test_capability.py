import unittest

from tsuzu.capability import Capability, CapabilityRegistry, CapabilityReport, NO, UNKNOWN, UNVERIFIED, VERIFIED


class CapabilityTests(unittest.TestCase):
    def test_verified_route_and_fail_closed_unknown(self):
        registry = CapabilityRegistry()
        registry.publish(CapabilityReport("claude_code", "CLAUDE_CODE", "1", "2026-09-12T00:00:00.000Z", "runtime", (Capability("EXPLICIT_RECALL", VERIFIED, ("GLOBAL",)),), "TRUSTED_EXTERNAL"))
        self.assertEqual(registry.supports("claude_code", "EXPLICIT_RECALL"), VERIFIED)
        self.assertEqual(registry.route("EXPLICIT_RECALL", ("unknown", "claude_code")), "claude_code")
        self.assertEqual(registry.supports("unknown", "EXPLICIT_RECALL"), UNKNOWN)
        self.assertEqual(registry.supports("claude_code", "PASSIVE_CONTEXT_INJECTION"), NO)

    def test_version_invalidation_removes_support(self):
        registry = CapabilityRegistry()
        registry.publish(CapabilityReport("claude_code", "CLAUDE_CODE", "1", "2026-09-12T00:00:00.000Z", "runtime", (Capability("EXPLICIT_RECALL", VERIFIED),), "TRUSTED_EXTERNAL"))
        registry.invalidate_report("claude_code", "version changed")
        self.assertEqual(registry.get_capability_report("claude_code").capabilities[0].state, UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
