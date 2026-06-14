# Tickframe

Tickframe MVP v0 is a static desktop web foundation for demonstrating
cryptocurrency pattern analytics, navigation, and user-scoped mock alerts.

## Assignment 2

- [Week 2 submission index](reports/week2/README.md)
- [MVP v0 report and smoke check](reports/week2/mvp-v0-report.md)
- [Public MVP v0 deployment](https://tickframe.h1n.ru/)

## Local setup

No package installation, API key, database, or `.env` file is required.

1. Clone the repository and enter its root directory.
2. Start a static HTTP server:

   ```bash
   python3 -m http.server 8000
   ```

3. Open <http://localhost:8000/>.
4. Sign in with the prefilled demo credentials or select `Continue as Guest`.

Opening `index.html` directly is not recommended. Using a local HTTP server
matches the hosted environment more closely.

## Security

Do not commit real credentials or personal data. Local `.env` files are
ignored, and `.env.example` contains no secrets.

## License

This project is licensed under the [MIT License](LICENSE).
