# Development Process and Configuration Management

## Purpose

This document describes the actual Tickframe team workflow used in Sprint 3 for Assignment 5, including backlog usage, Git/PR process, CI, runtime configuration, and secrets handling.

## Backlog and Sprint workflow

- Product Backlog view: https://github.com/orgs/Team-29-TickFrame/projects/1
- Sprint Backlog (Sprint 3 milestone): https://github.com/Team-29-TickFrame/Tickframe_team_29/milestone/3
- MVP v2 filtered issues: https://github.com/Team-29-TickFrame/Tickframe_team_29/issues?q=is%3Aissue%20label%3Amvp-v2

Workflow states used in practice:
- Issue is created from templates in `.github/ISSUE_TEMPLATE/`.
- Issue is refined, estimated (Story Points), labeled, and assigned to milestone.
- Work is done in a feature branch linked to the issue.
- PR is opened with issue reference and acceptance-criteria check.
- After review approval and CI pass, PR is merged to protected `main`.
- Linked issue is closed after merge (automatic with `Closes #...` or manual close).

## Issue creation, branch naming, and PR workflow

- Issue templates:
  - `.github/ISSUE_TEMPLATE/other-pbi.yml`
  - `.github/ISSUE_TEMPLATE/course-task.yml`
  - `.github/ISSUE_TEMPLATE/user-story.yml`
  - `.github/ISSUE_TEMPLATE/bug-report.yml`
- PR template: `.github/pull_request_template.md`

Branch naming used by the team:
- `a5-p01-sprint3-roadmap`
- `a5-p02-customer-feedback-response`
- `<issue>-<short-description>` for traceable work branches

PR and merge rules used in practice:
- One focused change per PR where practical.
- Reviewer approval required from another team member.
- Author does not self-approve.
- No history rewrite for protected branch workflow.
- Merge only after checks pass and checklist items are satisfied.

## CI and quality gates

Maintained CI workflows:
- `.github/workflows/quality.yml`
- `.github/workflows/links.yml`

CI is used to keep docs/code quality and link health inspectable before merge.

## Configuration and secrets management

- Runtime config template: `.env.example`
- Local secret file: `.env` (never committed)
- Ignore rules: `.gitignore` contains:
  - `.env`
  - `.env.*`
  - `!.env.example`
  - plus local/dev artifacts

Secrets handling policy:
- Real credentials, private deployment secrets, and private access details are never committed.
- Public repository stores only safe examples and non-sensitive defaults.
- Private credentials are stored only in private team channels / private submission context.

## Runtime and deployment configuration

- Local/dev and deployment entry point: `docker-compose.yml`
- Product run/deploy guidance: `README.md` sections "Run the Complete Product" and "Deployment"

## Git workflow used by the team

```mermaid
gitGraph
  commit id: "main"
  branch feature/a5-p03
  checkout feature/a5-p03
  commit id: "docs update"
  commit id: "review fixes"
  checkout main
  merge feature/a5-p03
  commit id: "post-merge sync"
  ```
