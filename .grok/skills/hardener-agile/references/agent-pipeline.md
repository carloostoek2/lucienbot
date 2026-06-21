# Pipeline de 6 Agentes — Referencia Rápida

## Secuencia (por ítem)

```
impact-analyzer → gsd-planner → gsd-executor → arch-enforcer → test-guardian → pytest
```

## Gates resumidos

| Paso | Agente | Gate de salida |
|------|--------|----------------|
| 1 | impact-analyzer | Mapa impacto + tests + riesgos |
| 2 | gsd-planner | PLAN.md ejecutable |
| 3 | gsd-executor | Código + self-check PASSED + gsd log |
| 4 | arch-enforcer | PASS / PASS WITH NOTES (0 critical) |
| 5 | test-guardian | "suite protege adecuadamente" |
| 6 | shell pytest | 0 regresiones atribuibles |

## Lanzar subagent (patrón)

Usar herramienta Task con `subagent_type: generalPurpose` o el tipo apropiado, prompt que incluya:

1. Rol del agente (copiar de `.claude/agents/<nombre>.md`)
2. Scope del ítem actual
3. Artefactos previos (reporte impact, PLAN, etc.)
4. Criterio de salida explícito

## Rollback por fallo

| Falla en | Volver a |
|----------|----------|
| arch-enforcer FAIL | gsd-executor (paso 3) |
| test-guardian gaps | gsd-executor o test-guardian |
| pytest red | paso 3 o 5 según naturaleza del fallo |
| impact muestra scope inválido | intake (redefinir ítem) |

## Post-pool

Documentador con prompt contextual (no siempre ROADMAP).