# Definition of Done

Tickframe work may be marked `Done` only when all of the following are true:

1. The issue acceptance criteria are satisfied.
2. Another team member has reviewed the work.
3. Required tests or checks have passed.
4. Verification evidence is preserved in the normal workflow artifacts.
5. The change is merged into the protected default branch through the issue-linked PR or MR.
6. The root `CHANGELOG.md` is updated for every user-visible change.
7. Any relevant documentation, deployment instructions, or release notes are updated.
8. For user stories, all supporting PBIs required to satisfy the story acceptance criteria are also completed, reviewed, verified, and marked `Done`.
9. The result is usable in the current product context and does not leave known regression risks unaddressed.
10. All required CI quality gates have passed before merge, including linting, formatting or type checking, build verification, automated tests, coverage checks, automated Quality Requirement Tests (QRTs), and additional QA checks.
11. Relevant automated unit tests and integration tests have passed for the affected product components.
12. Relevant automated Quality Requirement Tests defined in docs/quality-requirement-tests.md have passed, or their non-applicability has been explicitly documented.
13. Critical product modules satisfy the required minimum automated line coverage threshold of 30%.
14. Testing and verification evidence is preserved in issue-linked pull requests, GitHub Actions CI runs, coverage reports, release artifacts, or linked documentation.
15. Relevant quality requirements defined in docs/quality-requirements.md are satisfied.
16. All required CI checks for the repository technology stack have passed, including:
    * backend linting (ruff check backend ml);
    * backend formatting checks (ruff format --check backend ml);
    * frontend TypeScript type checking (npm run typecheck);
    * frontend build verification (npm run build);
    * backend automated tests and coverage checks;
    * automated Quality Requirement Tests;
    * critical-module coverage validation;
    * additional QA checks, including Ruff datetime-safety check.

Additional team rules:

- A Sprint-selected PBI must be ready before work starts: clear outcome, context,
  acceptance criteria, estimate, implementer, and different reviewer.
- Bugs are not `Done` until the fix is verified in the target environment.
- Documentation PBIs are not `Done` until their links are live and checked.
- Release PBIs are not `Done` until the release tag, mapped milestone, and
  linked evidence are all available.
- Relevant documentation introduced in Assignment 4 must be updated when applicable, including:
    * docs/testing.md;
    * docs/quality-requirements.md;
    * docs/quality-requirement-tests.md;
    * docs/user-acceptance-tests.md.
- CI quality gates introduced in Assignment 4 remain active project requirements for future development and must not be disabled or bypassed after Assignment 4.
- If future project work changes the technology stack, quality requirements, critical modules, testing strategy, or CI configuration, this Definition of Done must be updated so that it continues to reflect the current project completion standard.
- The latest protected-default-branch CI run must pass before a release or assignment submission unless a documented exception has been approved.
