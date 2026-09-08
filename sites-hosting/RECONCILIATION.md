# Sites hosting reconciliation, 8 September 2026

This directory preserves the complete deployed Sites source at commit `97d1a162994ff7abdd2104e5cb8682ebd74b9391`. The repository's existing collector, data, and workflows remain authoritative and unchanged at the root.

The Site is still required: it handles the configured domain redirects, including events.transduction.systems, and a database-backed anonymous event submission service. The main public events interface is at https://transduction.systems/events/.

The live `event_submissions` table is backed up separately and privately. Do not commit the database export, client hashes, or private moderation data to this public repository. Two submissions were present during reconciliation.

Source storage is not a host migration. Retain the Site and its D1 database until both redirects and submissions have a verified replacement. Original hosting identity is preserved in `.openai/hosting.json`.
