"""Synthetic regression fixtures, not live analytics or model quality tests."""
import importlib.util
from pathlib import Path
from typing import Optional
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow-controls.py"
spec = importlib.util.spec_from_file_location("workflow_controls", SCRIPT)
assert spec is not None and spec.loader is not None
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


class RecommendationTests(unittest.TestCase):
    def record(self, **changes):
        row = dict(id="fixture", recommendation_state="active", content_status="awaiting-copy-approval",
                   publication_status="unknown", copy_approval="retained fixture approval",
                   last_presented_at="2026-10-02", unchanged_pitch_count=1,
                   awaiting_user_decision=True)
        row.update(changes)
        return row

    def test_no_pause_before_seven_days(self):
        self.assertEqual(controls.evaluate(self.record(), "2026-10-08")["recommendation_state"], "active")

    def test_exact_seven_calendar_days_pauses_and_preserves_fields(self):
        source = self.record()
        result = controls.evaluate(source, "2026-10-09")
        self.assertEqual(result["recommendation_state"], "paused")
        for key in ("content_status", "publication_status", "copy_approval"):
            self.assertEqual(source[key], result[key])
        self.assertEqual(source["recommendation_state"], "active")

    def test_user_requested_piece_has_no_cap_exemption(self):
        result = controls.evaluate(self.record(user_requested=True, unchanged_pitch_count=2), "2026-10-03")
        self.assertEqual(result["recommendation_state"], "cooldown")

    def test_later_item_specific_response_prevents_inactivity_pause(self):
        row = self.record(last_response_at="2026-10-06")
        self.assertEqual(controls.evaluate(row, "2026-10-12")["recommendation_state"], "active")

    def test_booleans_are_not_reminder_counts(self):
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    controls.evaluate(self.record(unchanged_pitch_count=value), "2026-10-03")

    def test_unknown_delivery_does_not_invent_expiry(self):
        result = controls.evaluate(self.record(last_presented_at=None), "2026-10-12")
        self.assertEqual(result["recommendation_state"], "active")
        self.assertIsNone(result["pause_after"])

    def test_authorized_production_is_not_paused(self):
        row = self.record(content_status="in-production", awaiting_user_decision=False)
        self.assertEqual(controls.evaluate(row, "2026-10-12")["recommendation_state"], "active")

    def test_future_agreed_review_is_not_auto_paused(self):
        row = self.record(agreed_review_at="2026-10-20")
        self.assertEqual(controls.evaluate(row, "2026-10-12")["recommendation_state"], "active")

    def test_existing_cooldown_closed_and_paused_stay_suppressed(self):
        for state in ("cooldown", "closed", "paused"):
            result = controls.evaluate(self.record(recommendation_state=state), "2026-10-03")
            self.assertEqual(result["recommendation_state"], state)

    def test_reported_publication_is_not_changed_or_nudged(self):
        row = self.record(publication_status="reported-posted/unverified")
        result = controls.evaluate(row, "2026-10-12")
        self.assertEqual(result["publication_status"], "reported-posted/unverified")
        self.assertEqual(result["recommendation_state"], "closed")

    def test_bangkok_conversion_and_future_date_guard(self):
        row = self.record(last_presented_at="2026-10-01T18:00:00Z")
        self.assertEqual(controls.evaluate(row, "2026-10-09")["recommendation_state"], "paused")
        with self.assertRaises(ValueError):
            controls.evaluate(self.record(last_presented_at="2026-10-14"), "2026-10-12")


class WeeklyTests(unittest.TestCase):
    def event(self, identity, platform="X", account="fixture", when: Optional[str]="2026-10-05", status="platform-verified", **extra):
        return dict(event_id=identity, platform=platform, account=account, published_at=when,
                    publication_status=status, **extra)

    def count(self, events):
        return controls.weekly_counts(events, "2026-10-05", "2026-10-11")

    def test_cross_platform_same_day_is_one_overall_day(self):
        result = self.count([self.event("a"), self.event("b", "Instagram")])
        self.assertEqual(result["all_channels_union"]["unique_dated_days"], 1)
        self.assertEqual(len(result["by_platform_account"]), 2)
        self.assertTrue(all(b["unique_dated_days"] == 1 for b in result["by_platform_account"].values()))

    def test_duplicate_event_and_overlapping_report_do_not_inflate_days(self):
        a = self.event("a", status="reported-posted/unverified")
        b = self.event("a")
        c = self.event("c", status="reported-posted/unverified")
        result = self.count([a, a, b, c])["all_channels_union"]
        self.assertEqual(result["unique_dated_days"], 1)
        self.assertEqual(result["additional_reported_only_days"], [])

    def test_unknown_date_is_unassigned_not_today_or_this_week(self):
        result = self.count([self.event("a", when=None, status="reported-posted/unverified")])
        self.assertEqual(result["all_channels_union"]["unique_dated_days"], 0)
        self.assertEqual(result["all_channels_union"]["unknown_date_reports_unassigned_to_week"], 1)
        self.assertIn("not inferred", result["coverage"])

    def test_reposts_and_out_of_window_events_excluded(self):
        result = self.count([self.event("a", is_repost_of_other=True), self.event("b", when="2026-10-04")])
        self.assertEqual(result["all_channels_union"]["unique_dated_days"], 0)

    def test_utc_converts_to_bangkok_day(self):
        result = self.count([self.event("a", when="2026-10-04T18:00:00Z")])
        self.assertEqual(result["all_channels_union"]["verified_days"], ["2026-10-05"])

    def test_conflicting_same_event_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            self.count([self.event("a"), self.event("a", when="2026-10-06")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
