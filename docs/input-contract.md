# Input contract

Every input file is a JSON array. Examples are synthetic.

## `evaluate`

```bash
python3 scripts/workflow-controls.py evaluate --input examples/drafts.json --as-of 2026-10-03
```

Relevant fields:

- `recommendation_state`: `active` (default), `cooldown`, `paused`, or `closed`.
- `unchanged_pitch_count`: nonnegative integer; booleans are rejected. Count across all delivery channels. Default is zero.
- `last_presented_at`: ISO date/timestamp, or null/absent if unknown.
- `last_response_at`: latest item-specific response, not a general chat reply.
- `awaiting_user_decision`: defaults to true. Set false when the next action is not a pending human decision, such as authorised production.
- `agreed_review_at`: an explicitly agreed future review, not a date the assistant invented.
- `publication_status`: `reported-posted/unverified` or `platform-verified` suppress a further posting nudge for active/cooldown records. Other publication values are preserved.
- `content_status`, `copy_approval`, `id`, and other metadata: passed through, not inferred or validated as publication permission.

The output is a new list of dictionaries. It adds `pause_after` and `control_reason`; a newly paused recommendation also records `paused_at` and `pause_reason`.

Policy precedence: retain existing `closed`/`paused`; otherwise close for reported/verified publication; otherwise apply the inactivity pause when eligible; otherwise retain cooldown/apply the two-presentation cap; otherwise retain active. Existing paused records are not relabelled closed just because publication is subsequently reported. All these states suppress unsolicited recommendations; actual approval/publication evidence is separate.

A date later than `--as-of` for the last presentation is rejected. Unknown delivery date means no invented expiry. A reply later than the presentation prevents the inactivity rule from treating the item as silently awaiting a decision; the caller must then handle the real next action.

## `weekly`

```bash
python3 scripts/workflow-controls.py weekly --input examples/publications.json --start 2026-10-05 --end 2026-10-11
```

Relevant fields:

- `event_id` or `post_id`: stable identity, required for included events. The dedupe key is platform + account + identity.
- `platform`, `account`: reporting buckets; synthetic examples use `demo`.
- `publication_status`: included only if `reported-posted/unverified` or `platform-verified`.
- `published_at`: ISO date/timestamp or null if unknown. Dates are not guessed.
- `is_repost_of_other`: true excludes a repost of someone else's content.

The date range is inclusive. A repeated event is not an additional post; conflicts on its Bangkok date are rejected. Verified evidence takes precedence over reported-only status for the same event.

Output contains `by_platform_account` and `all_channels_union`. `unique_dated_days` is a set union, not a sum of per-platform totals. Unknown-date records are returned as `unknown_date_reports_unassigned_to_week`; their count does not claim they happened in the requested week. Feed coverage must be supplied and checked separately.

## Timezone

This first version uses `Asia/Bangkok`. A date-only value is midnight in that timezone; a timestamp without an offset is also treated as Bangkok local time. `Z` and explicit offsets are converted before comparing dates. Missing IANA timezone data must be resolved in the caller's environment (for example with Python's `tzdata` package).

## Privacy

There are no network calls or queue writes. But fields you supply can appear in output unchanged. This contract provides no secret scanning, anonymisation or authority to publish anything.
