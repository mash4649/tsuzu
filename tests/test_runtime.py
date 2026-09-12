import unittest

from tsuzu.runtime import runtime_info


class RuntimeInfoTests(unittest.TestCase):
    def test_reports_supported_runtime_and_stdlib_storage(self):
        info = runtime_info()

        self.assertEqual(info["language"], "python")
        self.assertGreaterEqual(info["major"], 3)
        self.assertEqual(info["storage"], "sqlite3")
        self.assertTrue(info["stdlib_only"])


if __name__ == "__main__":
    unittest.main()
