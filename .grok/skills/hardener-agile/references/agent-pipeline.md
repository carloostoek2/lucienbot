# Pipeline — Lucien Bot (extensión)

Base genérica: `~/.grok/skills/hardener-agile/references/agent-pipeline.md`

## Tests gold Lucien (re-correr si toca sistemas críticos)

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants"
```

## Memoria del proyecto

Preferir `.claude/agent-memory/<agent>/` (versionado con el repo) además de `.grok/agent-memory/`.