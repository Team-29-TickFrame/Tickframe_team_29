# Tickframe — Week 2 Submission

Tickframe MVP v0 is a static desktop web foundation for demonstrating
cryptocurrency pattern analytics, navigation, and user-scoped mock alerts.

## MVP v0

- [MVP v0 report, access instructions, and smoke check](./mvp-v0-report.md)
- Public MVP v0 deployment: <https://tickframe.h1n.ru/>
- [Open or download the public MVP v0 video (MP4)](./mvp-v0-demo.mp4?raw=true) — 1 minute 11 seconds

The video uses browser-compatible H.264 in an MP4 container. If GitHub shows a
download button instead of an embedded player, download the file and open it
with any modern browser or media player.

The deployment is publicly accessible without authentication to the hosting
control panel or private network access.

## Prototype (MVP v1)

- [Figma prototype (view-only)](https://www.figma.com/design/rHG9DGjIeDPResDNlMZrXn/Tickframe?node-id=0-1&t=ecf4MuhdmOd0OgEG-1)

## Requirements and analysis

- [User stories and priorities](./user-stories.md)
- [Week 2 analysis](./analysis.md)
- [LLM usage report](./llm-report.md)

## Repository workflow (Week 2)

- [PR/MR template](../../.github/PULL_REQUEST_TEMPLATE.md)
- [Reviewed PR #1](https://github.com/IvanGuzhov822/Tickframe_team_29/pull/1) (reviewed by kristina19-gif)

## Lychee link checking

- **Configuration:** [lychee.toml](../../lychee.toml) and [.github/workflows/links.yml](../../.github/workflows/links.yml)
- **Latest run on main:** https://github.com/IvanGuzhov822/Tickframe_team_29/actions/runs/27511430738

### Excluded Lychee links

See [docs/link-check-exclusions.md](../../docs/link-check-exclusions.md). No links excluded; manual verification not required.

## Local setup

No package installation, API key, or `.env` file is required.

1. Clone the repository and enter its root directory.
2. Start a static HTTP server:

   ```bash
   python3 -m http.server 8000
   ```

3. Open <http://localhost:8000/>.
4. Sign in with the built-in demo values shown on the page, or select
   `Continue as Guest`.

Opening `index.html` directly is not recommended. Use the local HTTP server so
the application runs in the same way as the hosted version.

## MVP v0 limitations

- Market prices and patterns are synthetic demonstration data.
- Authentication is a local demo and does not contact a backend.
- Alerts are stored in browser `localStorage`.
- The current MVP is intended for desktop web browsers.

## Security

Do not commit real credentials or personal data. Local `.env` files are
ignored, and [`.env.example`](../../.env.example) contains no secrets.

## Customer meeting

- [Customer meeting summary](./customer-meeting-summary.md)
- [Customer meeting transcript](./customer-meeting-transcript.md)
- Customer recording (instructors only): https://drive.google.com/drive/folders/1jT2cU4qXRnMtETrT1zOa5YaIwojFPqNk?usp=drive_link
- MIT consent: obtained via Telegram before repository creation (evidence in Moodle PDF)

## License

This project is licensed under the [MIT License](../../LICENSE).
