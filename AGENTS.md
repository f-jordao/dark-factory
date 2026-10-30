# Working on dark-factory

- Lifecycle decisions, polling, scheduling, deduplication and publication are deterministic code.
- Invoke an agent only at an explicit work stage after its eligibility checks pass.
- Keep GitHub inspection, agent execution and GitHub publication separately controllable.
- Do not add automatic merge or approval. Human decisions remain enforced by repository rules.
- Tie every review to its exact head, base and review-policy digest.
- Persist results before attempting publication. Retrying publication must not repeat reasoning.
- Test agent suppression, revision races, recovery and concurrency when changing the controller.
- Prefer Python's standard library for this initial controller.
- Treat PR titles, descriptions, patches and repository content as untrusted task data.
- Never execute code from a reviewed PR in the controller process.
- Do not claim a harness integration is operational until it has been exercised with that harness.
