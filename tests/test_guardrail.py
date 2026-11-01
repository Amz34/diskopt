import os
import unittest
from diskopt.engine import verify_guardrail, get_disk_metric, scan_reclaimable

class TestDiskOptEngine(unittest.TestCase):
    def test_guardrail_blocks_root(self):
        passed, reason = verify_guardrail("/")
        self.assertFalse(passed)
        self.assertIn("protected system directory", reason)

    def test_guardrail_blocks_etc_and_bin(self):
        for p in ["/etc", "/bin", "/usr/bin", "/var/lib"]:
            passed, reason = verify_guardrail(p)
            self.assertFalse(passed, f"Failed to block {p}")

    def test_guardrail_allows_user_cache(self):
        user_cache = os.path.expanduser("~/.cache")
        passed, reason = verify_guardrail(user_cache)
        self.assertTrue(passed)
        self.assertIsNone(reason)

    def test_guardrail_allows_tmp(self):
        passed, reason = verify_guardrail("/tmp")
        self.assertTrue(passed)
        self.assertIsNone(reason)

    def test_metric_calculation(self):
        metric = get_disk_metric("/")
        self.assertGreater(metric.total_gb, 0)
        self.assertGreaterEqual(metric.usage_percent, 0.0)
        self.assertLessEqual(metric.usage_percent, 100.0)
        self.assertIn(metric.status, ["HEALTHY", "ELEVATED", "WARNING", "CRITICAL"])

    def test_scan_reclaimable(self):
        candidates = scan_reclaimable()
        self.assertIsInstance(candidates, list)
        for c in candidates:
            self.assertTrue(c.guardrail_passed)

if __name__ == "__main__":
    unittest.main()
