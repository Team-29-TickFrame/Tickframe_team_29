# Process and Configuration Management

The Sprint 3 workflow uses issue templates, milestone planning, feature
branches, pull requests, reviewer approval, CI checks, and protected-branch
merge discipline. Runtime configuration is documented through safe examples;
real secrets are never committed.

## Maintained Workflow

1. Create or refine an issue with acceptance criteria, estimate, labels,
   assignee, milestone, and reviewer expectations.
2. Implement focused work in a traceable branch.
3. Open an issue-linked pull request.
4. Wait for review and required checks.
5. Merge through the protected default branch after evidence is available.

## Configuration Boundary

- `.env.example` documents safe local configuration names.
- `.env` and `.env.*` remain private except allowed examples.
- Private deployment credentials, recording links, and customer-identifying
  evidence are kept out of the public repository.

## Key Source Documents

- [Development process](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/development-process.md)
- [Definition of Done](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/docs/definition-of-done.md)
- [Pull request template](https://github.com/Team-29-TickFrame/Tickframe_team_29/blob/main/.github/pull_request_template.md)
- [Issue templates](https://github.com/Team-29-TickFrame/Tickframe_team_29/tree/main/.github/ISSUE_TEMPLATE)
