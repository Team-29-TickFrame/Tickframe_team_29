# Contributing to Tickframe

## Scope

This repository uses issue-driven, milestone-driven delivery.  
Contributions should be linked to a GitHub issue and aligned with current Sprint scope.

## Workflow

1. Create or pick a linked issue.
2. Create a feature branch from `main` (`<issue>-<short-description>`).
3. Make focused changes and keep public/private evidence boundaries safe.
4. Open a PR using `.github/pull_request_template.md`.
5. Include issue linkage (`Closes #...` or `Supports #...`) and testing notes.
6. Request review from at least one teammate.
7. Merge only after review approval and required checks pass.

## Documentation updates

When behavior, setup, access, deployment, or process changes:
- update `README.md` entry points;
- update relevant docs under `docs/`;
- update weekly report indexes under `reports/week*/README.md` where needed.

## Security and privacy

- Never commit `.env`, secrets, private credentials, or customer-identifying private evidence.
- Keep private recordings/timecodes/instructions out of the public repository.
- Use `.env.example` for safe configuration examples only.
