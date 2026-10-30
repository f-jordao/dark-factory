# Stage skills

The orchestrator determines **when** work is eligible. A skill supplies the
method for **how** an agent performs that work. A skill is not a scheduler,
approval record or merge rule.

Matt Pocock's [skills repository](https://github.com/mattpocock/skills) is the
preferred method reference from the initial discussion.

| Planned stage | Candidate Matt Pocock skill | Integration status |
|---|---|---|
| Clarify a demand | `grill-with-docs` | Planned |
| Write agreed requirements | `to-spec` | Planned |
| Break work into vertical slices | `to-tickets` | Planned |
| Triage incoming requests | `triage` | Planned |
| Reproduce and diagnose | `diagnosing-bugs` | Planned |
| Implement | `implement` | Planned |
| Independent review | `code-review` | Two-axis method adapted in the project prompt |
| Explain a PR and its merge danger | `pr` | Planned |

No upstream skills are installed or vendored yet. Before importing them, pin
the source revision, preserve its license, configure its tracker references and
document any adaptations.

The [shared stage catalog](../stages/catalog.json) records candidate methods.
The 17 agent-stage prompt files under `stages/` have empty Method, Input and
Output sections. They are separate from the existing working PR-review prompt.
Adding content alone does not enable the new workflow scaffolds.

Skills that ask for scope decisions, seam approval or approval before publishing
must retain those interaction points when orchestrated. A background worker
should emit a structured request for a human decision and pause.

The initial [review prompt](../prompts/pr-review.md) separates **Standards** from
**Spec** and returns validated JSON. It does not yet reproduce the upstream
skill's two parallel sub-agents or retrieve the full upstream specification
context. Those are explicit follow-ups, not hidden assumptions.
