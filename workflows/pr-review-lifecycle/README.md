# PR review lifecycle

Inspect readiness, claim a new revision, review, save, optionally comment and observe.

**Scaffold only.** Stage content, worker bindings, script implementations
and trusted approval validation are pending. Execution is disabled.

```mermaid
flowchart TD
    start(["Start"])
    exit(["End / governed handoff"])
    event["Script: Receive event or scheduled scan"]
    snapshot["Script: Read PR, checks and current revision"]
    terminal{{"Condition: PR merged or closed?"}}
    stop["Script: Stop monitoring closed PR"]
    eligible{{"Condition: Ready, green and eligible?"}}
    claim["Script: Claim exact review identity"]
    new_work{{"Condition: New claimed revision?"}}
    packet["Script: Build immutable review packet"]
    current{{"Condition: Revision and eligibility still current?"}}
    review["Agent: Review exact diff independently"]
    validate["Script: Validate structured findings"]
    save["Script: Save review before publication"]
    publish_enabled{{"Condition: COMMENT publication enabled?"}}
    recheck["Script: Recheck exact head, base and checks"]
    publish_current{{"Condition: Revision and eligibility still current?"}}
    comment["Script: Publish validated COMMENT once"]
    wait["Script: Record waiting or unchanged state"]
    start --> event
    event --> snapshot
    snapshot --> terminal
    terminal -->|"Closed / merged"| stop
    terminal -->|"Open"| eligible
    stop --> exit
    eligible -->|"Ready and green"| claim
    eligible -->|"Draft / pending / blocked"| wait
    claim --> new_work
    new_work -->|"New claim"| packet
    new_work -->|"Already claimed / saved"| wait
    packet --> current
    current -->|"Current"| review
    current -->|"Changed / blocked"| wait
    review --> validate
    validate --> save
    save --> publish_enabled
    publish_enabled -->|"Enabled"| recheck
    publish_enabled -->|"Save only"| wait
    recheck --> publish_current
    publish_current -->|"Current and eligible"| comment
    publish_current -->|"Changed / blocked"| wait
    comment --> wait
    wait --> exit
```

## Stage slots

| Stage | Executor | Content to add |
|---|---|---|
| Receive event or scheduled scan | script | Implementation / decision packet pending |
| Read PR, checks and current revision | script | Implementation / decision packet pending |
| PR merged or closed? | condition | Implementation / decision packet pending |
| Stop monitoring closed PR | script | Implementation / decision packet pending |
| Ready, green and eligible? | condition | Implementation / decision packet pending |
| Claim exact review identity | script | Implementation / decision packet pending |
| New claimed revision? | condition | Implementation / decision packet pending |
| Build immutable review packet | script | Implementation / decision packet pending |
| Revision and eligibility still current? | condition | Implementation / decision packet pending |
| Review exact diff independently | agent | [Prompt](../../stages/independent-review/prompt.md); candidate skill `code-review` |
| Validate structured findings | script | Implementation / decision packet pending |
| Save review before publication | script | Implementation / decision packet pending |
| COMMENT publication enabled? | condition | Implementation / decision packet pending |
| Recheck exact head, base and checks | script | Implementation / decision packet pending |
| Revision and eligibility still current? | condition | Implementation / decision packet pending |
| Publish validated COMMENT once | script | Implementation / decision packet pending |
| Record waiting or unchanged state | script | Implementation / decision packet pending |

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
