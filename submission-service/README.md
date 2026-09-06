# Anonymous event submission service

This is the GitHub source backup of the existing Sites Worker at `https://events.transduction.systems`. Its `.openai/hosting.json` identifies that existing project. The authoritative deployed source commit is `97d1a162994ff7abdd2104e5cb8682ebd74b9391` in its Sites source repository.

The service accepts public URLs into a durable D1 inbox, exposes the public queue without rate-limit metadata, and preserves the existing canonical event and legacy PSTA redirects. The main systemsmap collector extracts the queued links for human review. No visitor sign-in or email address is required.

Run `npm ci`, `npm test`, and `npm run build` to validate the service. Use the Sites skill and the existing project identity to publish. Generated, applied Drizzle migrations must remain immutable.
