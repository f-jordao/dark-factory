# Next milestones

## 1. Workflow structure — complete

Six demand routes and seven shared flows now define the full lifecycle.
They include demand classification, blast-radius routing, human gates, isolated
implementation, verification, PR preparation, review, final acceptance and a
governed GitHub merge handoff. Discovery ends in a human decision.

The scaffold has 77 stage templates, 17 empty agent prompts, input/output slots,
record schemas and bounded rework. All 13 generated Fabro graphs validate.
Scaffolds block before any agent stage and remain disabled.
See [workflow setup](docs/workflows.md) for maps and content locations.

Fabro's native workflow catalog is unimplemented. Its Automations page can hold
disabled definitions without adding a schedule. Kiro remains a generic ACP
worker with a project adapter, not a named Fabro settings integration.

## 2. Fill stage content

- Select and pin the relevant Matt Pocock skills; preserve license and required
  human decisions.
- Fill substantive agent methods, input packets and result contracts.
- Add deterministic script implementations and trusted context bindings.
- Add human decision packets, role requirements and approval validators.
- Bind each agent stage to an appropriate worker profile and isolated environment.
- Wire shared flow handoffs and result/resumption handling.

Prompt content alone does not enable a workflow. Keep the guards and triggers
disabled until the route's execution and recovery behavior is exercised.

## 3. Implement durable lifecycle state and human gates

- Persist demand identity, category, evidence, risk and current revision.
- Record approver identity, roles, workflow/stage, branch, artifact and scope.
- Invalidate approvals when revision, scope or policy changes.
- Enforce repair budgets and human escalation.
- Keep merge authority in GitHub rulesets and human decisions.

## 4. Finish the real GitHub PR pilot

The existing PR-review controller and authenticated Kiro worker are exercised
with local fixtures. Hosted CI cannot start because GitHub reports an account
billing or spending-limit issue.

- Resolve that account blocker or supply a configured runner.
- Review a controlled PR after its required checks are green.
- Inspect findings, then exercise COMMENT publication and recovery.
- Verify cancellation under the actual managed Kiro launcher.

## 5. Connect deterministic triggers and scheduling

- Handle PR readiness, new commits, completed checks and closure events.
- Reconcile periodically for recovery, without model calls when no new work exists.
- Preserve the state store across runs; fresh runner disks are not durable.
- Validate webhook signatures and repository allowlists.
- Add rate-limit handling, metrics and actionable alerts.

No recurring trigger or automatic merge is enabled.
