> Historical research from 30 October 2026. The later project decision is Fabro workers, Matt Pocock methods and deterministic lifecycle control. See README.md and docs/decisions/0001-deterministic-controller.md for the current direction. This comparison is research, not a runtime benchmark.

# Open-source orchestration for an agentic software lifecycle

Research date: 30 October 2026  
Scope: GitHub repositories; incoming requests, features, bugs and operational demand through classification, implementation, human decisions, verification and merge.

## Recommendation

**Pilot Fabro first if your priority is defining and seeing the complete lifecycle as a workflow graph. Pilot Fullsend alongside it if you prefer an existing issue-to-PR pipeline with less process design.** Use GitHub rulesets as the final authority for merge. Use Spec Kit for the feature, bug-fixing and investigation processes that run inside the lifecycle.

These are different choices. Fabro supplies a programmable factory engine. Fullsend supplies a more opinionated development pipeline. GitHub Agentic Workflows supplies repository automation through GitHub Actions. Temporal and LangGraph are foundations for building your own system. Spec Kit and BMAD supply development processes. A coding-agent SDK supplies workers. Buying into one layer does not automatically supply the others.

The best initial architecture for your stated needs is:

```text
GitHub issue / feature request / alert
                │
                ▼
Trusted intake → type + blast-radius evidence → deterministic policy
                │
                ▼
Fabro workflow selected by type and required approvals
                │
      ┌─────────┼──────────┬──────────────┐
      ▼         ▼          ▼              ▼
     Bug     Feature   Maintenance   Security / incident
      │         │          │              │
      └─────────┴──────────┴──────────────┘
                │
                ▼
Sandboxed implementation → tests → independent review
                │
                ▼
Reassess actual diff → required human approval(s)
                │
                ▼
GitHub rulesets + required checks + current revision → merge
```

This is a proposed architecture, not a claim that a single project ships every box preconfigured. Deployment, rollout and production monitoring are subsequent stages; a successful merge does not prove a safe release.

## How the research was conducted

I examined public project repositories, official documentation, license declarations, architecture records and selected enforcement code. I compared 15 projects or project families, including alternatives that are no longer attractive for new adoption. The assessment is based on source and documentation, not an installed performance or reliability benchmark.

For the closest candidates I recorded the public `main` revisions inspected. This matters because these projects change quickly and documentation can lag implementation:

| Repository | Inspected revision |
|---|---|
| `fabro-sh/fabro` | `ff5b08f8cdb205716c134919badd67e5307a1486` |
| `fullsend-ai/fullsend` | `f6efdd06422862517fd73210938c12d29ed7a07f` |
| `fullsend-ai/agents` | `ec1ed4607ff6df637d09e7258abb426732f7cac9` |
| `github/gh-aw` | `0c48a3354d11aaea16ae2b0fec7bca6c24c1ee6f` |
| `github/spec-kit` | `2a23a848f888de05f0107061d45232c485d6bae0` |

I distinguish native primitives from processes you would have to build. “Human-in-the-loop” can mean a paused prompt, a trusted approval API, or a GitHub-enforced code-owner review; these offer different guarantees.

## Shortlist

