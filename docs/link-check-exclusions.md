This document lists every link excluded from automated Lychee checking.

Do not broadly exclude all external links. Exclusions must be narrow and justified.

| Link or pattern | Reason for exclusion | Manual verification performed | Verified by | Date |
| --- | --- | --- | --- | --- |
| `^https?://(127\\.0\\.0\\.1\|localhost)(:[0-9]+)?(/.*)?$` | Local development HTTP URLs are only available when the product is running on the developer machine or deployment host, so CI cannot verify them reliably. | Verify the local endpoints after starting the stack with `docker compose up -d --build`. | Team 29 | 2026-06-27 |
| `^wss?://(127\\.0\\.0\\.1\|localhost)(:[0-9]+)?(/.*)?$` | Local development WebSocket URLs are only available when the backend is running locally, so CI cannot verify them reliably. | Verify the local WebSocket endpoints after starting the stack with `docker compose up -d --build`. | Team 29 | 2026-06-27 |
