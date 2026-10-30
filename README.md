# dark-factory

An agentic software lifecycle whose control flow runs through deterministic code.
Agents are workers at explicit stages, not schedulers or polling loops.

**First working slice: the PR review lifecycle.** A Python controller inspects
GitHub, waits for configured checks, claims each eligible revision, invokes one
review worker, validates its findings, and publishes a COMMENT review when
explicitly enabled. Fabro + Kiro CLI is the initial worker adapter.

## The rule

> No new eligible work → no agent invocation.

```mermaid
flowchart LR
    event["GitHub event / scheduled scan"] --> inspect["Script: inspect PR + checks + revision"]
    inspect --> eligible{"Ready, green, new diff?"}
    eligible -->|No| wait["Persist state and exit"]
    eligible -->|Yes| review["Agent: review the exact diff"]
    review --> validate["Script: validate findings + recheck revision"]
    validate -->|Current and eligible| publish["Script: post COMMENT + record"]
    validate -->|Changed| wait
    publish --> wait
    wait -. Next event .-> event
    inspect -->|Merged / closed| stop["Stop monitoring"]
```

Triggers, CI inspection, revision tracking, routing, waiting, deduplication and
publication never require an LLM. The review worker may use multiple model calls
inside its review stage.

## Try it now

Python 3.9+ is sufficient. The controller has no third-party Python dependencies.

```bash
python3 -m dark_factory demo
python3 -m unittest discover -s tests -v
```

The offline demo makes **zero GitHub requests and zero LLM calls**. It simulates
draft → ready/pending → green → duplicate trigger → new commit/pending → green
→ merged. Only the two eligible revisions invoke the deterministic fixture
reviewer.

With an authenticated [GitHub CLI](https://cli.github.com/), inspect this repo:

```bash
python3 -m dark_factory scan --repo f-jordao/dark-factory
python3 -m dark_factory reconcile --repo f-jordao/dark-factory --pr 1
python3 -m dark_factory status
```

These commands inspect GitHub and update local state. They do not invoke agents
or publish comments without the corresponding flags.

## Connect a real review worker

The supplied config points to the Fabro adapter. Follow
[Fabro setup](docs/fabro-setup.md) before enabling it.

```bash
cp config.example.json config.local.json
# Set required_checks to the exact checks required for the repository.
python3 -m dark_factory reconcile \
  --repo f-jordao/dark-factory --pr 1 --config config.local.json --execute
```

`--execute` permits the eligible worker to run, but does not post anything.
Inspect the saved findings in `.dark-factory/runs/<review-key>/output.json`.
Publish saved findings independently:

```bash
python3 -m dark_factory reconcile \
  --repo f-jordao/dark-factory --pr 1 --config config.local.json --publish
```

Once a worker has been exercised and validated, both flags can be used together.
`scan` accepts the same flags and processes open and previously tracked PRs.
It is a one-shot script suitable for an external scheduler. This repository
does not install a schedule or enable an autonomous review bot.

## What is implemented

- GitHub inspection through existing `gh` authentication.
- Exact configured check names; missing, pending, failed, skipped, neutral or
  ambiguous required checks block the review. No configured checks also blocks it.
- SQLite state for PR observations, review results and concurrent process claims.
- Review identity includes repository, PR, head SHA, base SHA and policy digest.
- Prompt changes invalidate previous review identity.
- Eligibility checked before reasoning and again before publication.
- Results saved before publication; posting failures reuse the saved result.
- A durable marker identifies reviews already accepted by GitHub after an
  interrupted request. Only reviews authored by the authenticated account match.
- Findings checked against new-side diff lines; incomplete patches are rejected.
- Closed PRs leave active monitoring.
- Publication is always `COMMENT`, never approval, change request or merge.

## Boundaries of this first slice

The deterministic controller and command-worker interface are tested. The
Fabro/Kiro files are an integration template; an actual authenticated ACP review
has not yet been exercised end to end.

Review context is currently the changed-file patches, PR description and selected
root standards files at the pinned base SHA. It does not yet retrieve linked
issues, nested standards, unchanged source files or test results. Missing or
incomplete patches require human handling rather than a partial automated review.

The final revision check is followed by a GitHub write, so a commit can still arrive
between those operations. `commit_id` pins the posted review to its reviewed head;
it does not make the read and write atomic. Native required-review enforcement
belongs in GitHub rulesets.

The local Fabro adapter is not a security boundary. A review prompt's tool
restrictions must be backed by harness permissions and worker isolation before
running on untrusted repositories. Controller credentials should not be available
to a production worker.

## Where this is going

The full lifecycle is documented in [Demand to merge](docs/lifecycle.md):
intake → demand type → blast-radius evidence → human gates → implementation
→ verification → review → merge eligibility.

The review prompt keeps Matt Pocock's **Standards** and **Spec** axes separate.
It is a project-authored adaptation, not his installed skill.
See [skill integration](docs/skills.md) and [next milestones](ROADMAP.md).

The earlier framework comparison is retained as
[research context](docs/research.md). This README and the architecture decisions
describe the current direction.

## Verification

See [verification status](docs/verification.md) for the initial checks. Local
tests and offline Fabro validation pass. GitHub-hosted CI is currently unable
to start because GitHub reports an account billing or spending-limit issue.