| Project | Open-source license / boundary | What it supplies | What you must add | Fit |
|---|---|---|---|---|
| **Fabro** | MIT | Workflow graphs, branches and loops, human gates, execution history, sandboxes, server/API and web interface, GitHub PR publication | Demand taxonomy, blast-radius evidence and policy, ownership rules, type-specific workflows | Closest match for a customizable visual factory |
| **Fullsend** | Apache-2.0 for the main project | Issue triage, code, review and feedback loops; Git-hosted coordination; protected-path and risk-verdict controls in the agent implementation | Organization-specific acceptance, planning, governance and lifecycle extensions | Closest opinionated pipeline, especially for bugs |
| **GitHub Agentic Workflows** | MIT | Markdown-defined agentic jobs compiled to GitHub Actions; event triggers, constrained writes and repository automation | Cross-stage lifecycle state, risk rules, human approval handoff, default-branch merge path | Strong GitHub-native starting point |
| **Spec Kit** | MIT | Feature, bug-fix and assessment processes; executable YAML workflows, gates, branching and persisted resume | Hosted intake, worker isolation, identity/permissions and GitHub merge enforcement | Strong process library and potentially a lightweight runner |
| **Temporal** | MIT server | Durable workflows, waiting for external events, retries and execution history | Agent workers, all SDLC logic, approval experience and repository integration | Strong foundation for a larger internal platform |
| **LangGraph** | MIT core | Stateful agent graphs, checkpointing, interrupts, branching and resumption | SDLC processes, production hosting, durable storage, approval identity and GitHub integration | Strong agent-oriented custom implementation |
| **Orchestrator.inc / Agent Orchestrator** | Apache-2.0 | Desktop supervision of agents, isolated worktrees, PR/CI/review feedback and a live work board | Organization-wide intake and explicit risk/approval policy | Useful operator workspace |
| **Windmill** | AGPLv3 source build without enterprise flag; distributed editions have additional terms | Visual/code workflows, scripts, triggers, approval waits and application-building tools | Coding execution environment and SDLC-specific flows | Attractive generic visual orchestrator; examine edition boundaries |

Sources: [S01–S18], [S23–S24]. License labels describe the inspected project boundaries, not the license or price of a model, a coding-agent subscription or a hosted service.

## Fabro: my first pilot

Fabro explicitly targets a dark software factory with an engineer-defined process. Its workflow graphs are written in Graphviz DOT. Nodes execute work; edges express transitions; human gate nodes pause for decisions. Its published example is a plan → approve → implement flow with a revise loop. [S01–S03]

This is a close match to your mental model: different demand enters the system, moves through an explicit graph and stops where human judgment matters. You can create separate bug, feature, dependency and security graphs rather than force every change through an identical process.

The classification and policy are your work. I did not find a complete, general-purpose demand taxonomy or automatically verified organization-wide blast-radius model. Define those as trusted steps before selecting a graph, and repeat the assessment after implementation.

Fabro documents a server, API, web interface and GitHub integration. Its GitHub App mode enables browser sign-in and webhooks. The default token mode disables the embedded web interface. For the visual team experience, assess App mode, not just the simplest CLI installation. [S04]

Its documented PR publication can create a PR and enable GitHub auto-merge. GitHub then determines whether required conditions are satisfied. That makes branch rules part of the architecture, rather than something replaced by an agent’s judgment. [S04]

The approval configuration deserves attention: unanswered gates fail closed, but an explicit timeout default or `--auto-approve` can advance them. For production approval workflows, preserve an explicit human answer and do not configure timeout-to-approval. Also constrain agent-generated routing signals: the transition documentation includes direct jumps and routing hints, so a graph alone is not proof that an untrusted model cannot influence the route. [S02–S03]

**Assessment:** the strongest conceptual and visual fit. Pilot it to establish the process; do not assume its factory positioning proves your organization’s security, availability or approval requirements.

## Fullsend: the closest ready-made pipeline

Fullsend’s bug-fix guide documents triage → code → review → fix/re-review, coordinated through issues, PRs, labels and repository mechanisms. Triage can route to needs-info, duplicate, blocked or ready-to-code. This is unusually close to an actual incoming-demand lifecycle. [S05–S06]

The project’s vision distinguishes the existing bug-fix workflow from broader discovery, refinement, prioritization, delivery and monitoring ambitions. Treat the issue-to-code/review pipeline as the concrete starting point, and evaluate the rest separately. Do not read its full-lifecycle vision as evidence that every phase is complete. [S07]

**A significant research finding: the risk documentation lags current enforcement.** The July risk-scoring ADR says risk is informational and protected paths supply the blocking mechanism. The newer agents code has a risk-verdict gate. When enabled, it downgrades an automatic approval to a comment for high, missing, invalid or degraded risk assessment. The inspected review harness sets risk assessment to `true` and the threshold to `4`. The post-review code treats a score at or above that threshold as requiring a human; `6` is an explicit opt-out from the verdict gate. [S08–S10]

