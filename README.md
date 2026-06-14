# Tickframe MVP v0

Tickframe MVP v0 is a static web prototype/foundation for a crypto market pattern analytics product. It demonstrates mock authentication, a BTC/USDT dashboard, generated candlestick data, timeframe controls, user-scoped alerts, alert creation, and alert deletion.

## MVP v0 Links

- Week 2 index: [reports/week2/README.md](reports/week2/README.md)
- MVP v0 report: [reports/week2/mvp-v0-report.md](reports/week2/mvp-v0-report.md)
- Deployment URL: <https://tickframe.h1n.ru/>
- Public demo video: [MP4 recording](reports/week2/mvp-v0-demo.mp4)

## Local Setup

No build step or third-party dependencies are required.

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

You can also use `Continue as Guest`. Alerts are stored separately for the demo user and guest user in browser `localStorage`.

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

This is acceptable for a simple MVP v0 demo, but it is not production-grade.

### More Reliable VM Deployment With systemd

Create a systemd service so the app restarts after VM reboot.

Create:

```bash
sudo nano /etc/systemd/system/tickframe.service
```

Use this content, replacing `/path/to/tickframe` with the real project path:

```ini
[Unit]
Description=Tickframe MVP v0 static server
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/tickframe
ExecStart=/usr/bin/python3 -m http.server 4173 --bind 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tickframe
sudo systemctl start tickframe
sudo systemctl status tickframe
```

Then open:

```text
http://YOUR_SERVER_IP:4173
```

### Recommended Public Deployment

For a cleaner public deployment, put Nginx in front of the static files and serve the app on port `80` or `443`. The Python server is fine for a course smoke check, but Nginx is more stable and easier to expose publicly.

## Environment

MVP v0 does not require secrets. See [.env.example](.env.example) for the future configuration shape. Never commit real `.env` files or credentials.
