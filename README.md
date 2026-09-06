# Systems events map

A worldwide directory of systems thinking, cybernetics, complexity, system dynamics, and systemic design events, maintained by Benjamin P Taylor. Inspired by [Nick Ananin’s systems events map](https://www.google.com/maps/d/u/0/viewer?mid=1KiZfEQGwEaAsOiEBjTdPN9LC5Pk).

Canonical public map: https://transduction.systems/events/

Vanity URL: https://events.transduction.systems (redirects to the canonical map).

GitHub Pages edition (once enabled): https://antlerboy.github.io/systemsmap/

The hosted edition reads the daily event data and subscription feeds directly from this repository.

## Features

- Search by topic, organisation, country, date range, and attendance format.
- Explore physical locations and approximate country/region focus markers for online events. Filter by geographic focus and language. Access restrictions, language requirements, and interpretation are separate published facts.
- Subscribe to all events, an organisation, a subject, or online events through ICS feeds.
- Download a filtered selection or an individual event.
- Submit an event, public calendar feed, or website through the on-page form to the public GitHub review queue.
- Collect sources daily at 04:23 UTC and after changes to main. GitHub may delay scheduled runs.
- Publish source health, provenance, collection timestamps, and discovered source candidates.

## Coverage and calendars

Worldwide is the scope, not a completeness claim. The register includes SCiO, ISSS, CybSoc, ASC, IFSR, and Systems Innovation, plus scientific and practitioner organisations. Some sources are blocked, private, undated, or require additional parsing. The site distinguishes sources yielding events from sources merely checked. Coverage remains biased towards public structured data. Original titles and languages are retained.

Online focus rings are approximate area markers, never physical venues or inferred access restrictions. Chapter geography is recorded separately from language, and translation is never assumed. City pins are approximate; unknown venues are never guessed. Dates without times are exported as date-only entries and labelled accordingly. Timed entries lacking a time zone are omitted from calendar feeds. Source errors can still propagate; follow the source links before booking. Recurring events are expanded to an 18-month horizon, preserving daylight-saving changes, exceptions, and cancellations. Missing listings are marked for rechecking, never assumed cancelled.

Subscriptions refresh when the receiving calendar app polls. Downloaded ICS files are snapshots. Calendar UIDs remain stable across title and date changes; SEQUENCE and LAST-MODIFIED track changes. Cancelled events remain marked CANCELLED. Events are retained for 90 days after their date.

## Submissions

The public form accepts a URL directly without an account or email address. Optional details are collapsed. A durable D1 inbox behind `https://events.transduction.systems/api/submissions` acknowledges receipt before the form clears. The service preserves the existing events and PSTA redirects. Honeypot, request-size, duplicate, origin, and daily submission limits reduce abuse.

Submissions and optional details are public; the form asks for public information only. IP addresses are not stored. A daily salted IP hash is used only for rate limits and is never included in the public queue.

The daily collection runs `review_public_submissions.py` to extract up to 20 new links per scan using the existing safe fetcher and event parsers. Extracted proposals appear in `dist/data/submission-review.json` and `submissions.html`. Failed or ambiguous extraction stays marked for manual review. Nothing is automatically added to the map. The owner accepts reviewed entries into `data/approved-events.json` or registers an ongoing source in `data/sources.json`.

The earlier GitHub issue queue and approval workflow remain available for maintainers and corrections. Visitors do not need GitHub. Owner-approved issue submissions still use `accept_submission.py`; the public link inbox uses the same event data fields and parser.

## Maintenance

`data/sources.json` is the reviewed register. `scripts/collect.py` handles ICS (including public Google and Teamup feeds), JSON-LD events, and selected organisation-specific HTML. `data/discovered-sources.json` records links found on source pages for review. `data/approved-events.json`, when present, holds reviewed manual events. Failed sources keep their previously collected events with a warning.

The collector honours robots rules, bounds requests and concurrency, checks redirects, rejects nonpublic target addresses in production, and never executes page content. No paid search API is required.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/collect.py
.venv/bin/python scripts/validate.py
```

`dist` is the complete static site. The workflow validates data and publishes through GitHub Pages. Initial activation may require selecting GitHub Actions under Settings → Pages. GitHub may disable scheduled workflows after prolonged repository inactivity. The interface flags collections older than two days.

## Assets

Leaflet 1.9.4 is vendored with its BSD-2-Clause licence. World boundaries derive from Natural Earth public-domain data, distributed through `johan/world.geo.json`. Boundaries are illustrative. No advertising, analytics, or personal data storage is included. GitHub receives issue submissions. Organisers remain the authoritative sources; no endorsement is implied.

## Public interface deployment

The Necessary Tangle pins a reviewed systemsmap revision in its workflows and copies `dist/` through `scripts/integrate_systems_events.py`. Update that revision and publish The Necessary Tangle when changing the interface. Daily event JSON and subscription feeds continue to load from systemsmap. The Sites project recorded in this historical hosting manifest now only redirects the vanity address; do not replace that redirect when updating the interface.
