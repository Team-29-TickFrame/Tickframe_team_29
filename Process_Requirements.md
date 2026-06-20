# Process Requirements

## Product Backlog

The Product Backlog is maintained through GitHub Issues and Projects. Each qualifying PBI must have a clear title, description, type, priority, work status, and story point estimate where required.

PBI types:
- User Story
- Other PBI
- Course Task
- Bug Report

Course administration tasks do not count toward the required 15 Product Backlog PBIs.

## Requirement Status

Requirement status values:
- Active — the requirement is part of the current product scope.
- Removed — the requirement is no longer part of the product scope, but its stable ID and history are preserved.

Removed requirements must not be deleted from traceability documentation.

## Work Status

Work status values:
- To Do — work has not started.
- In Progress — work has started.
- In Review — work is implemented and waiting for review or verification.
- Done — work satisfies acceptance criteria, review, testing, and Definition of Done.
- Blocked — work cannot proceed until a dependency or decision is resolved.

## Prioritization

MoSCoW priority values:
- Must Have
- Should Have
- Could Have
- Won't Have

MVP v1 scope is selected from Must Have user stories and required supporting PBIs.

## Acceptance Criteria

PBIs selected for MVP v1 or the current Sprint must have acceptance criteria before being treated as Ready.

Acceptance criteria should be:
- testable,
- specific,
- written from the user or product perspective where applicable,
- verified before the PBI is marked Done.

## Estimation

Story points are used to estimate qualifying PBIs. Final estimates are recorded on backlog items and summarized in the Week 3 report.

## Sprint Planning

The current Sprint is represented by a GitHub milestone. The Sprint milestone contains the Sprint Goal, Sprint dates, and selected Sprint Backlog items.

MVP version is tracked separately using a label or project field such as `mvp-v1`.

## Pull Request Workflow

Every implementation or documentation change should be made through an issue-linked branch and pull request.

Branch naming format:

```text
<issue-number>-short-description