These are implementation defaults, not calibrated probabilities or recommended thresholds for your repositories. The risk skill mixes deterministic metadata with LLM-assisted history and issue-context analysis. Measure its accuracy on your own changes before allowing risk-based autonomy. [S11]

Protected-path enforcement occurs outside the review agent. The inspected post-review implementation downgrades approvals for guarded paths. Keep this distinct from GitHub-native enforcement: repository rules must still require the appropriate reviews and checks, and the agent must not be able to rewrite or bypass those rules. [S09, S23]

**Assessment:** pilot on historical and new bug reports if you want an opinionated pipeline quickly. Compare how easily it can express a feature approval, an investigation that stops without code, and a migration requiring multiple specialists. Those are the differentiators against Fabro.

## GitHub Agentic Workflows: repository-native automation

GitHub Agentic Workflows turns Markdown plus configuration into GitHub Actions jobs. Its architecture separates agent work from configured writes: the agent job defaults to read-only GitHub access, and “safe outputs” validate and apply selected writes in separate jobs. This is useful for intake, triage, issue labels, implementation PRs, CI investigation and review support. [S12–S13]

This naturally fits a system whose demand and approvals live in GitHub. You still need to design how separate jobs share lifecycle state, how risk evidence is validated, and how trusted human decisions resume the correct work.

**Merge limitation:** the current pull-request reference marks `merge-pull-request` as experimental and states that it refuses merges to the repository’s default branch. Therefore, do not assume that operation supplies a complete “merge to main” path. Use an authorized separate merge controller or GitHub’s governed merge mechanism, subject to the repository’s rules. [S14]

**Assessment:** a strong alternative if you want incremental GitHub automation and a modest infrastructure footprint. It is less naturally a single visible lifecycle graph than Fabro.

## Spec Kit: more than a collection of prompts

The inspected Spec Kit supports independent entry processes for features, bug fixing and idea assessment. Its workflow documentation describes commands, prompts, shell steps, human gates, conditional dispatch, loops, fan-out/fan-in and persisted resumption. It should not be dismissed as only a sequence of manually invoked prompt templates. [S15–S16]

You could use a workflow switch to route a classified demand to a bug process, a feature process or an assessment process. Templates make acceptance criteria, plans and verification records consistent.

Its runner is not a security sandbox. The documentation explicitly says shell steps run with the user’s privileges. A persisted gate is also not a code-owner review or an authenticated approval boundary by itself. Gate verdicts can be supplied through inputs, and non-empty defaults can decide gates automatically. Protect who can supply those inputs when connecting it to a service. [S16]

**Assessment:** a valuable process layer inside Fabro, a GitHub automation workflow or a custom orchestrator. It is also worth evaluating as a smaller standalone runner when the team can supply hosting, isolation and approval enforcement.

## Temporal and LangGraph: when to build your own

Temporal’s server supplies durable workflow execution and retries. Its SDK interaction mechanisms let applications receive external decisions. This suits work that waits hours or days for approvals, survives worker restarts and coordinates several services. It does not supply a software-development lifecycle out of the box. [S17]

LangGraph supplies stateful agent orchestration, durable execution, persistence and human interrupts. It is closer to the reasoning and agent layer. The MIT library can run independently; hosted deployment, tracing and other associated products must be assessed separately from the core library. [S18]

For a custom implementation, choose one primary owner of lifecycle state. Temporal can own long-running business transitions while an agent framework operates inside activities. Alternatively, LangGraph can own a smaller end-to-end agent workflow with durable storage. Start with both only if their responsibilities are clear.

External effects need idempotency regardless of the engine: a resumed or retried step should recognize an existing PR, comment or merge request. Use keys such as repository + issue + stage + source revision. Keep LLM calls outside deterministic workflow replay where the engine requires that separation.

**Assessment:** strongest when you are deliberately creating an internal platform and can fund the engineering. More work than the purpose-built factory projects.

## Other useful projects and exclusions

**Orchestrator.inc**, formerly associated with the Composio Agent Orchestrator repository, is a practical agent-supervision workspace. Its current repository describes isolated worktrees, worker sessions, CI/review feedback and a board showing work that needs attention. It fits an engineer operating several tasks. I would not assume it provides your organization-wide classification and approval policy. [S19]

