# 0001: Deterministic lifecycle control, explicit agent workers

Status: accepted for the initial pilot.

## Problem

Using a general agent to watch GitHub consumes model calls when nothing has
changed and makes retry, waiting and approval behavior difficult to inspect.
The owner wants agents to perform substantive work while scripts manage the
software lifecycle.

## Decision

Start with a standard-library Python controller and durable SQLite state.
Use GitHub CLI authentication for repository inspection and publication.
Invoke a configurable command only after a PR is ready, its configured checks
are green, and its exact revision has not already been reviewed.

The first command adapter invokes one Fabro ACP review stage using Kiro CLI.
Fabro is the worker execution engine; the controller owns eligibility,
deduplication, publication and monitoring state. A later application can expose
the controller and workflow state visually.

Agent execution and publication are independently enabled. Publication always
uses COMMENT. Merge remains a GitHub-enforced human-governed step in the pilot.

## Consequences

Idle monitoring, retries of posting and terminal-state handling use no LLM.
SQLite claims prevent concurrent controller processes from repeating a review.
The deployment must preserve the state database; copying the controller into
fresh scheduled runners would lose that guarantee.

The local Fabro adapter runs on the same machine as the controller. Authenticated
Kiro ACP has been exercised with known-defect and clean packets. A deterministic
ACP fixture confirmed server cancellation and worker termination.

Each attempt uses its own workspace and copies a canonical tool-denial profile
from outside `.kiro`. The native ACP agent mode is selected explicitly before
prompting. The controller writes the final response and checks exact revision
and diff anchors. Workflow and worker artifacts join the prompt in the policy
digest.

Production worker isolation, native managed-launcher cancellation and a real
green-check GitHub PR with COMMENT publication remain required milestones before
continuous operation.
