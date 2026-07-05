This document lists every link excluded from automated Lychee checking.

Do not broadly exclude all external links. Exclusions must be narrow and justified.

| Link or pattern | Reason for exclusion | Manual verification performed | Verified by | Date |
| --- | --- | --- | --- | --- |
| `^https?://(127\\.0\\.0\\.1\|localhost)(:[0-9]+)?(/.*)?$` | Local development HTTP URLs are only available when the product is running on the developer machine or deployment host, so CI cannot verify them reliably. | Verify the local endpoints after starting the stack with `docker compose up -d --build`. | Team 29 | 2026-06-27 |
| `^wss?://(127\\.0\\.0\\.1\|localhost)(:[0-9]+)?(/.*)?$` | Local development WebSocket URLs are only available when the backend is running locally, so CI cannot verify them reliably. | Verify the local WebSocket endpoints after starting the stack with `docker compose up -d --build`. | Team 29 | 2026-06-27 |
| `^https://team-29-tickframe\\.github\\.io/Tickframe_team_29(/.*)?$` | The GitHub Pages site is created by the documentation deployment workflow after the change reaches `main`; PR link checks may run before the first deployment exists. | Verify the hosted documentation URL after the `Documentation Site` workflow deploys from `main`. | Team 29 | 2026-07-01 |
| `exclude_path = ["(^|/)node_modules/"]` | Third-party package README files under generated dependency folders are not maintained repository documentation and can contain package-registry, badge, or relative links outside the project scope. | Local Lychee v0.23.0 run first failed only in `frontend/node_modules`; the path exclusion keeps repository Markdown in scope while removing generated dependency noise. | z1nnyy | 2026-06-28 |
