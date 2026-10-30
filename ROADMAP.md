# Next milestones

## 1. Finish the GitHub PR pilot

Completed: project-local Fabro runtime, native Kiro ACP with existing login,
known-defect and clean fixture reviews, validated JSON output, duplicate
suppression, permission denial, cancellation check and runtime restart.

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
- Surface lifecycle state in a visual application.
- Add implementation and verification flows after the review slice is validated.

Automatic merge is outside the initial pilot.
