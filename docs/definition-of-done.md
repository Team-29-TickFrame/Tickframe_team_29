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

Additional team rules:

- A Sprint-selected PBI must be ready before work starts: clear outcome, context,
  acceptance criteria, estimate, implementer, and different reviewer.
- Bugs are not `Done` until the fix is verified in the target environment.
- Documentation PBIs are not `Done` until their links are live and checked.
- Release PBIs are not `Done` until the release tag, mapped milestone, and
  linked evidence are all available.
