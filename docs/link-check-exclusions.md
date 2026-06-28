This document lists every link excluded from automated Lychee checking.

Do not broadly exclude all external links. Exclusions must be narrow and justified.

| Link or pattern | Reason for exclusion | Manual verification performed | Verified by | Date |
| --- | --- | --- | --- | --- |
| `exclude_path = ["(^|/)node_modules/"]` | Third-party package README files under generated dependency folders are not maintained repository documentation and can contain package-registry, badge, or relative links outside the project scope. | Local Lychee v0.23.0 run first failed only in `frontend/node_modules`; the path exclusion keeps repository Markdown in scope while removing generated dependency noise. | z1nnyy | 2026-06-28 |
| `exclude_loopback = true` for `http://127.0.0.1:*` and `http://localhost:*` | Local frontend, API, Prometheus, and Grafana demo links only resolve when the Tickframe development stack is running; CI should not require those services. | Confirmed the latest `Links` workflow run excluded only loopback URLs and still checked public external links: <https://github.com/Team-29-TickFrame/Tickframe_team_29/actions/runs/28324067011>. | z1nnyy | 2026-06-28 |
