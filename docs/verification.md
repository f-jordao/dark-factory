# Verification

Date: 30 October 2026.

| Check | Result |
|---|---|
| Controller, adapter and workflow scaffold tests on Python 3.9.6 | 60 tests pass |
| Offline lifecycle demo | Pass; two fixture reviews, zero LLM calls and zero GitHub requests |
| Live `gh` inspection of this private repository | Pass; no open PRs at verification time |
| Fabro 0.254.0 offline workflow validation | Pass; three nodes, two edges; intentional no-retry goal-gate warning |
| GitHub-hosted CI | Job could not start because of an account billing or spending-limit issue |
| Authenticated Fabro → Kiro 2.36.0 native ACP, known defect | Pass; one Spec finding at `retry.py:2` for missing seconds-to-milliseconds conversion |
| Authenticated ACP, clean change | Pass; no findings for a rename preserving the conversion |
| Real worker through the controller, repeated trigger | First call reviewed; second reused the result with zero agent invocations |
| Live Fabro server cancellation with deterministic ACP fixture | Pass; terminal failed run and worker stopped, zero LLM calls |
| Local server stop/start and CLI reauthentication | Pass; runtime configuration and state reused |
| Fabro built-in web UI and local browser sign-in | Pass; authenticated run history and successful review timing visible |
| Native workflow catalog, Fabro 0.254.0 | Unavailable; authenticated `GET /api/v1/workflows` returns HTTP 501 |
| Newer prerelease workflow catalog | Source inspection only: `v0.400.0-nightly.0` real routes still use `not_implemented`; no runtime upgrade performed |
| Complete workflow scaffold structure | Pass; six demand routes, seven shared flows, valid references and explicit human decision paths |
| Fabro validation of all scaffold graphs | Pass; 13 graphs; intentional no-retry warning on each scaffold guard |
| Real Fabro scaffold guard | Pass; feature scaffold stopped at its failed guard, zero agent or human stages and zero model calls |
| Offline disabled-definition registration | Pass; repeat registration is unchanged; conflicts preserve existing definitions; no run or schedule endpoint used |
| Live Fabro scaffold registration and UI | Pass; all 13 definitions visible under Automations, every Run button disabled; repeat registration unchanged |
| Tool activity in successful ACP exports | No tool-related events observed |
| Actual review publication | Not yet exercised; offline publisher tests pass |

The GitHub check annotation states that recent account payments have failed
or the spending limit needs increasing. It does not identify which condition
applies. Resolve the account setting or provide a configured runner before
treating hosted CI as verified. Repository Actions are enabled.

The review packets in the authenticated pilot were offline fixtures, not real
GitHub PRs. Their synthetic readiness cannot bypass CI on a GitHub repository.
No model-provider API key was supplied to Fabro; Kiro used its existing login.
Account billing entitlement was not inferred from authentication.

Kiro is an ACP worker, not a named Fabro settings integration. Its authentication
and model selection remain in Kiro. The actual review graph is visible under
Runs → PRReview → Graph Source. Settings' WORKFLOWS heading groups variables
and secrets. The Automations page supports disabled scaffold definitions.
The full lifecycle has structural graphs and empty stage slots; it has not
been deployed as an operational end-to-end workflow.

Local evidence, excluded from Git:

- Known defect: Fabro run `01M666K7BW73HHDZYFZ9HSZFNC`.
- Clean change: Fabro run `01M666QJE2A5D9PFY712BKGD0M`.
- Controller review: Fabro run `01M66744TWAPZ1M6SWH341CG2N`, review key
  `a4184a84f0cfa14605d802ed1133b50b184217a4ecbf20015a768374afd86dc1`.
- Cancellation fixture: Fabro run `01M6673ZEZJT8YEAAPD6BKEG7X`.
- Scaffold guard: Fabro run `01M66G30T439ZE41KQFBNXRZTE`; only `start` and
  `scaffold_guard` ran. Its failed terminal state is the expected content guard.
- Disabled registration: `.dark-factory/runtime/scaffold-registration.json`.
  The 13 definitions target scaffold commit
  `dd6ae769b5e3b58b7967dcb1f3ba3b6ec53533b5`; no run or schedule was created
  by registration.

The 60 offline tests cover suppression of ineligible and duplicate work,
revision races, claims and recovery, publication retries, policy invalidation,
strict response validation, native ACP mode selection, permission denial,
graceful command timeout, runtime identity checks and separation of pilot
fixtures from GitHub.
Scaffold tests also cover category/risk routing, unknown evidence, discovery
separation, dangling or unreachable stages, conditional fallbacks, approval
record fields, inert generated graphs, path containment and disabled registration
idempotency/conflict handling.
The fake ACP cancellation check validates Fabro process cleanup; it does not
prove cancellation behavior of every managed launcher or arbitrary worker.

GitHub publication and continuously running event dispatch remain unexercised.
No recurring schedule or automatic merge was enabled. The local Fabro server
is available for explicit work and does not schedule reviews.

The initial guard experiment exposed that a failed command still follows an
unconditional edge. It was canceled after the inert ACP placeholder and a human
gate; no model call occurred. Generated graphs now require success to progress
from command/agent slots and terminate through an explicit fallback. The
subsequent real guard check above confirms that no agent stage starts.
