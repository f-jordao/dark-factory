# Fabro + Kiro ACP review worker

The same-machine adapter has been exercised with Fabro 0.254.0 and Kiro CLI
2.36.0, using the existing Kiro login. It gives Kiro an immutable review packet
and captures its final JSON response. The controller manages eligibility,
deduplication and publication.

## Start the local runtime

Requirements: Python 3.9+, authenticated GitHub CLI, and an installed,
authenticated Kiro CLI with the v3 ACP engine. The pinned Fabro installer
supports macOS arm64 and Linux arm64/x86_64.

From the repository:

```bash
python3 scripts/local_fabro.py start
python3 scripts/local_fabro.py status
```

On first start, the deterministic setup script downloads the pinned Fabro release
through `gh`, checks its release checksum, and configures a loopback-only server.
It stores its binary, environment catalog, state and private authentication
secrets under the Git-ignored `.dark-factory/runtime/`. It authenticates the
Fabro CLI to this server without changing the user's global server configuration.
These management commands never invoke an LLM.

The server also exposes Fabro's built-in UI at the loopback address printed by
`start`. Browser sign-in accepts the project-local dev token stored in
`.dark-factory/runtime/dev-token`. The UI provides real run history, stages,
logs, artifacts and timing; it does not yet represent the full demand-routing
policy. Browser and CLI sessions use the same authenticated local server.
No GitHub App registration is required for this local dev-token sign-in.

### What appears in the native UI

- **Runs → PRReview → Graph Source** shows the actual submitted review graph.
- **Settings → WORKFLOWS** contains variables and secrets settings.
- **Automations** can display the 13 lifecycle scaffolds after registration.
  Their API triggers are disabled and no recurring trigger is installed.
- Kiro does not appear in **Models** or **Integrations**. Fabro's generic ACP
  backend launches Kiro through our adapter; the CLI owns its authentication
  and model selection.

The installed 0.254.0 server returns HTTP 501 for `GET /api/v1/workflows`.
The newer `v0.400.0-nightly.0` source also routes workflow listing, detail and
run-list endpoints to `not_implemented` in real mode. This source inspection
does not validate that prerelease as a working replacement for our runtime.
An upgrade alone is therefore not a verified solution for a workflow catalog.
The lifecycle diagram is a design; only the review worker graph has been run.
See [workflow setup](workflows.md) for the complete scaffold catalog and its
disabled registration command.

```bash
python3 scripts/local_fabro.py stop
python3 scripts/local_fabro.py start
```

`stop` verifies the recorded process's executable and server identity before
terminating it. Stop only after active work has finished. The adapter prefers the
project's pinned binary; `DARK_FACTORY_FABRO_BINARY` is an explicit override.

The server's `dark-factory-local` environment uses its local execution provider.
The repository `.fabro/project.toml` serves offline validation; the setup script
creates the server's separate environment catalog. This adapter does not upload
packets to remote or container workers.

## Exercise the worker

```bash
python3 -m dark_factory pilot --fixture known-bug
python3 -m dark_factory pilot --fixture known-bug --execute
python3 -m dark_factory pilot --fixture known-bug --execute
python3 -m dark_factory pilot --fixture clean --execute
```

Inspection reports `would_review`, with zero agent invocations. Execution uses
the normal controller claims and a separate pilot state database. The second
identical trigger reuses the saved result. Fixtures use the reserved
`offline/pilot` namespace, synthetic readiness, and no GitHub client or publisher.
They cannot attest that a real PR's checks are green.

Inspect `.dark-factory/runs/<review-key>/input.json`, `output.json` and `worker.log`.
Each Fabro attempt has `run.json`, its generated workflow, a workspace profile
and an export of the stage responses and events. Runtime artifacts can contain
private review context; keep them local.

For a real PR, configure exact required-check names and use `reconcile --execute`.
`--publish` is separately required to post a COMMENT review. No schedule or
automatic merge is installed.

## Authentication and the native ACP mode

Fabro starts the installed `kiro-cli` launcher. The pilot used its existing
authenticated SSO session; no model-provider API key was supplied to Fabro.
The pilot proves this login works for native ACP. It does not establish which
subscription or organizational billing rules apply to another account.

Kiro's v3 ACP engine exposes agents as session modes. The deterministic proxy
holds `session/new` until `session/set_mode` selects `dark-factory-reviewer`.
If that mode is unavailable or rejected, the review fails instead of using the
default agent.

The canonical profile is [workers/kiro/reviewer.json](../workers/kiro/reviewer.json).
Each attempt copies it into its own workspace, disables inherited default
resources, denies tools and declines every ACP permission callback. Packet data
arrives in the prompt, so file-reading and file-writing tools are unnecessary.
The controller parses, validates and writes the final response.

The managed Kiro launcher on the pilot machine injects a credential-agent
configuration into workspace agent files. The canonical source stays outside
`.kiro` so this cannot modify checked-in policy. Its deny-all permission rule is
retained; both successful pilot exports contained no tool-related events.
This local setup shares the user's machine and is not a production isolation
boundary.

## Failure handling

The controller hashes the prompt and configured review artifacts into the review
identity. Profile, workflow or worker-source changes invalidate earlier results.
Fabro's run ID is persisted before `start`, then the adapter polls its server
deterministically. A successful run must contain exactly one successful review
stage before output is accepted.

The workflow marks review as a goal gate with no retry target. Fabro 0.254.0's
validator warns about that missing target; the omission is intentional so a
failed review cannot reach a successful exit or automatically repeat reasoning.
Actual review failures require explicit controller retry.

Timeout, SIGTERM or interruption requests cancellation at the server and records
`cancellation_confirmed` in `run.json`. The outer worker timeout allows a grace
period for this cleanup. If cancellation is unconfirmed, inspect the saved run
ID before retrying; the record never claims that an unconfirmed run stopped.
Publication retries reuse saved findings rather than repeating review.

Exercise actual cancellation without making any model calls:

```bash
python3 scripts/verify_fabro_cancel.py
```

This opt-in check runs a deterministic ACP peer on the real Fabro server,
waits until it reaches the work stage, times out, and verifies both terminal
server state and worker termination. It is separate from the ordinary offline
test suite.

## Primary references

- [Pinned Fabro source](https://github.com/fabro-sh/fabro/tree/v0.254.0)
- [Prerelease real-mode workflow routes](https://github.com/fabro-sh/fabro/blob/v0.400.0-nightly.0/lib/apps/fabro-server/src/server/handler/mod.rs#L188)
- [Fabro ACP backend](https://docs.fabro.sh/core-concepts/agents)
- [Fabro run configuration](https://docs.fabro.sh/execution/run-configuration)
- [Fabro server configuration](https://docs.fabro.sh/administration/server-configuration)
- [Kiro ACP](https://kiro.dev/docs/cli/acp/)
- [Kiro agent configuration](https://kiro.dev/docs/cli/custom-agents/configuration-reference/)
