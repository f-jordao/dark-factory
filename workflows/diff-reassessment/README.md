# Actual-diff reassessment

Reassess impact and invalidate stale or expanded-scope approvals.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    diff["Script: Collect exact implementation diff"]
    impact["Agent: Explain reach and uncertainty"]
    policy["Script: Apply deterministic routing policy"]
    current{{"Condition: Actual diff within approved scope?"}}
    invalidate["Script: Invalidate approvals for changed scope"]
    approve_scope{"Human: Confirm scope and acceptance"}
    record["Script: Validate and record human decision"]
    revise["Agent: Plan bounded implementation"]
    save["Script: Persist actual-diff assessment"]
    stopped["Script: Record stopped demand"]
    start --> diff
    diff --> impact
    impact --> policy
    policy --> current
    current -->|"Current"| save
    current -->|"Broader / uncertain / stale"| invalidate
    invalidate --> approve_scope
    approve_scope -->|"[A] Approve revised scope"| record
    approve_scope -->|"[R] Revise"| revise
    approve_scope -->|"[S] Stop"| stopped
    revise --> approve_scope
    record --> save
    save --> exit
    stopped --> exit
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Collect exact implementation diff | script | Implementation / decision packet pending |
| Explain reach and uncertainty | agent | [Prompt](../../stages/analyze-impact/prompt.md) |
| Apply deterministic routing policy | script | Implementation / decision packet pending |
| Actual diff within approved scope? | condition | Implementation / decision packet pending |
| Invalidate approvals for changed scope | script | Implementation / decision packet pending |
| Confirm scope and acceptance | human | Implementation / decision packet pending |
| Validate and record human decision | script | Implementation / decision packet pending |
| Plan bounded implementation | agent | [Prompt](../../stages/plan/prompt.md); candidate skill `to-tickets` |
| Persist actual-diff assessment | script | Implementation / decision packet pending |
| Record stopped demand | script | Implementation / decision packet pending |

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
