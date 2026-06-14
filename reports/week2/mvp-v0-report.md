# MVP v0 Report

## Purpose and description

Tickframe MVP v0 is a runnable static desktop web foundation for a future
cryptocurrency pattern analytics product. It demonstrates the intended visual
direction, primary navigation, a synthetic BTC/USDT dashboard, and a mock alert
workflow without requiring a production backend.

The application supports demo sign-in or guest access. A user can move between
the Dashboard, Alerts, and Create Alert screens, create an alert, and see the
new alert saved for that browser profile.

## Access

- **Deployment URL:** <https://tickframe.h1n.ru/>
- **Product type:** Desktop web application
- **Demo email:** `demo@tickframe.local`
- **Demo password:** `demo123`
- **Alternative access:** Select `Continue as Guest`

The demo values are built into the static application. They are not real,
personal, production, or third-party credentials.

The public deployment was verified on June 14, 2026. It returns the Tickframe
sign-in page without requiring access to the hosting control panel or a private
network.

## Public video demonstration

[MVP v0 video demonstration (MP4)](./mvp-v0-demo.mp4) — 1 minute 11 seconds.

The recording is encoded as H.264 video in a browser-compatible MP4 container.
If GitHub offers the file as a download instead of displaying an embedded
player, download it and open it in any modern browser or media player.

The recording shows only the public Tickframe application in an incognito
browser window. It contains no audio, real credentials, personal data, hosting
control panel, or confidential information.

## Relationship to the prototype and proposed MVP v1

MVP v0 turns the desktop web direction discussed with the customer into a
runnable technical foundation. The demo sign-in flow relates to `US-01`, while
the dashboard, chart, pattern panel, metrics, and signal feed establish an
interface foundation for `US-03` through `US-07`. The current implementation
uses synthetic data and mock behavior, so it demonstrates the intended
interaction model rather than completing those production user stories.

## Current limitations, placeholders, and mocks

- BTC/USDT prices, candles, indicators, confidence values, and patterns are
  synthetic.
- Demo authentication is implemented only in the browser.
- Alerts are saved to browser `localStorage`; there is no database.
- Email and SMS options are labels only and do not send notifications.
- Only BTC/USDT is available in MVP v0.
- The interface is desktop-focused and has not been packaged as a mobile app.

## Local setup

See the [root README local setup instructions](../../README.md#local-setup).

## Repeatable smoke-check scenario

### Goal

Confirm that the hosted MVP opens, primary navigation works, and the alert form
causes a visible state change that persists in the current browser profile.

### Access instructions

Use a desktop browser. A private/incognito window is recommended for a
repeatable initial state.

1. Open the public hosting URL listed in the `Access` section above.
2. Confirm that the `TICKFRAME` sign-in page is visible.
3. Keep the prefilled demo email `demo@tickframe.local` and password
   `demo123`, then select `Sign In`.

### Test steps and expected results

1. Confirm that the Dashboard opens.
   **Expected:** the sidebar contains `Dashboard`, `Alerts`, and `Create Alert`;
   the BTC/USDT chart and pattern panel are visible.
2. Select a different chart timeframe, such as `15m`.
   **Expected:** the selected timeframe becomes highlighted and the chart is
   redrawn.
3. Select `Create Alert` in the sidebar.
   **Expected:** the `Create New Alert` form opens.
4. Keep `Pattern Detected`, set `Confidence Rate` to `85%`, and keep
   `In-App Notification` selected.
5. Select `Create Alert`.
   **Expected:** a `Success!` page states that the alert was created and saved.
6. Select `Continue`.
   **Expected:** the Alerts page opens and contains an active BTC/USDT
   `Pattern Detected` alert with `Threshold 85%`.
7. Reload the page.
   **Expected:** the user remains signed in and the new alert remains visible
   because the mock state is stored in browser `localStorage`.

### Smoke-check coverage

- **Application access:** the hosted sign-in page opens.
- **Primary navigation:** Dashboard, Alerts, and Create Alert are reachable.
- **Interactive data flow:** submitting the form creates and stores a new alert.
- **Visible state change:** Success and Alerts screens confirm the result.

## Hosted availability

The MVP is deployed on shared hosting. The team must keep the hosting service
active, preserve public access to the deployment URL, and avoid changing or
removing the documented test access until the course has been graded.

## Mobile application requirement

Part 4, item 5 is **not applicable**. Tickframe MVP v0 is a desktop web
application, and the customer meeting records that desktop web is the selected
MVP platform while mobile may be considered later. The public hosting URL is
therefore the required access method; no mobile installable build or emulator
distribution is needed for this MVP.

## Moodle PDF access information

The Moodle PDF should include the following information:

- **MVP v0 URL:** <https://tickframe.h1n.ru/>
- **Access:** no hosting-panel account, SSH, VPN, or private network is needed.
- **Demo email:** `demo@tickframe.local`
- **Demo password:** `demo123`
- **Alternative access:** select `Continue as Guest`.
- **Smoke check:** [Repeatable smoke-check scenario](#repeatable-smoke-check-scenario)

The demo credentials are built-in placeholders and do not provide access to any
real account or third-party service.
