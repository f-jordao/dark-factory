# Demand intake & routing

Capture, classify, assess evidence and select a demand route.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    capture["Script: Capture demand"]
    classify["Script: Normalize demand type"]
    known{{"Condition: Demand type known?"}}
    choose_type{"Human: Choose demand type"}
    record_type["Script: Record chosen demand type"]
    evidence["Script: Collect blast-radius evidence"]
    policy["Script: Apply deterministic routing policy"]
    route{{"Condition: Select demand route"}}
    stopped["Script: Record stopped demand"]
    dispatch_bug["Flow: Bug Fix"]
    dispatch_feature["Flow: Feature Delivery"]
    dispatch_maintenance["Flow: Maintenance"]
    dispatch_security["Flow: Security Remediation"]
    dispatch_incident["Flow: Incident Response"]
    dispatch_discovery["Flow: Discovery"]
    start --> capture
    capture --> classify
    classify --> known
    known -->|"Known"| evidence
    known -->|"Unknown"| choose_type
    record_type --> evidence
    evidence --> policy
    policy --> route
    route -->|"Missing / invalid type"| choose_type
    stopped --> exit
    route -->|"Bug"| dispatch_bug
    dispatch_bug --> exit
    choose_type -->|"[B] Bug"| record_type
    route -->|"Feature"| dispatch_feature
    dispatch_feature --> exit
    choose_type -->|"[F] Feature"| record_type
    route -->|"Maintenance"| dispatch_maintenance
    dispatch_maintenance --> exit
    choose_type -->|"[M] Maintenance"| record_type
    route -->|"Security"| dispatch_security
    dispatch_security --> exit
    choose_type -->|"[S] Security"| record_type
    route -->|"Incident"| dispatch_incident
    dispatch_incident --> exit
    choose_type -->|"[I] Incident"| record_type
    route -->|"Discovery"| dispatch_discovery
    dispatch_discovery --> exit
    choose_type -->|"[D] Discovery"| record_type
    choose_type -->|"[X] Stop"| stopped
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Capture demand | script | Implementation / decision packet pending |
| Normalize demand type | script | Implementation / decision packet pending |
| Demand type known? | condition | Implementation / decision packet pending |
| Choose demand type | human | Implementation / decision packet pending |
| Record chosen demand type | script | Implementation / decision packet pending |
| Collect blast-radius evidence | script | Implementation / decision packet pending |
| Apply deterministic routing policy | script | Implementation / decision packet pending |
| Select demand route | condition | Implementation / decision packet pending |
| Record stopped demand | script | Implementation / decision packet pending |
| Bug Fix | handoff | [Shared flow](../bug-fix/README.md); dispatch binding pending |
| Feature Delivery | handoff | [Shared flow](../feature-delivery/README.md); dispatch binding pending |
| Maintenance | handoff | [Shared flow](../maintenance/README.md); dispatch binding pending |
| Security Remediation | handoff | [Shared flow](../security-remediation/README.md); dispatch binding pending |
| Incident Response | handoff | [Shared flow](../incident-response/README.md); dispatch binding pending |
| Discovery | handoff | [Shared flow](../discovery/README.md); dispatch binding pending |

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
