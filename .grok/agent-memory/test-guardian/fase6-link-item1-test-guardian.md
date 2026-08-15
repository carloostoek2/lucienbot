# Test-Guardian Report: Item 1 — Lucien emisor (Fase 6 link, Part A)

**Verdict:** suite protege adecuadamente — con 4 tests nuevos añadidos por test-guardian (gaps del contrato cubiertos, sin commitear).

## Coverage Audit

**Cubre (contrato A1-A5):**
- (a) flag OFF → no send: `test_notify_vip_kicked_disabled_does_not_send` (notifier) + `test_business_connection_handler_disabled_is_noop` (handler guard, NUEVO).
- (b) flag ON → payload `[LINK]` exacto: `test_notify_vip_kicked_enabled_sends_exact_link_payload` — `[LINK] ` + JSON one-line con `v=1`, `event=vip_kicked`, `username` con "@", `channel_id`, `channel_name`, `reason`, `ts`, `user_id`.
- (c) send raise → swallow: `test_notify_vip_kicked_send_error_is_swallowed` (no propaga, no rompe flujo).
- (d) event_id uuid4 fresco por evento: `test_notify_vip_kicked_event_id_fresh_per_event`.
- (e) `_fetch_enabled_business_connection_id`: fila → id (`..._returns_most_recent_enabled`) y sin filas → None (`..._returns_none_when_empty`), ambos con SQLite in-memory REAL (`db_session`).
- (f) helper puro `build_vip_kicked_payload`: `test_build_vip_kicked_payload_builds_contract_dict` (NUEVO) — keys exactas, `ts` int, username/channel_name raw.
- Upsert idempotente real: `test_upsert_business_connection_inserts_then_updates` (NUEVO) — inserta y actualiza misma fila (no duplica), DB in-memory real.
- Handler ON → 1 service → fila persistida: `test_business_connection_handler_enabled_persists_row` (NUEVO).

**Falta (residual, fuera del DoD A5):**
- Assertión directa de las 3 emisiones post-ban (A4): los golds de `test_vip_service.py`/`test_scheduler.py` ejercitan los branches sin romper (emit = no-op, no patchan `schedule_emit`) pero no asertan que el emit ocurre SOLO en ban real. Verificado por arch-audit + grep (3 sitios) + no-regresión de golds. Añadir asserts exigiría patchear `schedule_emit` en servicios, fuera del scope del ítem.
- Orden de registro del listener vs startup check (A3): verificado por lectura de `bot.py` (L235 register ANTES de L237 check) y arch-audit; sin test de orden dedicado.

## Mock Audit

| Archivo | Mock / patch | Clasificación | Path de negocio | Acción |
|---------|--------------|---------------|-----------------|--------|
| tests/unit/test_link_notifier.py:40,72,84 | `mock_bot` (AsyncMock de Bot Telegram) | PERMITIDO | borde externo (Telegram) | ninguna |
| :42,74,86 | `monkeypatch _fetch_enabled_business_connection_id → "bc_test"` | PERMITIDO | precondición "bc habilitado existe" para testear payload; el fetch real se testea en :90/:100 con DB real | ninguna |
| :75 | `mock_bot.send_message = AsyncMock(side_effect=Exception)` | PERMITIDO | borde externo levantando error → testea swallow | ninguna |
| :139 | `bch.bot_config.FEATURE_LINK_ENABLED = False` | PERMITIDO (control de config) | guard del handler | ninguna |
| :140-141 | `bch.LinkNotifier.upsert_business_connection = MagicMock()` | PERMITIDO | assert de NO-call en guard OFF (no sustituye lógica) | ninguna |
| :157 | `bch.bot_config.FEATURE_LINK_ENABLED = True` | PERMITIDO (control de config) | handler ON → upsert real | ninguna |
| :158,178 | `link_notifier.get_db_session → _session_ctx(db_session)` | PERMITIDO (inyección) | cablea sesión SQLite in-memory REAL; no sustituye lógica | ninguna |

**Resumen mocks:** 7 permitidos, 0 prohibidos en scope del ítem.
**Confianza de realidad:** alta — la lógica bajo test (`notify_vip_kicked`, `build_vip_kicked_payload`, `upsert_business_connection`, `_fetch_enabled_business_connection_id`) se ejercita SIEMPRE real; los únicos mocks son borde externo (Telegram), precondición documentada y control de flag; los helpers de DB se prueban contra SQLite in-memory real.

## Re-run Results

- Golds `test_link_notifier.py + test_vip_service.py + test_scheduler.py`: 99 passed, 3 xfailed (95 + 4 nuevos).
- Smoke `tests/unit/`: 750 passed, 10 xfailed (746 + 4 nuevos) — baseline + nuevos, 0 regresiones.
- `tests/integration/test_alembic_heads.py`: 4 passed (single head confirmado, A1).

## Pre-existing vs Attributable

- 3 xfailed en test_vip_service.py: pre-existentes (xfail marcado), no regresión.
- SAWarning `transaction already deassociated` + RuntimeWarning `emit never awaited` en golds: pre-existentes (mismo warning en runs del executor y del arch-enforcer), cosmet.
- 0 fallos atribuibles al ítem.

## Handoff

Listo para cierre. Los 4 tests nuevos (`test_link_notifier.py`) quedan sin commitear para el commit gate / review loop. Residuales documentados: assert directo de A4 (3 emisiones) y test de orden A3 — fuera del DoD, no inflar el ítem.
