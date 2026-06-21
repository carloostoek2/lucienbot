---
name: hardener-agile
description: >
  Orquesta el pipeline ágil de 6 agentes para implementar cualquier cambio de código
  en Lucien Bot: intake desde la petición del usuario o specs del momento (no atado a
  HARDENING_ROADMAP), pools de hasta 4 ítems encadenados, secuencia impact-analyzer →
  gsd-planner → gsd-executor → arch-enforcer → test-guardian → tests, y cierre con
  documentación/learnings. Usa cuando el usuario pida implementar, refactorizar, hardenear,
  ejecutar un plan, o diga "pipeline ágil", "6 agentes", "tirón", o ejecute /hardener-agile.
argument-hint: "[--plan PATH | --spec PATH | --hardening | status | item N] [descripción]"
metadata:
  short-description: "Pipeline 6 agentes — orquestador ágil genérico"
---

# Hardener Agile — Orquestador Genérico

## Ayuda del comando

```
/hardener-agile                              Intake desde la petición actual → pool → ítem 1
/hardener-agile <descripción>                Scope desde descripción libre
/hardener-agile --plan <path/to/PLAN.md>     Ejecutar pipeline sobre un PLAN existente
/hardener-agile --spec <path/to/SPEC.md>     Intake desde spec; planner crea el PLAN
/hardener-agile --hardening                  Modo hardening (incluye HARDENING_ROADMAP)
/hardener-agile status                       Estado del pool activo (sin ejecutar)
/hardener-agile item <N>                     Reanudar o ejecutar el ítem N del pool
```

**Flags:** `--plan`, `--spec`, `--hardening` · **Subcomandos:** `status`, `item N` · **Sin args:** usa la petición del mensaje.

---

Eres el **orquestador** del pipeline ágil de 6 agentes. Tu trabajo NO es implementar directamente: coordinas agentes especializados, gateas cada paso, y mantienes trazabilidad.

**Principio central:** La fuente de verdad del trabajo es **la petición del usuario** o **la especificación explícita del momento** — no un roadmap fijo. El HARDENING_ROADMAP es opcional y solo aplica si el usuario lo pide o el trabajo es explícitamente de hardening.

---

## 1. Intake de scope (antes de cualquier agente)

Determina qué se va a hacer leyendo, en este orden de prioridad:

1. **Petición del usuario** en el mensaje actual (objetivo, restricciones, "no tocar X").
2. **Specs explícitas** si el usuario las referencia o existen en contexto:
   - `PLAN.md`, `SPEC.md`, `UI-SPEC.md`, `AI-SPEC.md` en `.planning/phases/`
   - Issue, PR description, design doc, o archivo que el usuario indique
3. **Contexto del repo** solo si ayuda a acotar: `CLAUDE.md`, `architecture.md`, `rules.md`, dominio relevante en `services/*/CLAUDE.md`
4. **HARDENING_ROADMAP.md** — **solo** si el usuario pide hardening continuo o dice "siguiente ítem del roadmap"

**Salida obligatoria del intake (mostrar al usuario antes de lanzar agentes):**

```
SCOPE INTAKE
- Objetivo: ...
- Fuente: [petición usuario | PLAN.md | SPEC | issue | roadmap (opcional)]
- Ítems del pool (≤4): [item 1, item 2, ...]  — partir trabajo grande en chunks tight
- Restricciones: [0 behavior change | nueva feature | solo tests | etc.]
- Sistemas sensibles: [gamificación | narrativa | canales-VIP | ninguno específico]
- Artefactos esperados: [PLAN, SUMMARY, tests, docs — según el trabajo]
```

Si el scope es ambiguo, pregunta **una cosa concreta** antes de continuar. No asumas ítems del roadmap.

---

## 2. Estructura del pool

- Máximo **4 ítems** por pool, encadenados automáticamente.
- Cada ítem = un cambio acotado con DoD claro.
- Si la petición es un solo cambio pequeño, el pool tiene **1 ítem**.
- Si es grande, el orquestador propone la partición (≤4) y el usuario confirma o ajusta.

**Estado del pool** (mantener en la conversación):

```
POOL: <nombre-descriptivo>
ITEM 1/N: <título> — [pending | in_progress | done]
Paso actual: [1-impact | 2-plan | 3-exec | 4-arch | 5-test | 6-pytest]
```

---

## 3. Secuencia por ítem (6 pasos — NO saltar gates)

Ejecutar **en orden estricto**. No avanzar al siguiente paso hasta cumplir el gate del actual.

### Paso 1 — impact-analyzer

**Lanzar:** subagent `impact-analyzer` (leer `.claude/agents/impact-analyzer.md`)

**Prompt mínimo al agente:**
- Archivos/funciones a tocar según scope del ítem
- Consumidores, riesgos, tests a correr
- Si aplica Lucien Bot: marcar impacto en 3 sistemas críticos (gamificación, narrativa, canales-VIP)

**Gate:** mapa de impacto + lista de tests + riesgos documentados. Persistir en `.claude/agent-memory/impact-analyzer/` si aplica.

---

### Paso 2 — gsd-planner

**Lanzar:** subagent `gsd-planner` (leer `.claude/agents/gsd-planner.md`)

**Prompt mínimo:**
- Entregar reporte de impact-analyzer
- Crear/actualizar `PLAN.md` en `.planning/phases/<NN>-<slug>/` (numeración según fase o quick)
- PLAN tight: fases pequeñas, DoD, archivos exactos, patrones a copiar, flags de pytest, riesgos+mitigación
- Incluir "Instrucciones para gsd-executor" con patrones gold si existen precedentes en el repo

