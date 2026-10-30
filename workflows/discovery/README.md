# Discovery / investigation

Read-only investigation ends in a human go, clarify or stop decision.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    validate["Script: Validate demand and immutable inputs"]
    investigate["Agent: Investigate without changing code"]
    impact["Agent: Explain reach and uncertainty"]
    recommend["Agent: Produce findings and alternatives"]
    decision{"Human: Authorize new demand, clarify or stop"}
    record_decision["Script: Validate and record human decision"]
    new_demand["Script: Create a separate scoped demand"]
    stopped["Script: Record stopped demand"]
    start --> validate
    validate --> investigate
    investigate --> impact
    impact --> recommend
    recommend --> decision
    decision -->|"[A] Authorize a new scoped demand"| record_decision
    decision -->|"[R] Clarify"| investigate
    decision -->|"[S] Stop"| stopped
    record_decision --> new_demand
    new_demand --> exit
    stopped --> exit
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Validate demand and immutable inputs | script | Implementation / decision packet pending |
| Investigate without changing code | agent | [Prompt](../../stages/investigate/prompt.md) |
| Explain reach and uncertainty | agent | [Prompt](../../stages/analyze-impact/prompt.md) |
| Produce findings and alternatives | agent | [Prompt](../../stages/recommend/prompt.md) |
| Authorize new demand, clarify or stop | human | Implementation / decision packet pending |
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
