# Bounded rework & escalation

Repair failed verification or review within scope; escalate after two attempts.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    context["Script: Collect failure and revision context"]
    budget["Script: Read bounded repair budget"]
    remaining{{"Condition: Repair budget remaining?"}}
    repair["Agent: Repair within approved scope"]
    count["Script: Persist completed repair attempt"]
    verify["Flow: Hand off to shared workflow"]
    passed{{"Condition: Verification passed?"}}
    reassess["Flow: Hand off to shared workflow"]
    review["Flow: Hand off to shared workflow"]
    escalate{"Human: Human decides after repair limit"}
    record["Script: Validate and record human decision"]
    new_demand["Script: Create a separate scoped demand"]
    stopped["Script: Record stopped demand"]
    start --> context
    context --> budget
    budget --> remaining
    remaining -->|"Budget available"| repair
    remaining -->|"Exhausted / unknown"| escalate
    repair --> count
    count --> verify
    verify --> passed
    passed -->|"Passed"| reassess
    passed -->|"Failed / missing evidence"| budget
    reassess --> review
    review --> exit
    escalate -->|"[A] Authorize a separate scoped demand"| record
    escalate -->|"[S] Stop"| stopped
    record --> new_demand
    new_demand --> exit
    stopped --> exit
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Collect failure and revision context | script | Implementation / decision packet pending |
| Read bounded repair budget | script | Implementation / decision packet pending |
| Repair budget remaining? | condition | Implementation / decision packet pending |
| Repair within approved scope | agent | [Prompt](../../stages/repair/prompt.md); candidate skill `implement` |
| Persist completed repair attempt | script | Implementation / decision packet pending |
| Hand off to shared workflow | handoff | [Shared flow](../verification/README.md); dispatch binding pending |
| Verification passed? | condition | Implementation / decision packet pending |
| Hand off to shared workflow | handoff | [Shared flow](../diff-reassessment/README.md); dispatch binding pending |
| Hand off to shared workflow | handoff | [Shared flow](../pr-review-lifecycle/README.md); dispatch binding pending |
| Human decides after repair limit | human | Implementation / decision packet pending |
| Validate and record human decision | script | Implementation / decision packet pending |
| Create a separate scoped demand | script | Implementation / decision packet pending |
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
