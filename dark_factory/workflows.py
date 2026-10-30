"""Structural workflow catalog. Inspect and build scaffolds without invoking workers."""

import json
import re
from pathlib import Path


SCAFFOLD_MESSAGE = "Workflow scaffold: stage content and trusted execution bindings are pending."
EXECUTORS = {"script", "agent", "human", "condition", "handoff"}
SHAPES = {
    "script": "parallelogram", "agent": "box", "human": "hexagon",
    "condition": "diamond", "handoff": "parallelogram",
}
DEMAND_TYPES = {"bug", "feature", "maintenance", "security", "incident", "discovery"}
SHARED_FLOWS = {
    "demand-intake", "verification", "diff-reassessment",
    "pr-preparation", "pr-review-lifecycle", "merge-readiness", "rework",
}


def read_json(path):
    return json.loads(Path(path).read_text())


def project_path(project, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Catalog paths must be nonempty project-relative paths")
    project = Path(project).resolve()
    path = (project / relative).resolve()
    if project not in path.parents:
        raise ValueError("Catalog path leaves the project: " + relative)
    return path


def load_catalog(project):
    project = Path(project).resolve()
    catalog = read_json(project / "workflows/catalog.json")
    stages = read_json(project_path(project, catalog["stage_catalog"]))["stages"]
    definitions = {}
    for item in catalog["workflows"]:
        if item["id"] in definitions:
            raise ValueError("Duplicate workflow: " + item["id"])
        definitions[item["id"]] = read_json(project_path(project, item["definition"]))
    return catalog, stages, definitions


def _reachable(start, adjacency):
    visited, remaining = set(), [start]
    while remaining:
        node = remaining.pop()
        if node not in visited:
            visited.add(node)
            remaining.extend(adjacency.get(node, []))
    return visited


def validate_catalog(project, generated=True):
    project = Path(project).resolve()
    catalog, stages, definitions = load_catalog(project)
    if catalog.get("_version") != 1 or catalog.get("execution_enabled") is not False:
        raise ValueError("Scaffold catalog must explicitly disable execution")
    identifiers = set(definitions)
    demand_types = [item.get("demand_type") for item in catalog["workflows"]
                    if item["group"] == "demand"]
    if set(demand_types) != DEMAND_TYPES or len(demand_types) != len(DEMAND_TYPES):
        raise ValueError("The catalog must contain each of the six demand routes exactly once")
    if not SHARED_FLOWS <= identifiers:
        raise ValueError("Missing a shared lifecycle workflow")
    policy = read_json(project_path(project, catalog["routing_policy"]))
    if set(policy["routes"]) != DEMAND_TYPES:
        raise ValueError("Routing policy must cover every demand type")
    for demand, flow in policy["routes"].items():
        if flow not in identifiers or definitions[flow].get("demand_type") != demand:
            raise ValueError("Routing policy points to the wrong demand workflow")
    for stage_id, stage in stages.items():
        if stage["executor"] not in EXECUTORS or stage.get("content_status") != "pending":
            raise ValueError("Stage must declare its executor and pending content: " + stage_id)
        if not isinstance(stage.get("inputs"), list) or not isinstance(stage.get("outputs"), list):
            raise ValueError("Stage must declare input/output slots: " + stage_id)
        if stage["executor"] == "agent":
            prompt = project_path(project, stage["prompt"])
            if not prompt.is_file() or "SCAFFOLD ONLY" not in prompt.read_text():
                raise ValueError("Agent prompt must be an explicit placeholder: " + stage_id)
            if stage.get("worker_binding") is not None:
                raise ValueError("Scaffold agent must not have a live worker binding")
        elif "prompt" in stage:
            raise ValueError("Only agent stages may have prompts")
        empty_slots = {
            "script": ("implementation",),
            "human": ("decision_packet", "trusted_decision_validator"),
            "condition": ("trusted_context_binding",),
            "handoff": ("dispatch_binding",),
        }
        for slot in empty_slots.get(stage["executor"], ()):
            if slot not in stage or stage[slot] is not None:
                raise ValueError("Scaffold execution/content slot must be empty: " + stage_id)
    summaries = []
    for item in catalog["workflows"]:
        flow = definitions[item["id"]]
        if flow["id"] != item["id"] or flow.get("status") != "scaffold":
            raise ValueError("Workflow identity/status differs from its catalog entry")
        if flow.get("enabled") is not False or item.get("enabled") is not False:
            raise ValueError("Workflow scaffolds must remain disabled")
        nodes = {node["id"]: node for node in flow["nodes"]}
        if len(nodes) != len(flow["nodes"]) or "start" in nodes or "exit" in nodes:
            raise ValueError("Workflow node IDs must be unique and not reserved")
        if not nodes or any(not re.fullmatch(r"[a-z][a-z0-9_]*", key) for key in nodes):
            raise ValueError("Workflow nodes require safe identifiers")
        edges = flow["edges"]
        outgoing = {key: [] for key in set(nodes) | {"start", "exit"}}
        reverse = {key: [] for key in outgoing}
        for edge in edges:
            source, target = edge["from"], edge["to"]
            if source not in outgoing or target not in outgoing:
                raise ValueError("Dangling workflow edge in " + flow["id"])
            outgoing[source].append(target)
            reverse[target].append(source)
        if outgoing["exit"] or len(outgoing["start"]) != 1:
            raise ValueError("Workflow must have one entry and a terminal exit")
        if set(outgoing) != _reachable("start", outgoing):
            raise ValueError("Unreachable stage in " + flow["id"])
        if set(outgoing) != _reachable("exit", reverse):
            raise ValueError("A stage cannot reach exit in " + flow["id"])
        for node_id, node in nodes.items():
            if node["stage"] not in stages:
                raise ValueError("Unknown stage: " + node["stage"])
            stage = stages[node["stage"]]
            executor = stage["executor"]
            node_edges = [edge for edge in edges if edge["from"] == node_id]
            if node.get("workflow") is not None:
                if executor != "handoff" or node["workflow"] not in identifiers:
                    raise ValueError("Invalid shared workflow handoff")
            if executor == "human":
                labels = [edge.get("label", "") for edge in node_edges]
                if len(labels) < 2 or not all(labels) or len(set(labels)) != len(labels):
                    raise ValueError("Human gates require explicit, distinct decision options")
                if not node.get("roles") or node.get("default_choice") is not None:
                    raise ValueError("Human gate requires roles and no default approval")
                if node.get("approval") is True:
                    required = {
                        "actor", "roles", "demand_id", "repository", "head_sha",
                        "base_sha", "artifact_digest", "scope_digest", "policy_version",
                        "workflow_id", "stage_id", "target_branch",
                    }
                    if set(node.get("record_fields", [])) != required:
                        raise ValueError("Approval must be bound to actor, scope and revision")
                    if not any("Revise" in label or "Stop" in label for label in labels):
                        raise ValueError("Approval gate requires a nonapproval path")
            if executor == "condition":
                fallbacks = [edge for edge in node_edges if "condition" not in edge]
                conditions = [edge["condition"] for edge in node_edges if "condition" in edge]
                if len(fallbacks) != 1 or not conditions or len(conditions) != len(set(conditions)):
                    raise ValueError("Conditional stage needs distinct conditions and one fallback")
            if node.get("effect") == "merge" or stage.get("effect") == "merge":
                raise ValueError("Scaffolds must not add an automatic merge action")
        limits = flow.get("limits", {})
        if limits.get("max_repair_attempts") != 2 or limits.get("on_exhaustion") != "human":
            raise ValueError("Workflow must declare bounded repair and human escalation")
        if flow["id"] == "discovery" and any(
            node.get("workflow") in {"verification", "merge-readiness"}
            or node["stage"] == "implement" for node in nodes.values()
        ):
            raise ValueError("Discovery must end in a decision, not implementation or merge")
        if generated:
            for relative, expected in generated_files(project, item, flow, stages).items():
                path = project_path(project, relative)
                if not path.is_file() or path.read_text() != expected:
                    raise ValueError("Generated scaffold is stale: " + relative)
        summaries.append({
            "id": flow["id"], "name": item["name"], "group": item["group"],
            "stages": len(nodes), "human_gates": sum(
                stages[node["stage"]]["executor"] == "human" for node in nodes.values()
            ), "enabled": False, "status": "scaffold",
        })
    return {"workflows": summaries, "execution_enabled": False,
            "agent_invocations": 0, "valid": True}


def dot_quote(value):
    return json.dumps(value, ensure_ascii=False)


def graph_source(flow, stages):
    name = "".join(part.title() for part in flow["id"].split("-"))
    blocked = "printf '%s\\n' " + "'" + SCAFFOLD_MESSAGE + "'; exit 78"
    lines = [
        "// Generated from definition.json. Content and execution bindings are pending.",
        "// Human selections are not authenticated approval records by themselves.",
        "digraph " + name + " {",
        '    graph [default_fidelity="full", default_max_retries=0, '
        'max_node_visits=3, on_failure="exit"]',
        '    start [shape=Mdiamond, label="Start"]',
        '    scaffold_guard [shape=parallelogram, label="Content pending — execution blocked", '
        'script=' + dot_quote(blocked) + ', goal_gate=true, max_retries=0]',
        '    exit [shape=Msquare, label="End / governed handoff"]',
    ]
    nodes = {node["id"]: node for node in flow["nodes"]}
    for node in flow["nodes"]:
        stage = stages[node["stage"]]
        attributes = ["shape=" + SHAPES[stage["executor"]],
                      "label=" + dot_quote(node.get("label", stage["name"]))]
        if stage["executor"] == "agent":
            attributes += [
                'backend="acp"', 'acp.command="false"',
                "prompt=" + dot_quote("@../../" + stage["prompt"]),
                'timeout="12m"', "max_retries=0",
            ]
        elif stage["executor"] in {"script", "handoff"}:
            attributes += ["script=" + dot_quote(blocked), "max_retries=0"]
        if "max_visits" in node:
            attributes.append("max_visits=" + str(node["max_visits"]))
        lines.append("    " + node["id"] + " [" + ", ".join(attributes) + "]")
    lines.append("    start -> scaffold_guard")
    lines.append('    scaffold_guard -> exit [label="Content pending"]')
    for edge in flow["edges"]:
        source = "scaffold_guard" if edge["from"] == "start" else edge["from"]
        values = dict(edge)
        executor = stages[nodes[source]["stage"]]["executor"] if source in nodes else None
        if source == "scaffold_guard" or executor in {"agent", "script", "handoff"}:
            condition = values.get("condition")
            values["condition"] = "outcome=succeeded" + (" && " + condition if condition else "")
        attributes = [
            key + "=" + dot_quote(values[key])
            for key in ("label", "condition") if key in edge
        ]
        if "condition" in values and "condition" not in edge:
            attributes.append("condition=" + dot_quote(values["condition"]))
        suffix = " [" + ", ".join(attributes) + "]" if attributes else ""
        lines.append("    " + source + " -> " + edge["to"] + suffix)
    for node in flow["nodes"]:
        executor = stages[node["stage"]]["executor"]
        if executor != "condition":
            condition = ', condition="outcome!=succeeded"' if executor == "human" else ""
            lines.append("    " + node["id"]
                         + ' -> exit [label="Failed / unanswered"' + condition + "]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generated_files(project, item, flow, stages):
    directory = str(Path(item["definition"]).parent)
    config = (
        '# Generated scaffold; all automatic and manual execution is disabled.\n'
        '_version = 1\n\n[workflow]\nname = ' + dot_quote(item["name"]) + '\n'
        'description = ' + dot_quote(item["description"]) + '\ngraph = "workflow.fabro"\n\n'
        '[run]\ngoal = "Inspect the workflow scaffold; substantive stage content is pending."\n\n'
        '[run.environment]\nid = "dark-factory-local"\n\n'
        '[run.clone]\nenabled = false\n\n[run.run_branch]\nenabled = false\n'
    )
    return {
        directory + "/workflow.fabro": graph_source(flow, stages),
        directory + "/workflow.toml": config,
        directory + "/README.md": workflow_readme(item, flow, stages),
    }


def workflow_readme(item, flow, stages):
    lines = [
        "# " + item["name"], "",
        item["description"], "",
        "**Scaffold only.** Stage content, worker bindings, script implementations",
        "and trusted approval validation are pending. Execution is disabled.", "",
        "```mermaid", "flowchart TD",
        '    start(["Start"])', '    exit(["End / governed handoff"])',
    ]
    for node in flow["nodes"]:
        stage = stages[node["stage"]]
        kind = "Flow" if stage["executor"] == "handoff" else stage["executor"].title()
        label = dot_quote(kind + ": " + node.get("label", stage["name"]))
        if stage["executor"] == "human":
            shape = "{" + label + "}"
        elif stage["executor"] == "condition":
            shape = "{{" + label + "}}"
        else:
            shape = "[" + label + "]"
        lines.append("    " + node["id"] + shape)
    for edge in flow["edges"]:
        label = "|" + dot_quote(edge["label"]) + "|" if edge.get("label") else ""
        lines.append("    " + edge["from"] + " -->" + label + " " + edge["to"])
    lines += [
        "```", "", "## Stage slots", "",
        "| Stage | Executor | Content to add |",
        "|---|---|---|",
    ]
    for node in flow["nodes"]:
        stage = stages[node["stage"]]
        if stage["executor"] == "agent":
            slot = "[Prompt](../../" + stage["prompt"] + ")"
            if stage.get("skill_candidate"):
                slot += "; candidate skill `" + stage["skill_candidate"] + "`"
        elif node.get("workflow"):
            slot = "[Shared flow](../" + node["workflow"] + "/README.md); dispatch binding pending"
        else:
            slot = "Implementation / decision packet pending"
        lines.append("| " + node.get("label", stage["name"]) + " | "
                     + stage["executor"] + " | " + slot + " |")
    lines += [
        "", "Human approval records bind actor and roles to the demand, repository,",
        "head, base, artifact digest, scope digest and policy version. A native",
        "Fabro choice alone does not enforce those records or roles. Records",
        "also identify the workflow, stage and target branch.", "",
        "Repair is limited to two attempts; exhausted or unknown budgets require",
        "a human decision. No automatic merge is defined.", "",
        "Edit `definition.json` for structure and `../../stages/catalog.json`",
        "for shared stage slots. Rebuild derived files with:", "",
        "```bash", "python3 -m dark_factory workflows build", "```", "",
    ]
    return "\n".join(lines)


def build_catalog(project):
    project = Path(project).resolve()
    validate_catalog(project, generated=False)
    catalog, stages, definitions = load_catalog(project)
    written = []
    for item in catalog["workflows"]:
        for relative, content in generated_files(project, item, definitions[item["id"]], stages).items():
            path = project_path(project, relative)
            path.write_text(content)
            written.append(relative)
    validate_catalog(project)
    return {"written": written, "execution_enabled": False, "agent_invocations": 0}


def select_route(project, demand, blast_radius="local", sensitive=False, incomplete=False):
    catalog, _, _ = load_catalog(project)
    policy = read_json(project_path(project, catalog["routing_policy"]))
    demand = policy.get("aliases", {}).get(demand, demand)
    if demand not in policy["routes"]:
        raise ValueError("Unknown demand type; human classification is required")
    if blast_radius not in {"local", "service", "shared", "system"}:
        raise ValueError("Unknown blast radius; human clarification is required")
    if type(sensitive) is not bool or type(incomplete) is not bool:
        raise ValueError("Evidence flags must be booleans")
    if demand == "discovery":
        risk = "Discovery"
    elif sensitive or demand in {"security", "incident"} or blast_radius == "system":
        risk = "R3"
    elif incomplete or demand == "feature" or blast_radius in {"service", "shared"}:
        risk = "R2"
    else:
        risk = "R1"
    return {
        "workflow": policy["routes"][demand], "demand_type": demand,
        "blast_radius": blast_radius, "risk_class": risk,
        "human_gates": policy["classes"][risk]["human_gates"],
        "execution_enabled": False, "agent_invocations": 0,
    }
