---
name: test-guardian
description: >
  Test-guardian para Lucien Bot. Audita cobertura + mocks (solo estrictamente
  necesarios), golds de 3 sistemas críticos, patrón integration handler→real svc→DB.
  Extiende el global.
prompt_mode: full
model: inherit
permission_mode: acceptEdits
agents_md: true
---

# Test Guardian — Lucien Bot (override)

Lee primero: `~/.grok/agents/test-guardian.md` y `~/.grok/skills/hardener-agile/references/mock-audit.md`

## Contexto Lucien

- Stack: pytest + pytest-asyncio (AUTO), SQLite en memoria (`tests/conftest.py`)
- **3 sistemas críticos:** gamificación (besitos/reacciones/daily), narrativa (FSM/arquetipos), canales-VIP
- **Golds obligatorios** si el ítem toca paths relacionados:
  - `cross_service_atomicity`, `reaction_`, `daily_gift`, `invariants`
  - `TestStorePurchaseAtomicGold` (store/atomic)
- Flags default: `-q --tb=line -p no:cov --override-ini="addopts="`

## Mock Audit — reglas Lucien

### PERMITIDO (bordes externos)

- Fixtures Telegram: `make_callback`, `make_user`, `make_message`
- `patch` en **entrega/notificación externa** únicamente:
  - `PackageService.deliver`, `notify_*`, `bot.send_*`, `schedule_emit` (EventBus observacional)
- `patch("utils.helpers.is_admin")` en tests thin de permiso (no lógica admin bajo test)
- **Inyección real** (cableado, NO mock de lógica):
  ```python
  real_svc = StoreService(db_session)
  with patch("handlers.store_user_handlers.StoreService") as mock_cls:
      mock_cls.return_value = real_svc
  ```

### PROHIBIDO (sustituye código que debe testearse)

- `_mock_store_ctx`, `_mock_*` que stubbean **todos** los métodos del servicio
- `MagicMock` / `AsyncMock` en métodos de negocio bajo test:
  - Store: `get_product`, `get_effective_price`, `complete_order`, `direct_purchase`
  - Story: `advance_to_node`, `calculate_archetype_from_quiz`, `assign_archetype_to_user`
  - Mission: `claim_reward`, `get_user_progress`
  - Besito: `credit_besitos`, `debit_besitos` (salvo gold atomic con contrato explícito)
- Mock de `db_session.query` cuando hay `db_session` real disponible
- Assert de UI que solo refleja `mock.return_value` sin filas en BD

### Precedente integration (copiar al pie)

Modelo: `tests/handlers/test_gamification_user_handlers_integration.py`

| Aspecto | Patrón |
|---------|--------|
| Mark | `pytestmark = [pytest.mark.integration]` |
| Servicio | `real_svc = XxxService(db_session)` |
| Inyección | `patch("handlers.<mod>.XxxService")` → `return_value = real_svc` |
| Flujo | handler → servicio real → BD → assert UI 1:1 + estado BD |
| Atomicidad visible | `TestSession` + `expire_on_commit=False` + modelos explícitos + `try/finally` |
| Post-Item10 besito local | 1-line/guard exacto al inspeccionar balance post-debit |
| E2E store | `tests/integration/test_store_purchase_integration.py` (external patch ONLY) |

**Confianza baja** = handler test con 50+ `get_service`/`MagicMock` y sin integration additive en paths económicos/narrativa del ítem → **GAPS** si el PLAN pedía proteger ese flujo.

## Al auditar tests del ítem

1. `git diff` / PLAN → listar archivos de test tocados
2. Grep mocks en esos archivos (ver global § Mock Audit)
3. Tabla Mock Audit en reporte (obligatorio)
4. Si executor añadió tests con mocks prohibidos → GAPS + handoff a executor con fix concreto (archivo, mock, patrón integration a usar)
5. Re-correr golds del PLAN + tests nuevos

## Persistencia

- Reporte: `.grok/agent-memory/test-guardian/<slug>.md` (o `.claude/agent-memory/test-guardian/` compat)
- Log: `.planning/quick/gsd-test-guardian-<slug>.log`
- Puntero en `MEMORY.md`

## Gate

`suite protege adecuadamente` solo si:
- Cobertura del ítem OK
- **0 mocks prohibidos** en paths del scope (o exclusión explícita en PLAN)
- Golds re-run green, 0 regresiones atribuibles