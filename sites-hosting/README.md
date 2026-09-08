# Systems events: canonical public home

The public interface now lives at https://transduction.systems/events/. This existing hosted address and the planned events.transduction.systems vanity address return permanent redirects to that canonical home, preserving paths and query strings. The daily collector, source register, stable calendar feeds, and review queue remain in antlerboy/systemsmap.

Build with `npm run build`. The collector source preserved in this repository is historical; continue collector work in the maintained GitHub systemsmap repository.

## Legacy PSTA redirect

The user authorised retirement of publicservicetransformation.com on 5 September 2026. Requests on its apex and www host redirect to https://www.publicservicetransformation.org/, preserving paths and queries. DNS cutover and old-host cancellation must follow a verified file/database archive and dependency review. The legacy hosting panel recorded a malware finding on its 28 December 2025 scan; preserve its export as quarantine material and never deploy its executable files as part of this clean redirect.

## Anonymous event submissions

`POST /api/submissions` accepts a public URL and optional event details without authentication. D1 stores the receipt before the response reports success. The public `GET /api/submissions` endpoint supplies the community review queue, excluding the daily rate-limit hash. No submitted link is fetched by this Worker; the maintained GitHub collector performs bounded extraction and human review before event publication.

Schema lives in `db/schema.ts`; generated migrations live in `drizzle/`. Run `npm run db:generate` after schema changes, `npm test`, and the existing build command before publication. This service remains the existing Sites project; its root and legacy PSTA routing are preserved.
