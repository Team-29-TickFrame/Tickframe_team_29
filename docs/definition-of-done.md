# Definition of Done

## Purpose

This Definition of Done (DoD) defines the minimum completion standard for all Product Backlog Items (PBIs) in the Tickframe project.

A PBI may be marked Done only when:

1. All issue-specific acceptance criteria are satisfied.
2. All requirements in this Definition of Done are satisfied.

## Requirements

### Acceptance Criteria

- All acceptance criteria defined in the issue are satisfied.
- Acceptance criteria have been verified and documented through normal workflow artifacts (issue comments, pull requests, screenshots, tests, demonstrations, or equivalent evidence).

### Implementation

- The planned implementation is complete.
- The implementation satisfies the scope described in the issue.
- No known critical defects remain.

### Testing and Verification

- Required tests, checks, or validation activities have been completed.
- Test or verification results indicate that the implemented functionality behaves as expected.
- Verification evidence is preserved in repository workflow artifacts.

### Review

- The work has been reviewed by at least one other team member.
- Review comments have been addressed.
- The issue-linked Pull Request has been approved.

### Traceability

- The issue is linked to the corresponding branch and Pull Request.
- Commits, Pull Requests, and issues maintain traceability.
- For user stories, all linked supporting PBIs required to satisfy the story are completed and provide implementation, review, and verification evidence.

### Documentation

- Relevant project documentation has been updated.
- User-facing changes are recorded in CHANGELOG.md following the project changelog workflow.
- README instructions remain accurate if affected by the change.

### Repository Workflow

- The Pull Request is linked to the relevant issue.
- Acceptance criteria have been explicitly verified before merge.
- The Pull Request follows the repository workflow requirements.
- The Pull Request has been merged into the protected default branch using the approved merge workflow.

### Sprint Completion

- The Product Owner (or delegated team representative) accepts the completed work.
- The issue Work Status has been updated to Done.
- The PBI satisfies any Sprint Goal commitments associated with the current Sprint.

## User Stories

### A User Story may be marked Done only when:

- The User Story acceptance criteria are satisfied.
- All supporting PBIs required for implementation, testing, review, and verification are completed.
- The User Story can be demonstrated as working within the delivered product increment.

## Supporting PBIs

### A supporting PBI may be marked Done only when:

- Its acceptance criteria are satisfied.
- The related implementation or documentation is completed.
- The issue-linked Pull Request is approved and merged into the protected default branch.

## Exclusions

Work must not be marked Done if:

- Acceptance criteria are incomplete.
- Review is missing.
- Required verification evidence is missing.
- Required documentation updates are missing.
- The Pull Request has not been merged.
