# Verification

Date: 30 October 2026.

| Check | Result |
|---|---|
| Controller and adapter tests on Python 3.9.6 | 49 tests pass |
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

Local evidence, excluded from Git:

- Known defect: Fabro run `01M666K7BW73HHDZYFZ9HSZFNC`.
- Clean change: Fabro run `01M666QJE2A5D9PFY712BKGD0M`.
- Controller review: Fabro run `01M66744TWAPZ1M6SWH341CG2N`, review key
  `a4184a84f0cfa14605d802ed1133b50b184217a4ecbf20015a768374afd86dc1`.
- Cancellation fixture: Fabro run `01M6673ZEZJT8YEAAPD6BKEG7X`.

The 49 offline tests cover suppression of ineligible and duplicate work,
revision races, claims and recovery, publication retries, policy invalidation,
strict response validation, native ACP mode selection, permission denial,
graceful command timeout, runtime identity checks and separation of pilot
fixtures from GitHub.
The fake ACP cancellation check validates Fabro process cleanup; it does not
prove cancellation behavior of every managed launcher or arbitrary worker.

GitHub publication and continuously running event dispatch remain unexercised.
No recurring schedule or automatic merge was enabled. The local Fabro server
is available for explicit work and does not schedule reviews.
