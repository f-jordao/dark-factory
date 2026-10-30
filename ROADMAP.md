# Next milestones

## 0. Resolve the lifecycle UI gap

Fabro's authenticated run UI works, but the installed stable server's workflow
catalog returns HTTP 501. Inspection of `v0.400.0-nightly.0` finds the same
unimplemented real-mode catalog routes. An upgrade has not been validated
as a fix. Kiro is connected through generic ACP, not a named settings integration.

- Decide the lifecycle control surface before expanding worker flows. A small
  Dark Factory console could show registered flows, deterministic PR readiness,
  saved results and human decisions, with links to Fabro worker runs.
- Show which stages are implemented and which are design-only.
- Keep readiness checks, scheduling and status refresh free of model calls.
- Complete the PR review path before adding feature implementation workflows.

## 1. Finish the GitHub PR pilot

Completed: project-local Fabro runtime, native Kiro ACP with existing login,
known-defect and clean fixture reviews, validated JSON output, duplicate
suppression, permission denial, cancellation check, runtime restart and the
authenticated Fabro web UI.

- Resolve the GitHub-hosted CI account blocker or supply a configured runner.
- Review a real controlled PR after its required checks are green.
- Inspect its findings, then exercise COMMENT publication and recovery.
- Verify native Kiro cancellation under the actual managed launcher.

## 2. Connect GitHub events and durable scheduling

- A deterministic dispatcher handles PR readiness, new commits, completed checks
  and closure events; an external scheduler runs reconciliation for recovery.
- Use a persistent worker store; GitHub-hosted runner disks are not durable.
- Validate webhook signatures and allowlist repositories.
- Keep unchanged, ineligible and terminal states quiet.
- Add rate-limit handling, metrics and alerting without using agents.

## 3. Make demand routing and human gates executable

- Represent bugs, features, maintenance, security, incidents and discovery.
- Record blast-radius evidence separately from the demand category.
- Route sensitive or incomplete cases to humans.
- Persist approval identity, scope and revision; invalidate approval on changes.
- Map approved stages to selected Matt Pocock skills and Fabro workers.

## 4. Enforce merge readiness and broaden review context

- Configure GitHub rulesets, required checks and code-owner reviews.
- Resolve linked requirements and standards at immutable revisions.
- Provide workers with read-only repository snapshots and no publication credential.
- Show demand-routing state and human decisions alongside Fabro's worker UI.
- Add implementation and verification flows after the review slice is validated.

Automatic merge is outside the initial pilot.
