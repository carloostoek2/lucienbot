# Scope Intake — Fuentes y Prioridad

## Orden de prioridad (genérico)

1. **Mensaje del usuario** — siempre primero
2. **Spec/plan explícito** — si referenciado
3. **Contexto repo** — para invariantes y convenciones
4. **HARDENING_ROADMAP** — solo con `--hardening` o petición explícita

## Fuentes válidas de especificación

| Fuente | Cuándo usar |
|--------|-------------|
| Petición en chat | Default; cualquier implementación |
| `.planning/phases/*/PLAN.md` | Plan ya existe; `--plan` |
| `.planning/phases/*/SPEC.md` | Spec sin plan; planner crea PLAN |
| Issue / PR / design doc | Usuario pasa path o contenido |
| `HARDENING_ROADMAP.md` | Modo `--hardening` únicamente |

## Partir trabajo en ítems (≤4)

Heurística para el orquestador:

- **1 ítem:** fix puntual, un handler, un test file
- **2 ítems:** feature con service + handlers
- **3-4 ítems:** feature multi-dominio, refactor con fases, batch de deuda

Cada ítem debe tener:
- Título corto
- Archivos principales
- DoD verificable
- 0 dependencia circular con otros ítems del pool (o orden explícito)

## Preguntas de clarificación (una a la vez)

Usar solo si falta información crítica:

- ¿Es cambio de comportamiento o solo refactor/hardening (0 behavior)?
- ¿Hay spec/plan existente o partimos de cero?
- ¿Algún sistema que NO debe tocarse?
- ¿Tests obligatorios o smoke suficiente?

## Restricciones Lucien Bot (cuando aplica)

Siempre vigilar aunque el scope sea genérico:

- handlers → exactamente 1 service call
- sin acceso DB fuera de models
- funciones ≤50 líneas
- logging: `módulo | acción | user_id | resultado`
- 3 sistemas críticos: gamificación, narrativa, canales-VIP