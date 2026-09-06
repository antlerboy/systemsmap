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

Quick submission requires only a public URL. Optional details are collapsed. The on-page form prepares a structured GitHub issue; plain links in issues are also accepted. A GitHub account is required and submission is completed on GitHub; an unsent proposal is never claimed as received. Include only public information.

On issue creation or editing, `extract_submission.py` extracts JSON-LD events, ICS feeds, or supported event-page facts and posts a preview for review. Ambiguous dates, blocked pages, and missing facts stay in the queue. Multi-event pages become source proposals. No submission is automatically published.

The owner reviews the source, dates, time zone, access, language requirements, and scope. Apply the `approved` label to a valid structured submission to add it automatically. Only approval by the repository owner triggers this path. Link-only approvals are re-parsed; an event without a verified date, title, organiser, or required time zone must be completed before publication. Accepted feeds and pages join the daily scan. Corrections can be supplied through issues or pull requests.

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