**Windmill** is worth evaluating if a generic visual workflow editor and approval steps are more important than a prebuilt coding factory. Its source and distributed editions have distinct licensing terms. Verify authenticated, group-restricted approvals in the edition you intend to run; an approval link is not automatically an authorization policy. [S20]

**BMAD Method** offers right-sized processes and product, architecture, development and testing perspectives. It is a process approach to use within your delivery system. Its inspected README describes a stable v6 line and a changing v7 preview; pin the version you assess. [S21]

**Attractor** from StrongDM is a relevant design reference for the software-factory idea. Its repository contains natural-language specifications and instructions to implement your own version. It is not a drop-in production runtime. Fabro is a more concrete runtime to pilot for graph-based execution. [S22]

**OpenHands** offers a useful open-source coding-agent execution layer. Its Software Agent SDK, agent server, UI and automation service have separate responsibilities. The automation service is described as beta and aimed at scheduling/event dispatch for OpenHands Cloud. Do not assume the SDK alone supplies the full lifecycle. [S25–S26]

**Mastra** is a TypeScript alternative for a custom agent/workflow system. It supports branches, parallel work and suspend/resume. Its core is Apache-2.0, while `ee/` code has an enterprise license. As with LangGraph, you must provide the SDLC. [S27]

**Symphony** is a useful issue-to-agent architectural reference, but its inspected README calls it an engineering preview and its demonstration uses Linear. It is not my first choice for your GitHub-centered, complete governance requirement. [S28]

I excluded **Automaker** from new-adoption recommendations because its current README says it is no longer actively maintained. **Vibe Kanban** says it is sunsetting. Existing users can still study or fork their code, but those statuses materially change adoption risk. [S29–S30]

## The lifecycle to implement

The following is my proposed process. The labels and policy levels are illustrative, not a standard shipped by these frameworks.

### 1. Create a durable demand record

Every request gets a unique ID and source, type, owner, urgency, affected repositories/services, acceptance criteria, expected blast radius, evidence, unknowns, policy version and approval state.

Treat an issue body as a request for work. It does not grant authority to merge, access another repository, change secrets or weaken the delivery controls.

### 2. Classify type separately from risk

| Demand type | First useful action | Type-specific evidence |
|---|---|---|
| Bug | Reproduce and diagnose | Failure before fix; regression test; root-cause evidence |
| Feature | Clarify intent and scope | Acceptance examples; affected user journeys; design/architecture changes |
| Maintenance / dependency | Inspect compatibility | Upstream changes; affected consumers; breaking-change and license checks |
| Security | Validate threat and exposure | Exploitability, affected versions and adversarial verification |
| Incident | Assess containment and prepare a minimal repair | Operational facts, rollback plan and regression evidence |
| Investigation | Gather evidence without committing to a change | Findings, alternatives and a human go/clarify/stop decision |

A one-line bug can affect authorization across every customer. A large documentation change may have little runtime impact. Urgency does not reduce blast radius.

### 3. Assess blast radius with observable evidence

Inspect the changed components and their consumers; dependency and call relationships; public APIs and schemas; permissions; migrations; infrastructure; CI and deployment configuration; tests; rollback difficulty; and services or tenants potentially affected.

Paths and diff counts are useful signals, but they do not prove semantic impact. Use deterministic repository checks for observable facts, then allow an agent to explain consequences with references to code. Unknown impact is itself a reason to obtain more evidence or escalate.

Repeat this assessment on the actual diff. The intake estimate must not remain authoritative after an agent expands scope.

### 4. Apply a deterministic approval policy

| Proposed class | Example | Initial human interaction | Merge requirement |
|---|---|---|---|
| R0: explicitly allowlisted trivial work | Non-sensitive typo with narrow effects | Optional intent clarification | Initially reviewed; consider auto-merge only after measured qualification |
| R1: localized change | Reproduced bug within one component | Clarify incomplete reports | Code-owner approval on the final revision |
| R2: material change | Feature, shared dependency, public API impact or incomplete evidence | Approve scope/acceptance and plan | Owner approval and relevant acceptance evidence |
| R3: critical or wide reach | Auth, data migration, delivery controls, cross-service change | Owner and relevant specialist approve plan | Specialist and owner acceptance, strict checks and explicit merge authority |