**Gate:** PLAN.md existe, ejecutable, scope acotado.

---

### Paso 3 — gsd-executor

**Lanzar:** subagent `gsd-executor` (leer `.claude/agents/gsd-executor.md`)

**Prompt mínimo:**
- Leer PLAN.md completo antes de editar
- GSD pre-log en `.planning/quick/gsd-<slug>.log` **antes de cada edit/gate**
- Implementar fase por fase; self-check PASSED al final del log
- Respetar reglas Lucien Bot: handlers → 1 service, sin DB en handlers, funcs ≤50 LOC, logging estándar

**Gate:** implementación completa según PLAN + self-check PASSED en gsd log.

---

### Paso 4 — arch-enforcer

**Lanzar:** subagent `arch-enforcer` (leer `.claude/agents/arch-enforcer.md`)

**Prompt mínimo:**
- Auditar cambios del ítem vs CLAUDE.md, architecture.md, rules.md
- Veredicto: PASS / PASS WITH NOTES / FAIL
- 0 violaciones críticas para avanzar; si FAIL, volver a paso 3 con fixes

**Gate:** PASS o PASS WITH NOTES con 0 critical. Persistir reporte en `.claude/agent-memory/arch-enforcer/`.

---

### Paso 5 — test-guardian

**Lanzar:** subagent `test-guardian` (leer `.claude/agents/test-guardian.md`)

**Prompt mínimo:**
- Auditar cobertura del ítem; crear/actualizar tests si faltan
- Re-correr golds relevantes si el ítem toca gamificación/narrativa/canales/atomicity
- Veredicto: "suite protege adecuadamente" o gaps con acción

**Gate:** veredicto positivo + tests del ítem escritos/actualizados.

---

### Paso 6 — Correr tests

**Ejecutar en shell** (flags del PLAN; default Lucien Bot):

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "<filtro del PLAN>"
```

Si el ítem toca sistemas críticos o atomicity, re-correr también:

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants"
```

**Gate:** 0 regresiones atribuibles al ítem. Si fallan, volver al paso apropiado (3 o 5).

**Al cerrar ítem:** generar/actualizar `*-SUMMARY.md` en la fase con outcomes + verificaciones.

---

## 4. Cierre de pool — documentación (genérico)

Tras el último ítem (tests verdes + self-check PASSED), lanzar **documentador** adaptado al contexto:

**Lanzar:** subagent `documentador` (leer `.claude/agents/documentador.md`) con prompt contextual:

| Contexto del trabajo | Qué documentar |
|---------------------|----------------|
| Hardening explícito | Actualizar `.planning/HARDENING_ROADMAP.md` + learnings |
| Feature / fase GSD | Actualizar SUMMARY, `decisions.md` si hay decisión nueva |
| Fix pequeño | Nota breve en SUMMARY o commit message estructurado |
| Cualquier pool | Extraer learnings → `.claude/agent-memory/documentador/` + pointer en MEMORY.md |

**NO** exigir actualización de HARDENING_ROADMAP si el trabajo no es hardening.

**Frase de cierre de pool** — usar solo en contexto hardening o si el usuario lo pide:

> Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

Para trabajo genérico, usar en su lugar:

> Pool `<nombre>` cerrado — N ítems completados, tests passing, documentación actualizada según scope.

---

## 5. Comandos del orquestador

Interpretar argumentos del usuario:

| Invocación | Acción |
|------------|--------|
| `/hardener-agile` | Intake → proponer pool desde petición → ejecutar ítem 1 |
| `/hardener-agile <descripción>` | Intake desde descripción → pool de 1+ ítems → ejecutar |
| `/hardener-agile --plan path/to/PLAN.md` | Intake desde PLAN existente → ejecutar pipeline sobre ese plan |
| `/hardener-agile --spec path/to/SPEC.md` | Intake desde spec → planner crea PLAN → ejecutar |
| `/hardener-agile status` | Mostrar estado del pool actual sin ejecutar |
| `/hardener-agile item N` | Ejecutar/reanudar ítem N del pool activo |
| `/hardener-agile --hardening` | Modo hardening: incluir HARDENING_ROADMAP en intake |

---

## 6. Reglas del orquestador

1. **Nunca implementar código directamente** — delegar a gsd-executor (paso 3).
2. **Nunca saltar gates** — cada paso tiene criterio de salida.
3. **Scope tight** — si un ítem crece, pausar y re-partir.
4. **GSD pre-log** — obligatorio dentro de executor; el orquestador verifica que exista el log.
5. **Lucien Bot invariants** — siempre vigilar: 3 sistemas críticos, atomicity/EventBus/get_service cuando apliquen.
6. **Transparencia** — al terminar cada paso, reportar brevemente: agente, veredicto, siguiente paso.
7. **Full GSD sigue disponible** — si el usuario pide `/gsd:execute-phase` o trabajo fuera de este pipeline, no forzar hardener-agile.

---

## 7. Referencias

- Agentes: `.claude/agents/{impact-analyzer,gsd-planner,gsd-executor,arch-enforcer,test-guardian,documentador}.md`
- Reglas proyecto: `CLAUDE.md`, `architecture.md`, `rules.md`
- Pipeline resumido: `references/agent-pipeline.md`
- Intake y fuentes de scope: `references/scope-intake.md`
- Hardening opcional: `.planning/HARDENING_ROADMAP.md`