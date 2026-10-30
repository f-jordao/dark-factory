# Fabro + Kiro review worker

This is a same-machine integration template. The controller is operational
without Fabro for its offline demo and GitHub inspection. An authenticated ACP
review remains the next integration milestone.

## Requirements

- Fabro CLI and a configured, authenticated Fabro server on the same machine.
- Kiro CLI installed and signed in on the machine executing the ACP process.
- A server-managed local environment named `dark-factory-local`.
- An explicit Kiro tool policy allowing packet reads and writing the result file.

Follow [Fabro installation](https://docs.fabro.sh/getting-started/installation)
and its setup wizard. A checked archive of Fabro 0.254.0 was used for offline
workflow validation during this repository's creation; it is not installed by
this project.

Merge the environment in [the server fragment](fabro-server.example.toml) into
the server's generated `settings.toml`. Preserve the generated authentication and
storage settings. The repository's `.fabro/project.toml` declares the same
environment for local validation; that client-side declaration is not transmitted
to the server.

```bash
fabro validate workflows/pr-review/workflow.toml
kiro-cli acp --help
```

The workflow contains start → one ACP review stage → exit. It uses
`acp.command="kiro-cli acp"`, disables automatic review retries and disables
Fabro's managed Git run branch. There are no agent polling or routing stages.

The adapter supplies immutable packet and output paths through `--goal-file`.
Absolute host paths require the server's local worker to run on the same machine.
For Docker, Daytona or a remote server, add explicit packet upload and result
download. Those transports are not implemented by this adapter.

## Authentication and subscriptions

ACP authentication belongs to the external harness, not Fabro's model provider
configuration. Kiro's native ACP command uses the CLI login session. Verify the
actual account and entitlement during the pilot; this project does not store or
copy login tokens.

A Claude ACP adapter can replace the Kiro command later. It must satisfy the
same structured-output contract and supported harness authentication. Changing
the worker behavior requires bumping `review_version` in the controller config.

## Exercise before enabling a schedule

Create a controlled PR, wait for its configured `tests` check, then run with
`--execute` alone. Check the saved `input.json`, `output.json` and worker log.
Test a known defect, a clean change and a commit arriving during review.

Test harness permission failures, malformed output and worker cancellation.
The controller times out its command; terminating the Fabro CLI is not proof that
the server cancelled its run. Before using `--retry` after a timeout, check and
stop any still-active Fabro worker. Automatic cancellation is a tracked follow-up.

Only after inspecting the result should a pilot invocation add `--publish`.
The publisher issues COMMENT reviews and does not approve or merge.

## Primary references

- [Fabro ACP backend](https://docs.fabro.sh/core-concepts/agents)
- [Fabro run configuration](https://docs.fabro.sh/execution/run-configuration)
- [Fabro server configuration](https://docs.fabro.sh/administration/server-configuration)
- [Fabro node types](https://docs.fabro.sh/workflows/stages-and-nodes)
- [Kiro ACP](https://kiro.dev/docs/cli/acp/)