Use the highest applicable class. A sensitive path cannot be made “safe” by averaging it with documentation changes. Incomplete evidence must not become permission to proceed.

Do not treat an LLM’s self-reported confidence as a calibrated probability. If you introduce a numeric risk model, measure false negatives and false positives against human-reviewed historical changes.

### 5. Run the correct route

```text
Bug:
reproduce → scoped fix → regression tests → review → final approval → merge

Feature:
clarify → acceptance criteria → plan approval → build → acceptance tests
→ review → final approval → merge

Maintenance:
compatibility evidence → bounded update → consumer tests
→ review → required approval → merge

Security / incident:
validate → specialist-approved remedy → minimal implementation
→ targeted tests → independent review → specialist acceptance → governed merge

Investigation:
gather evidence → findings → human go / clarify / stop
→ only a new authorized change enters an implementation route
```

Failed tests or review return to a bounded repair loop. Limit retries, elapsed time and spend; after the limit, hand a person the evidence and a clear reason for stopping.

### 6. Make human decisions concrete and reusable

Humans should decide intent when ambiguous, scope when substantial, specialist acceptance when consequences are critical, and whether the final change satisfies the authorized request.

Each approval should record the approver, authorized role, demand ID, plan or diff revision, target branch, policy version and approved scope. A new revision or changed scope can require renewed approval. A generic “approved” label should not authorize whatever later happens to be on the branch.

Present a short decision packet: requested behavior, changed behavior, affected systems, test evidence, remaining uncertainty, rollback options and the exact artifact under review.

### 7. Enforce the final merge outside the coding agent

Use GitHub rulesets or branch protection for PRs, required checks, review requirements, stale-approval handling and applicable code-owner review. Check the exact rules available for your repository visibility and GitHub plan. GitHub’s documentation describes ruleset availability and enforcement options. [S23–S24]

CODEOWNERS must be connected to a required-review rule to enforce that review. Listing ownership alone is not sufficient. If you require separate security and service-owner approvals, encode the two obligations explicitly; do not assume a list of owners automatically requires approval from every person or team.

Keep policy, workflow, ownership and delivery-control changes on protected paths. Give the execution identity the least authority needed to write its branch and produce a PR. Use a separately controlled merge path, and prevent bypass through direct pushes or an overprivileged bot.

A final merge decision should confirm:

```text
Authorized demand
AND current scope permitted
AND required evidence complete
AND required checks successful
AND required human approvals valid for current revision
AND no unresolved blocking findings
AND repository merge conditions satisfied
```

## A practical pilot and decision criteria

Run Fabro and Fullsend against the same small set of historical changes: a local bug, a feature, a dependency update, an authentication change, a migration and an ambiguous investigation. Start in PR-only mode with human review on every code change. This allows process evaluation without assuming autonomy is already earned.

Evaluate observed behavior, rather than comparing star counts or marketing claims:

1. Does the demand reach the right process, including needs-info and stop?
2. Are blast-radius claims backed by inspectable repository evidence?
3. Can required human decisions survive a restart and be tied to a revision?
4. Can the coding agent change or bypass the policy?
5. Does an expanded diff escalate rather than retain the initial low-risk route?
6. Are tests meaningful enough to distinguish a plausible fix from a correct fix?
7. Does independent review detect deliberate defects?
8. Are failed checks, conflicting feedback and merge conflicts handled within limits?
9. Can a replay avoid duplicate PRs and other external effects?
10. Can the system explain why a demand is waiting and exactly who must act?

Track human minutes per accepted change, escaped defects, incorrect routing, failed-run recovery, elapsed approval time, rework and cost. Do not set numeric success thresholds without the repository’s baseline.

