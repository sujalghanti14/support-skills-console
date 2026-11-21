# Product Changelog

## 2026.11.2 — 2026-11-10
### Known issues
- KI-412: CSV export times out for workspaces with more than 50,000 rows. Workaround: filter by date range and export in batches. Fix scheduled for 2026.11.3.
- KI-415: Safari 17 users may see a blank dashboard after login until they refresh the page.
### Fixed
- Slack integration no longer posts duplicate notifications when a task is reassigned.

## 2026.11.1 — 2026-11-03
### Fixed
- KI-398: Password reset emails delayed by up to 30 minutes for Outlook domains.
- Timezone shown incorrectly on recurring task due dates for users in UTC+5:30.
### Known issues
- KI-409: Mobile app (Android 15) crashes when attaching a photo larger than 20 MB.

## 2026.10.4 — 2026-10-27
### Fixed
- KI-390: Invoices PDF showed wrong currency symbol for EUR accounts.
- Two-factor authentication codes rejected when device clock drifts more than 30 seconds.
