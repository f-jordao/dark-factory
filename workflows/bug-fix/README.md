# Bug fix

Reproduce, diagnose, plan a regression and implement a scoped fix.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    validate["Script: Validate demand and immutable inputs"]
    scope_known{{"Condition: Expected behavior and scope clear?"}}
    clarify_scope{"Human: Confirm scope and acceptance"}
    record_scope["Script: Validate and record human decision"]
    needs_info["Script: Record clarification needed"]
    reproduce["Agent: Reproduce reported failure"]
    diagnose["Agent: Diagnose root cause"]
    regression["Agent: Design regression evidence"]
    plan["Agent: Plan bounded implementation"]
    plan_gate{{"Condition: Plan approval required?"}}
    approve_plan{"Human: Approve approach and plan"}
    record_plan["Script: Validate and record human decision"]
    implement["Agent: Implement approved change"]
    verification["Flow: Verify change"]
    checks_passed{{"Condition: Verification passed?"}}
    reassess["Flow: Reassess actual diff"]
    scope_current{{"Condition: Actual diff within approved scope?"}}
    renew_scope{"Human: Renew approval for expanded scope"}
    record_renewal["Script: Validate and record human decision"]
    review["Flow: Independent PR review"]
    review_clear{{"Condition: Independent review clear?"}}
    merge_readiness["Flow: Final approvals and GitHub merge readiness"]
    rework["Flow: Bounded repair / human escalation"]
    stopped["Script: Record stopped demand"]
    prepare_branch["Script: Prepare isolated branch and workspace"]
    prepare_pr["Flow: Prepare and optionally publish draft PR"]
    pr_available{{"Condition: PR exists and is ready for lifecycle tracking?"}}
    waiting_pr["Script: Save PR proposal without publication"]
    start --> validate
    validate --> scope_known
    scope_known -->|"Clear"| reproduce
    scope_known -->|"Ambiguous / missing"| clarify_scope
    clarify_scope -->|"[A] Confirm expected behavior"| record_scope
    clarify_scope -->|"[R] Clarify"| needs_info
    clarify_scope -->|"[S] Stop"| stopped
    record_scope --> reproduce
    needs_info --> exit
    reproduce --> diagnose
    diagnose --> regression
    regression --> plan
    plan --> plan_gate
    approve_plan -->|"[A] Approve"| record_plan
    approve_plan -->|"[R] Revise"| plan
    approve_plan -->|"[S] Stop"| stopped
    record_plan --> prepare_branch
    plan_gate -->|"Approval not required"| prepare_branch
    plan_gate -->|"Approval required / unknown"| approve_plan
    implement --> verification
    verification --> checks_passed
    checks_passed -->|"Passed"| reassess
    checks_passed -->|"Failed / missing evidence"| rework
    reassess --> scope_current
    scope_current -->|"Scope current"| prepare_pr
    scope_current -->|"Broader / uncertain"| renew_scope
    renew_scope -->|"[A] Approve revised scope"| record_renewal
    renew_scope -->|"[R] Revise"| rework
    renew_scope -->|"[S] Stop"| stopped
    record_renewal --> reassess
    review --> review_clear
    review_clear -->|"Clear"| merge_readiness
    review_clear -->|"Findings / missing review"| rework
    merge_readiness --> exit
    rework --> exit
    stopped --> exit
    prepare_branch --> implement
    prepare_pr --> pr_available
    pr_available -->|"PR available"| review
    pr_available -->|"Proposal saved / publication disabled"| waiting_pr
    waiting_pr --> exit
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Validate demand and immutable inputs | script | Implementation / decision packet pending |
| Expected behavior and scope clear? | condition | Implementation / decision packet pending |
| Confirm scope and acceptance | human | Implementation / decision packet pending |
| Validate and record human decision | script | Implementation / decision packet pending |
| Record clarification needed | script | Implementation / decision packet pending |
| Reproduce reported failure | agent | [Prompt](../../stages/reproduce/prompt.md); candidate skill `diagnosing-bugs` |
| Diagnose root cause | agent | [Prompt](../../stages/diagnose/prompt.md); candidate skill `diagnosing-bugs` |
| Design regression evidence | agent | [Prompt](../../stages/regression-design/prompt.md); candidate skill `diagnosing-bugs` |
| Plan bounded implementation | agent | [Prompt](../../stages/plan/prompt.md); candidate skill `to-tickets` |
| Plan approval required? | condition | Implementation / decision packet pending |
| Approve approach and plan | human | Implementation / decision packet pending |
| Validate and record human decision | script | Implementation / decision packet pending |
| Implement approved change | agent | [Prompt](../../stages/implement/prompt.md); candidate skill `implement` |
| Verify change | handoff | [Shared flow](../verification/README.md); dispatch binding pending |
| Verification passed? | condition | Implementation / decision packet pending |
| Reassess actual diff | handoff | [Shared flow](../diff-reassessment/README.md); dispatch binding pending |
| Actual diff within approved scope? | condition | Implementation / decision packet pending |
| Renew approval for expanded scope | human | Implementation / decision packet pending |
| Validate and record human decision | script | Implementation / decision packet pending |
| Independent PR review | handoff | [Shared flow](../pr-review-lifecycle/README.md); dispatch binding pending |
| Independent review clear? | condition | Implementation / decision packet pending |
| Final approvals and GitHub merge readiness | handoff | [Shared flow](../merge-readiness/README.md); dispatch binding pending |
| Bounded repair / human escalation | handoff | [Shared flow](../rework/README.md); dispatch binding pending |
| Record stopped demand | script | Implementation / decision packet pending |
| Prepare isolated branch and workspace | script | Implementation / decision packet pending |
| Prepare and optionally publish draft PR | handoff | [Shared flow](../pr-preparation/README.md); dispatch binding pending |
| PR exists and is ready for lifecycle tracking? | condition | Implementation / decision packet pending |
| Save PR proposal without publication | script | Implementation / decision packet pending |

Human approval records bind actor and roles to the demand, repository,
head, base, artifact digest, scope digest and policy version. A native
Fabro choice alone does not enforce those records or roles. Records
also identify the workflow, stage and target branch.

Repair is limited to two attempts; exhausted or unknown budgets require
a human decision. No automatic merge is defined.

Edit `definition.json` for structure and `../../stages/catalog.json`
for shared stage slots. Rebuild derived files with:

```bash
python3 -m dark_factory workflows build
```