My selection rule: choose **Fabro** if explicit graphs, varied demand routes and placement of human gates win; **Fullsend** if its supplied pipeline handles your representative work with fewer extensions; **GitHub Agentic Workflows** if you prefer incremental repository automation; **Temporal or LangGraph** if you are intentionally building a larger platform.

## Primary-source register

All sources were inspected on 30 October 2026. URLs are supplied as reference text. Mutable `main` content can change; the recorded revisions above identify the source snapshot for the closest candidates.

- **S01 — Fabro repository and MIT license:** `https://github.com/fabro-sh/fabro`
- **S02 — Fabro human gates:** `https://docs.fabro.sh/workflows/human-in-the-loop`
- **S03 — Fabro transitions:** `https://docs.fabro.sh/workflows/transitions`
- **S04 — Fabro GitHub integration:** `https://docs.fabro.sh/integrations/github`
- **S05 — Fullsend repository:** `https://github.com/fullsend-ai/fullsend`
- **S06 — Fullsend bug-fix workflow:** `https://github.com/fullsend-ai/fullsend/blob/main/docs/guides/user/bugfix-workflow.md`
- **S07 — Fullsend current scope and vision:** `https://github.com/fullsend-ai/fullsend/blob/main/docs/vision.md`
- **S08 — Fullsend risk-scoring ADR:** `https://github.com/fullsend-ai/fullsend/blob/main/docs/ADRs/0089-pr-risk-assessment-scoring.md`
- **S09 — Fullsend post-review enforcement:** `https://github.com/fullsend-ai/agents/blob/ec1ed4607ff6df637d09e7258abb426732f7cac9/scripts/post-review.sh` — especially risk-verdict gate around lines 1548–1704 and protected-path checks before it.
- **S10 — Fullsend review harness defaults:** `https://github.com/fullsend-ai/agents/blob/ec1ed4607ff6df637d09e7258abb426732f7cac9/harness/review.yaml`
- **S11 — Fullsend risk-assessment skill:** `https://github.com/fullsend-ai/agents/blob/ec1ed4607ff6df637d09e7258abb426732f7cac9/skills/pr-risk-assessment/SKILL.md`
- **S12 — GitHub Agentic Workflows repository and MIT license:** `https://github.com/github/gh-aw`
- **S13 — GitHub Agentic Workflows architecture:** `https://github.github.com/gh-aw/introduction/architecture/`
- **S14 — GitHub Agentic Workflows PR operations and merge limitation:** `https://github.github.com/gh-aw/reference/safe-outputs-pull-requests/`
- **S15 — Spec Kit repository and process entry points:** `https://github.com/github/spec-kit`
- **S16 — Spec Kit executable workflows:** `https://github.github.io/spec-kit/reference/workflows.html`
- **S17 — Temporal repository, capabilities and MIT license:** `https://github.com/temporalio/temporal`
- **S18 — LangGraph repository and core capabilities:** `https://github.com/langchain-ai/langgraph`
- **S19 — Orchestrator.inc repository and Apache-2.0 license:** `https://github.com/OrchestratorInc/agent-orchestrator`
- **S20 — Windmill repository, workflow example and licensing boundaries:** `https://github.com/windmill-labs/windmill`
- **S21 — BMAD Method, version status and method:** `https://github.com/bmad-code-org/BMAD-METHOD`
- **S22 — StrongDM Attractor specifications:** `https://github.com/strongdm/attractor`
- **S23 — GitHub available rules for rulesets:** `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets`
- **S24 — GitHub code-owner rules:** `https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners`
- **S25 — OpenHands Software Agent SDK:** `https://github.com/OpenHands/software-agent-sdk`
- **S26 — OpenHands automation-service boundaries and beta status:** `https://github.com/OpenHands/automation`
- **S27 — Mastra core and enterprise licensing / suspend-resume:** `https://github.com/mastra-ai/mastra`
- **S28 — Symphony scope and preview status:** `https://github.com/openai/symphony`
- **S29 — Automaker maintenance status:** `https://github.com/automaker-org/automaker` — “Project Status” near the end of the README.
- **S30 — Vibe Kanban sunsetting notice:** `https://github.com/BloopAI/vibe-kanban`
