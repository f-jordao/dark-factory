# Contributing

Keep lifecycle decisions deterministic. Add agent work only at a named stage
with eligibility checks, revision identity and a recorded result.

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m dark_factory demo
python3 -m dark_factory workflows validate
```

For controller changes, cover any affected retry, concurrency, stale-revision
or agent-suppression behavior. Test with offline adapters before writing to GitHub.

The prototype uses Python 3.9+ and the standard library. Configuration and worker
results are JSON. Worker commands are argument arrays, never interpolated shell
strings. Check every publication against the exact reviewed revision.

Do not commit `.dark-factory/`, credentials, local configuration or worker logs.
Describe which parts were tested with a real service and which used fixtures.

For workflow structure, edit `workflows/<name>/definition.json` and the shared
`stages/catalog.json`. Run `python3 -m dark_factory workflows build` to regenerate
graphs, run configurations and visual maps. Keep stage content separate from
structure and do not enable placeholder definitions or automatic merge.
