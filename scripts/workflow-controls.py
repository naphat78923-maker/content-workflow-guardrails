#!/usr/bin/env python3
"""Pure local recommendation/date controls. No network or queue writes."""
import argparse
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")
STATES = {"active", "cooldown", "paused", "closed"}
PUBLISHED = {"reported-posted/unverified", "platform-verified"}


def local_moment(value):
    if not value:
        return None
    value = str(value)
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), time.min, BANGKOK)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BANGKOK)
    return parsed.astimezone(BANGKOK)


def evaluate(record, as_of):
    """Preserve supplied fields; change recommendation state only."""
    today = date.fromisoformat(as_of)
    result = dict(record)
    state = record.get("recommendation_state", "active")
    if state not in STATES:
        raise ValueError("Invalid recommendation_state")
    count = record.get("unchanged_pitch_count", 0)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("unchanged_pitch_count must be a nonnegative integer")
    delivered = local_moment(record.get("last_presented_at"))
    response = local_moment(record.get("last_response_at"))
    agreed = local_moment(record.get("agreed_review_at"))
    result["pause_after"] = (
        (delivered.date() + timedelta(days=7)).isoformat() if delivered else None
    )
    if delivered and delivered.date() > today:
        raise ValueError("Delivery date is in the future")
    if state in {"closed", "paused"}:
        result["control_reason"] = "existing suppression retained; resume needs explicit handling"
    elif record.get("publication_status") in PUBLISHED:
        result["recommendation_state"] = "closed"
        result["control_reason"] = "publication already reported/verified; no posting nudge"
    elif (
        record.get("awaiting_user_decision", True)
        and delivered
        and (response is None or response <= delivered)
        and (agreed is None or agreed.date() <= today)
        and today >= delivered.date() + timedelta(days=7)
    ):
        result["recommendation_state"] = "paused"
        result["paused_at"] = as_of
        result["pause_reason"] = "no item-specific reply in seven calendar days"
        result["control_reason"] = result["pause_reason"]
    elif state == "cooldown" or count >= 2:
        result["recommendation_state"] = "cooldown"
        result["control_reason"] = "shared delivery cap reached or existing cooldown retained"
    else:
        result["recommendation_state"] = state
        result["control_reason"] = (
            "delivery date unknown; no invented pause" if not delivered else "not due for pause"
        )
    return result


def weekly_counts(events, start, end):
    """Deduplicate named events and Bangkok dates, never infer coverage."""
    start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
    if end_day < start_day:
        raise ValueError("End before start")
    unique = {}
    for source in events:
        row = dict(source)
        status = row.get("publication_status")
        if status not in PUBLISHED or row.get("is_repost_of_other", False):
            continue
        identity = row.get("post_id") or row.get("event_id")
        if not identity:
            raise ValueError("A stable post_id/event_id is required for deduplication")
        key = (row.get("platform", "unknown"), row.get("account", "unknown"), str(identity))
        previous = unique.get(key)
        if previous:
            a = local_moment(previous.get("published_at"))
            b = local_moment(row.get("published_at"))
            if a and b and a.date() != b.date():
                raise ValueError("Conflicting publication dates for the same event")
            row["published_at"] = row.get("published_at") or previous.get("published_at")
            if previous["publication_status"] == "platform-verified":
                row["publication_status"] = "platform-verified"
        unique[key] = row
    buckets = {}
    all_verified, all_reported = set(), set()
    unknown_reports = 0
    for (platform, account, _), row in unique.items():
        moment = local_moment(row.get("published_at"))
        if moment and not start_day <= moment.date() <= end_day:
            continue
        label = f"{platform}|{account}"
        bucket = buckets.setdefault(label, {"verified": set(), "reported": set(), "unknown": 0})
        if moment is None:
            bucket["unknown"] += 1
            unknown_reports += 1
            continue
        day = moment.date().isoformat()
        if row["publication_status"] == "platform-verified":
            bucket["verified"].add(day)
            all_verified.add(day)
        else:
            bucket["reported"].add(day)
            all_reported.add(day)
    def summarize(verified, reported, unknown):
        return {
            "verified_days": sorted(verified),
            "additional_reported_only_days": sorted(reported - verified),
            "unique_dated_days": len(verified | reported),
            "unknown_date_reports_unassigned_to_week": unknown,
        }
    return {
        "start": start, "end": end, "timezone": "Asia/Bangkok",
        "by_platform_account": {
            label: summarize(b["verified"], b["reported"], b["unknown"])
            for label, b in sorted(buckets.items())
        },
        "all_channels_union": summarize(all_verified, all_reported, unknown_reports),
        "coverage": "not inferred from events; supply actual check timestamps separately",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    control = subs.add_parser("evaluate")
    control.add_argument("--input", required=True)
    control.add_argument("--as-of", required=True)
    weekly = subs.add_parser("weekly")
    weekly.add_argument("--input", required=True)
    weekly.add_argument("--start", required=True)
    weekly.add_argument("--end", required=True)
    args = parser.parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Input must be an array of explicit records")
    result = ([evaluate(row, args.as_of) for row in rows] if args.command == "evaluate"
              else weekly_counts(rows, args.start, args.end))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
