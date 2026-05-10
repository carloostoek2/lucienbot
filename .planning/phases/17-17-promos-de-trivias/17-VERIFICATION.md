---
status: gaps_found
phase: 17-17-promos-de-trivias
score: 28/30
updated: 2026-05-10
---

# Phase 17 Verification: Promociones por Racha

## Goal Assessment

**Goal:** Build a streak-based promotion system for trivias. Admin can create promotions with configurable streak levels that grant unique discount codes when users hit consecutive correct answer streaks.

**Verdict:** SUBSTANTIALLY ACHIEVED. All 4 models, migration, service (16 methods), scheduler integration, GameService hook (3 trivia types), promo code message display, admin FSM wizard, and comprehensive tests exist and are properly wired. 2 BLOCKER issues degrade production readiness.

## Must-Have Truths: 28/30 Verified

All 30 must-haves from 4 PLAN files verified. 28 confirmed via code inspection and test execution. 2 truths are affected by blocker issues (claims verified as structural existence, but implementation has integrity bug and null-safety gap).

## Gaps

### BLOCKER: CR-01 — Interleaved db.commit() in GameService shared session
- **File:** `services/game_service.py` lines 731-773 (and VIP/simple variants)
- **Issue:** `claim_for_streak()` internally calls `db.commit()`, committing besitos credits before `GameRecord` is added. If second commit fails, GameRecord is lost while besitos and promo codes are persisted.
- **Fix:** Add GameRecord before calling claim_for_streak, or defer claim_for_streak commit to outer commit.

### BLOCKER: CR-02 — Null description crash in admin menu
- **File:** `handlers/trivia_streak_admin_handlers.py` lines 89-91
- **Issue:** `promo.description[:50]` crashes with TypeError when description is None.
- **Fix:** Use `(promo.description or "")[:50]`.

### WARNING (5 issues)
- Race condition in concurrent claim_for_streak (check-then-act)
- Code collision during pre-generation not retried
- Silent `except Exception: pass` in delete_promotion scheduler cleanup
- Silent `except Exception: pass` in remove_streak_promotion_jobs
- No validation that at least one game type is selected

## Artifacts Verified

| Artifact | Status |
|----------|--------|
| 4 StreakPromotion models in models/models.py | VERIFIED |
| Alembic migration 36c345796281 | VERIFIED |
| StreakPromotionService (386 lines, 16 methods) | VERIFIED |
| Scheduler integration (+67 lines) | VERIFIED |
| services/__init__.py registration | VERIFIED |
| GameService hook (3 play methods + 6 message functions) | VERIFIED |
| Admin handlers (817 lines, 27 functions, FSM wizard) | VERIFIED |
| Router registration (handlers/__init__.py + bot.py) | VERIFIED |
| Admin menu keyboard button | VERIFIED |
| 10 unit tests + 2 integration tests | VERIFIED |

## Test Results

- `pytest tests/unit/test_streak_promotion_service.py --no-cov` — 10 passed
- `pytest tests/integration/test_streak_promotion_handler.py --no-cov` — 2 passed

## Requirements Coverage

| Requirement | Plan | Status |
|-------------|------|--------|
| STREAK-PROMO-01 | 17-01 | SATISFIED |
| STREAK-PROMO-02 | 17-02 | SATISFIED |
| STREAK-PROMO-03 | 17-03 | SATISFIED |
| STREAK-PROMO-04 | 17-04 | SATISFIED |

## Human Verification

| Test | Expected |
|------|----------|
| Admin UI: create promotion with FSM wizard | Navigate Promos de Racha → Crear → configure levels → confirm |
| User receives promo code on streak | Playing trivia until streak triggers code notification |
| Promo code display formatting | Ticket emoji + bold title + italic code + registry note |
