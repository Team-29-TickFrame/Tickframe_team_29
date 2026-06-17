# Tickframe MVP v0

Tickframe MVP v0 is a static web prototype/foundation for a crypto market pattern analytics product. It demonstrates mock authentication, a BTC/USDT dashboard, generated candlestick data, timeframe controls, user-scoped alerts, alert creation, and alert deletion.

## MVP v0 Links

- Week 2 index: [reports/week2/README.md](reports/week2/README.md)
- MVP v0 report: [reports/week2/mvp-v0-report.md](reports/week2/mvp-v0-report.md)

## Local Setup


Run from the repository root:

```bash
python -m http.server 4173
```

Open:

```text
http://localhost:4173
```

Demo account:

```text
Email: demo@tickframe.local
Password: demo123
```

 `Continue as Guest` also can be used. Alerts are stored separately for the demo user and guest user in browser `localStorage`.

## Deploy on a VM

For MVP v0, the app can be served as a static site from a virtual machine.

### Quick Deployment

1. Copy or clone this repository onto the VM.
2. Open the project folder:

```bash
cd /path/to/tickframe
```

3. Start the static server:

```bash
python -m http.server 4173 --bind 0.0.0.0
```

4. Open TCP port `4173` in the VM firewall or cloud security group.
5. Visit:

```text
http://YOUR_SERVER_IP:4173
```
