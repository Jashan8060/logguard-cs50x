"""
Unit tests for the LogGuard FMCSA compliance rule engine.
Run via: pytest test_compliance.py
"""

import unittest
from datetime import datetime
from compliance import HOSRuleEngine


class TestHOSRuleEngine(unittest.TestCase):

    def setUp(self):
        self.engine = HOSRuleEngine()

    def test_compliant_shift(self):
        """Test a clean 8-hour driving shift with adequate 10h rest and 30m break."""
        events = [
            {"duty_status": "OFF", "start_time": "2026-10-22 00:00:00", "end_time": "2026-10-22 06:00:00"},
            {"duty_status": "ON",  "start_time": "2026-10-22 06:00:00", "end_time": "2026-10-22 06:30:00"},
            {"duty_status": "D",   "start_time": "2026-10-22 06:30:00", "end_time": "2026-10-22 10:30:00"},
            {"duty_status": "OFF", "start_time": "2026-10-22 10:30:00", "end_time": "2026-10-22 11:15:00"},  # 45m break
            {"duty_status": "D",   "start_time": "2026-10-22 11:15:00", "end_time": "2026-10-22 15:15:00"},
            {"duty_status": "ON",  "start_time": "2026-10-22 15:15:00", "end_time": "2026-10-22 15:45:00"},
            {"duty_status": "SB",  "start_time": "2026-10-22 15:45:00", "end_time": "2026-10-22 23:59:59"}
        ]
        res = self.engine.evaluate_events(events)
        self.assertTrue(res["compliant"])
        self.assertEqual(len(res["violations"]), 0)
        self.assertEqual(res["totals"]["D"], 8 * 3600)

    def test_11_hour_driving_violation(self):
        """Test driving exceeding 11 hours in a shift triggers US_11H_DRIVE."""
        events = [
            {"duty_status": "OFF", "start_time": "2026-10-22 00:00:00", "end_time": "2026-10-22 06:00:00"},
            {"duty_status": "ON",  "start_time": "2026-10-22 06:00:00", "end_time": "2026-10-22 06:30:00"},
            {"duty_status": "D",   "start_time": "2026-10-22 06:30:00", "end_time": "2026-10-22 12:30:00"},  # 6h
            {"duty_status": "OFF", "start_time": "2026-10-22 12:30:00", "end_time": "2026-10-22 13:05:00"},  # 35m break
            {"duty_status": "D",   "start_time": "2026-10-22 13:05:00", "end_time": "2026-10-22 19:05:00"}   # 6h -> Total 12h drive!
        ]
        res = self.engine.evaluate_events(events)
        self.assertFalse(res["compliant"])
        rule_codes = [v["rule_code"] for v in res["violations"]]
        self.assertIn("US_11H_DRIVE", rule_codes)

    def test_14_hour_duty_window_violation(self):
        """Test driving past the 14th hour from shift start triggers US_14H_WINDOW."""
        events = [
            {"duty_status": "OFF", "start_time": "2026-10-22 00:00:00", "end_time": "2026-10-22 05:00:00"},
            {"duty_status": "ON",  "start_time": "2026-10-22 05:00:00", "end_time": "2026-10-22 06:00:00"},  # Shift starts at 05:00
            {"duty_status": "D",   "start_time": "2026-10-22 06:00:00", "end_time": "2026-10-22 10:00:00"},  # 4h drive
            {"duty_status": "OFF", "start_time": "2026-10-22 10:00:00", "end_time": "2026-10-22 18:00:00"},  # 8h off (not 10h, so no reset!)
            {"duty_status": "D",   "start_time": "2026-10-22 19:30:00", "end_time": "2026-10-22 21:00:00"}   # 19:30 is > 14h from 05:00 (which ended at 19:00)
        ]
        res = self.engine.evaluate_events(events)
        self.assertFalse(res["compliant"])
        rule_codes = [v["rule_code"] for v in res["violations"]]
        self.assertIn("US_14H_WINDOW", rule_codes)

    def test_30_minute_break_violation(self):
        """Test driving > 8 hours without a 30m break triggers US_30M_BREAK."""
        events = [
            {"duty_status": "OFF", "start_time": "2026-10-22 00:00:00", "end_time": "2026-10-22 06:00:00"},
            {"duty_status": "ON",  "start_time": "2026-10-22 06:00:00", "end_time": "2026-10-22 06:30:00"},
            {"duty_status": "D",   "start_time": "2026-10-22 06:30:00", "end_time": "2026-10-22 15:30:00"}   # 9 continuous hours driving without break
        ]
        res = self.engine.evaluate_events(events)
        self.assertFalse(res["compliant"])
        rule_codes = [v["rule_code"] for v in res["violations"]]
        self.assertIn("US_30M_BREAK", rule_codes)


if __name__ == "__main__":
    unittest.main()
