# MVP v0 Report

## Purpose and description

Tickframe MVP v0 is a runnable static desktop web foundation for a future cryptocurrency pattern analytics product. It demonstrates the intended visual direction, primary navigation, a synthetic BTC/USDT dashboard, and a mock alert
workflow without requiring a production backend.

The application supports demo sign-in or guest access. A user can move between the Dashboard, Alerts, and Create Alert screens create an alert, and see the new alert saved for that browser profile.

## Access

- **Deployment URL:** <https://tickframe.h1n.ru/>

## Public video demonstration

[Open or download the MVP v0 video demonstration (MP4)](./mvp-v0-demo.mp4?raw=true) — 1 minute 11 seconds.

The recording is located in the folder reports/week2

## Relationship to the prototype and proposed MVP v1

MVP v0 turns the desktop web direction discussed with the customer into a runnable technical foundation. The demo sign-in flow relates to `US-01`, while the dashboard, chart, pattern panel, metrics, and signal feed establish an interface foundation for `US-03` through `US-07.

## Current limitations, placeholders, and mocks

- BTC/USDT prices, candles, indicators, confidence values, and patterns are not real.
- Alerts are saved to browser `localStorage`; there is no database.
- Email and SMS options are labels only and do not send notifications.
- Only BTC/USDT is available in MVP v0.


## Local setup

See the [root README local setup instructions](../../README.md#local-setup).

## Repeatable smoke-check scenario


1. Confirm that the `TICKFRAME` sign-in page is visible.
2. Keep the prefilled demo email `demo@tickframe.local` and password
   `demo123`, then select `Sign In`.
3. Confirm that the Dashboard opens.
   **Expected:** the sidebar contains `Dashboard`, `Alerts`, and `Create Alert`;
   the BTC/USDT chart and pattern panel are visible.
4. Select `Create Alert` in the sidebar.
   **Expected:** the `Create New Alert` form opens.
5. Keep `Pattern Detected`, set `Confidence Rate` to `85%`, and keep or choose the parameters of the alert
   `In-App Notification` selected.
5. Select `Create Alert`.
   **Expected:** a `Success!` page states that the alert was created and saved.
6. Reload the page.
   **Expected:** the user remains signed in and the new alert remains visible
   because the mock state is stored in browser `localStorage`.
