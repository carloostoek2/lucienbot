---
phase: 17
slug: 17-promos-de-trivias
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 17 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest -x tests/unit/ -q` |
| **Full suite command** | `pytest -x tests/ --ignore=tests/e2e -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x tests/unit/test_streak_promotion_service.py tests/unit/test_game_service.py -q`
- **After every plan wave:** Run `pytest -x tests/ --ignore=tests/e2e -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-T0 | 01 | 0 | STREAK-PROMO-01 | — | Wave 0 test stubs for StreakPromotionService and admin handler tests | unit | `pytest tests/unit/test_streak_promotion_service.py tests/integration/test_streak_promotion_handler.py -q` | ❌ W0 | ⬜ pending |
| 17-01-T1 | 01 | 1 | STREAK-PROMO-01 | T-17-03, T-17-04 | 4 models (StreakPromotion, StreakPromotionLevel, StreakPromotionCode, StreakPromotionRedemption) with unique constraints and relationships | unit | `python3 -c "from models.models import StreakPromotion, StreakPromotionLevel, StreakPromotionCode, StreakPromotionRedemption; print('OK')"` | ❌ | ⬜ pending |
| 17-01-T2 | 01 | 1 | STREAK-PROMO-01 | — | Idempotent Alembic migration creating all 4 tables with indices and constraints | integration | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` | ❌ | ⬜ pending |
| 17-02-T0 | 02 | 0 | STREAK-PROMO-02 | — | StreakPromotionService registered in services/__init__.py | unit | `python3 -c "from services import StreakPromotionService; print('OK')"` | ❌ | ⬜ pending |
| 17-02-T1 | 02 | 1 | STREAK-PROMO-02 | T-17-03, T-17-04, T-17-05, T-17-07 | StreakPromotionService with create_promotion, claim_for_streak, activate/deactivate, code generation via secrets.token_hex(6) | unit | `pytest tests/unit/test_streak_promotion_service.py -q` | ❌ W0 | ⬜ pending |
| 17-02-T2 | 02 | 2 | STREAK-PROMO-02 | T-17-06, T-17-07 | Scheduler job handlers for auto-activation/deactivation with DateTrigger jobs and orphan cleanup | integration | `python3 -c "from services.scheduler_service import _activate_streak_promotion, _deactivate_streak_promotion; print('OK')"` | ❌ | ⬜ pending |
| 17-03-T0 | 03 | 0 | STREAK-PROMO-03 | — | Wiring: admin menu button + handlers/__init__.py router registration + bot.py dispatcher include | integration | `grep -n "trivia_streak_admin_router" handlers/__init__.py bot.py` | ❌ | ⬜ pending |
| 17-03-T1 | 03 | 1 | STREAK-PROMO-03 | T-17-05 | GameService hook: claim_for_streak() in all 3 play methods + promo_code_line surfaced in displayed message via _build_*_message_parts + _build_*_message (D-14) | unit | `python3 -c "import ast; ..." (AST check for 3+ claim_for_streak calls + 6+ promo_code_line refs)` | ❌ | ⬜ pending |
| 17-03-T2 | 03 | 1 | STREAK-PROMO-03 | T-17-01, T-17-02 | Admin FSM wizard with is_admin() on all callback handlers, callback data validation | integration | `python3 -c "from handlers.trivia_streak_admin_handlers import router, StreakPromotionStates; print('OK')"` | ❌ | ⬜ pending |
| 17-04-T1 | 04 | — | STREAK-PROMO-04 | T-17-03, T-17-04, T-17-05 | 10 unit tests covering: create with levels, claim delivers code, duplicate prevention (D-15), code uniqueness (D-11), inactive promo (D-06), available count (D-13), dates/relative modes (D-05), activation/deactivation, GameService hook integration | unit | `pytest tests/unit/test_streak_promotion_service.py -x -v -q` | ❌ W0 | ⬜ pending |
| 17-04-T2 | 04 | — | STREAK-PROMO-04 | T-17-01 | 2+ integration tests: admin menu button presence, service method availability | integration | `pytest tests/integration/test_streak_promotion_handler.py -x -v -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_streak_promotion_service.py` -- stubs for StreakPromotionService
- [ ] `tests/integration/test_streak_promotion_handler.py` -- stubs for admin handlers
- [ ] `tests/unit/test_game_service.py` -- extend with streak promotion hook tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin UI: crear promocion con niveles | STREAK-PROMO-03 | Telegram UI interaction | /admin -> Promos de Racha -> Crear -> configurar niveles -> verificar en DB |
| Usuario recibe codigo al alcanzar racha | STREAK-PROMO-02 | End-to-end streak flow | Jugar trivia hasta alcanzar racha configurada, verificar notificacion y codigo |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
