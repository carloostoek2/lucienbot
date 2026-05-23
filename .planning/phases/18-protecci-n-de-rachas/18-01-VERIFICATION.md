---
phase: 18-protecci-n-de-rachas
verified: 2026-05-23T03:10:00Z
status: human_needed
score: 20/20 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Protection flow in real Telegram"
    expected: "Play trivia (general/VIP/simple), fail a question with active promotion -> protection keyboard appears with cost, accept/decline buttons"
    why_human: "Requires real Telegram bot interaction to verify keyboard rendering and callback routing"
  - test: "Risk mode retire/continue flow"
    expected: "Reach a tier with streak -> retire/continue keyboard appears -> both paths produce correct state (retire preserves codes, continue sets risk mode)"
    why_human: "Multi-step FSM with real Telegram callbacks; requires user interaction to verify"
  - test: "Timeout UX with 2-minute window"
    expected: "Fail a question without enough besitos -> timeout message appears -> after 2 minutes, verify session expired -> codes cancelled"
    why_human: "Timer-based interaction requires real Telegram client and waiting period"
---

# Phase 18: Proteccion De Rachas Verification Report

**Phase Goal:** Extender el sistema de promociones por racha (Phase 17) con: (1) proteccion de racha comprable con besitos al fallar una pregunta, (2) modo arriesgo FSM que permite elegir entre retirarse con codigos actuales o continuar por un codigo mayor arriesgando perderlo todo, (3) timeout de 2 minutos para ganar besitos en trivia libre cuando no se puede pagar la proteccion.

**Verified:** 2026-05-23T03:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

The three core capabilities of Phase 18 are all implemented and verified:

1. **Streak protection purchasable with besitos** — `protect_streak()` method atomically debits besitos and sets `protection_used=True`. Handlers route incorrect answers to protection keyboard when a session is active and balance is sufficient. All service methods tested (11 unit tests all passing).

2. **Risk mode FSM (retire/continue)** — `_build_streak_claim_state()` returns `offer_retire` action on code delivery; `risk_mode_keyboard()` presents retire/continue choices; `handle_streak_retire()` calls `close_session(retire=True)` preserving codes; `handle_streak_continue()` calls `set_risk_mode()` activating risk mode. All transition logic tested (6 integration tests all passing).

3. **2-minute timeout for free trivia** — `_build_streak_failure_state()` sets `session.expires_at = now + 2 minutes` when user cannot afford protection; `get_active_session()` checks expiry on every access and cancels if expired; `_cleanup_expired_streak_sessions()` scheduled job handles stale sessions at 60-minute intervals.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Codes marked CANCELLED excluded from active listings (cannot be redeemed) | Veriefied | `_get_available_code()` filters by `AVAILABLE` status; CANCELLED enum exists; `cancel_session_codes()` marks DELIVERED->CANCELLED |
| 2 | Active trivia session tracks streak lifecycle (risk mode, protection, codes) | Veriefied | `StreakSession` model with all fields; session management methods in `StreakPromotionService` |
| 3 | Delivered codes linked to originating session via `session_id` FK | Veriefied | `claim_for_streak()` sets `code.session_id = session.id`; FK column exists in model and migration |
| 4 | `calculate_protection_cost(streak)` returns correct formula | Veriefied | Code returns `5 + (streak // 3) * 5`; tests confirm `cost(0)=5, cost(3)=10, cost(6)=15` |
| 5 | `claim_for_streak()` links delivered codes to active session | Veriefied | Session created/reused in `claim_for_streak()`; code ID appended to `codes_delivered` JSON |
| 6 | Trivia results include `session_state` when promotion is active | Veriefied | All 3 play methods (trivia, vip, simple) set `session_state` in return dict; 3 matches found |
| 7 | Incorrect answer + active session + sufficient balance -> protection keyboard | Veriefied | `_build_streak_failure_state()` returns `offer_protection` action; handler shows `protection_keyboard`; test verifies action |
| 8 | Incorrect answer + active session + protection_used -> codes cancelled | Veriefied | `_build_streak_failure_state()` cancels codes, returns `cancelled` action; test verifies |
| 9 | `cancel_session_codes()` marks all session DELIVERED codes CANCELLED | Veriefied | Code iterates codes_delivered list, sets status; test verifies transition |
| 10 | `close_session(retire=True)` preserves codes; `retire=False` cancels them | Veriefied | Both paths implemented and tested |
| 11 | Protection accept/decline callbacks routable, trigger correct transitions | Veriefied | 4 callback data classes exist; 4 handler functions route correctly |
| 12 | Retire/continue callbacks routable, trigger correct session mutations | Veriefied | `StreakRetireCallback` + `StreakContinueCallback` routable; handlers exist |
| 13 | Protection and risk-mode keyboards render with correct labels | Veriefied | `protection_keyboard()` and `risk_mode_keyboard()` factory functions exist with correct button text |
| 14 | Protection/risk decisions handled by dedicated callbacks, 1 service each | Veriefied | Each handler delegates to exactly 1 service method; no direct DB access in `handle_protection_accept/decline` |
| 15 | Protection payment atomic: `protect_streak()` in single transaction | Veriefied | `debit_besitos(commit=False)` + `session.protection_used = True` + single `db.commit()` |
| 16 | All new handlers delegate to 1 service, no direct DB, under 50 lines | Veriefied | All 4 new handlers between 18-27 lines; `set_risk_mode()` wraps commit; handlers call `promo_svc.protect_streak()` etc. |
| 17 | Expired sessions cleaned by 60-minute scheduler job | Veriefied | `_cleanup_expired_streak_sessions()` function exists; registered with `IntervalTrigger(minutes=60)` |
| 18 | Existing trivia flow without session produces no `session_state` | Veriefied | `session_state = None` default; test verifies `_build_streak_failure_state(no session) returns None` |
| 19 | All LucienVoice messages use Lucien's voice (3rd person) | Veriefied | 8 message methods use "Lucien", elegant tone, no vulgarity |
| 20 | Phase 18 specific tests all pass | Veriefied | 11/11 protection tests pass; 6/6 FSM tests pass |

**Score:** 20/20 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `models/models.py` | CANCELLED enum, STREAK_PROTECTION enum, StreakSession model, session_id FK | Veriefied | All present at expected lines |
| `services/streak_promotion_service.py` | 6 new methods, modified claim_for_streak | Veriefied | All methods present; imports for json, uuid, StreakSession |
| `services/game_service.py` | _build_streak_failure_state, _build_streak_claim_state, session_state in 3 play methods | Veriefied | All present; timedelta import at line 9 |
| `services/scheduler_service.py` | _cleanup_expired_streak_sessions function + job registration | Veriefied | Function at line 273; job at line 386-391 |
| `handlers/game_user_handlers.py` | TriviaStreakStates, session_state routing in 3 handlers, 4 new callback handlers | Veriefied | All present |
| `keyboards/callback_data.py` | 4 new CallbackData classes | Veriefied | StreakProtectAcceptCallback, StreakProtectDeclineCallback, StreakRetireCallback, StreakContinueCallback |
| `keyboards/inline_keyboards.py` | protection_keyboard, risk_mode_keyboard | Veriefied | Both present with correct buttons |
| `utils/lucien_voice.py` | 8 new message methods | Veriefied | All present with Lucien voice |
| `tests/test_streak_protection.py` | 11 unit tests | Veriefied | All 11 pass |
| `tests/test_streak_fsm.py` | 6 integration tests | Veriefied | All 6 pass |
| `tests/conftest.py` | sample_streak_promotion, sample_streak_session fixtures | Veriefied | Both exist |
| Alembic migrations | Enum migration, table migration, fix migration | Veriefied | 3 migrations exist; head is `20260523_fix_streak_sessions_fk` |

### Key Link Verification

The complete wiring diagram for each scenario:

**Protection flow (incorrect answer + active session + sufficient balance):**

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `trivia_answer` handler | `GameService.play_trivia()` | `get_service(GameService)` | Wired | Line 172 |
| `GameService.play_trivia()` | `_build_streak_failure_state()` | direct call | Wired | Line 799 |
| `_build_streak_failure_state()` | `StreakPromotionService.get_active_session()` | lazy import + call | Wired | Line 826-829 |
| `_build_streak_failure_state()` | `BesitoService.has_sufficient_balance()` | direct import | Wired | Line 839-840 |
| `streak_failure_state` returns `offer_protection` | Handler shows `protection_keyboard()` | session_state dict | Wired | Lines 177-188 |
| `protection_keyboard()` | `StreakProtectAcceptCallback` / `StreakProtectDeclineCallback` | callback_data packing | Wired | Lines 808-815 in inline_keyboards.py |
| `handle_protection_accept` | `StreakPromotionService.protect_streak()` | `get_service(StreakPromotionService)` | Wired | Line 497-498 |
| `handle_protection_decline` | `StreakPromotionService.cancel_session_codes() + close_session()` | `get_service(StreakPromotionService)` | Wired | Lines 518-522 |

**Risk mode flow (correct answer + code claimed):**

| From | To | Via | Status |
| ---- | --- | --- | ------ |
| `trivia_answer` handler | `GameService.play_trivia()` | `get_service(GameService)` | Wired |
| `GameService.play_trivia()` | `claim_for_streak()` | lazy import | Wired |
| `claim_for_streak()` | `_get_or_create_session()` | direct call | Wired |
| `play_trivia()` | `_build_streak_claim_state()` | direct call | Wired |
| `_build_streak_claim_state()` | `StreakPromotionService.get_active_session()` | lazy import | Wired |
| Returns `offer_retire` | Handler shows `risk_mode_keyboard()` | session_state dict | Wired |
| `handle_streak_retire` | `StreakPromotionService.close_session(retire=True)` | get_service pattern | Wired |
| `handle_streak_continue` | `StreakPromotionService.set_risk_mode()` | get_service pattern | Wired |

**Timeout flow (incorrect answer + insufficient balance):**

| From | To | Via | Status |
| ---- | --- | --- | ------ |
| `_build_streak_failure_state()` | Sets `session.expires_at = now + 2 minutes` | direct | Wired |
| Returns `timeout` action | Handler shows `LucienVoice.streak_timeout_granted()` | session_state dict | Wired |
| `get_active_session()` | Checks `expires_at > now`, cancels codes if expired | lazy check | Wired |
| `_cleanup_expired_streak_sessions()` | `SchedulerService` job | 60-min IntervalTrigger | Wired |

**Data model wiring:**

| From | To | Via | Status |
| ---- | --- | --- | ------ |
| `StreakSession.codes` | `StreakPromotionCode.session` | SQLAlchemy relationship | Wired |
| `StreakPromotionCode.session_id` | `streak_sessions.id` | FK constraint | Wired |
| `StreakSession.promotion_id` | `streak_promotions.id` | FK constraint | Wired (fix migration applied) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `streak_promotion_service.py:claim_for_streak()` | `session.codes_delivered` | DB query + json.dumps | YES — real DB read/write | Flowing |
| `game_service.py:_build_streak_failure_state()` | `session_state` dict | DB query via `get_active_session()` | YES — depends on StreakSession row | Flowing |
| `game_service.py:_build_streak_claim_state()` | `session_state` dict | DB query via `get_active_session()` | YES — depends on StreakSession row | Flowing |
| `handlers/game_user_handlers.py:trivia_answer()` | `session_state` | `result.get('session_state')` from `play_trivia()` | YES — passes through from service | Flowing |
| `handlers/game_user_handlers.py:handle_streak_retire()` | `codes_delivered` JSON | DB via `session.codes_delivered` | YES — real DB query | Flowing |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| protection cost calculation | `python3 -c "from services.streak_promotion_service import StreakPromotionService; svc=StreakPromotionService(None); print(svc.calculate_protection_cost(0), svc.calculate_protection_cost(3), svc.calculate_protection_cost(6))"` | `5 10 15` | Pass |
| Python imports (all models) | `python3 -c "from models.models import StreakSession, StreakPromotionCodeStatus, TransactionSource; print(StreakPromotionCodeStatus.CANCELLED.value, TransactionSource.STREAK_PROTECTION.value)"` | `cancelled streak_protection` | Pass |
| Alembic migration head | `python3 -m alembic current` | `20260523_fix_streak_sessions_fk (head)` | Pass |
| Protection test suite | `python3 -m pytest tests/test_streak_protection.py -q --no-cov` | 11 passed | Pass |
| FSM test suite | `python3 -m pytest tests/test_streak_fsm.py -q --no-cov` | 6 passed | Pass |
| Callback serialization | `python3 -c "from keyboards.callback_data import StreakProtectAcceptCallback, StreakContinueCallback; print(StreakProtectAcceptCallback(streak=3, question_idx=1).pack(), StreakContinueCallback().pack())"` | `streak_protect_accept:3:1 streak_continue` | Pass |
| Keyboard factories | `python3 -c "from keyboards.inline_keyboards import protection_keyboard, risk_mode_keyboard; print(len(protection_keyboard(10,3,1).inline_keyboard), len(risk_mode_keyboard().inline_keyboard))"` | `2 2` | Pass |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| STREAK-PROT-01 | PLAN 18-01 | CANCELLED enum in StreakPromotionCodeStatus | Satisfied | Line 1146 in models.py |
| STREAK-PROT-02 | PLAN 18-01 | STREAK_PROTECTION in TransactionSource | Satisfied | Line 179 in models.py |
| STREAK-PROT-03 | PLAN 18-01 | StreakSession model with all fields | Satisfied | Lines 1232-1245 in models.py |
| STREAK-PROT-04 | PLAN 18-01 | session_id FK on StreakPromotionCode | Satisfied | Line 1210 in models.py; fix migration for promotion_id FK |
| STREAK-PROT-05 | PLAN 18-01 | start_session() (as _get_or_create_session) | Satisfied | Lines 264-284 in streak_promotion_service.py |
| STREAK-PROT-06 | PLAN 18-01 | claim_for_streak() links codes to session | Satisfied | Lines 212-217 in streak_promotion_service.py |
| STREAK-PROT-07 | PLAN 18-01 | calculate_protection_cost() formula | Satisfied | Lines 233-238, tests verify 5/10/15 |
| STREAK-PROT-08 | PLAN 18-01 | protect_streak() atomic debit + protection | Satisfied | Lines 286-322; commit=False + single commit |
| STREAK-PROT-09 | PLAN 18-01 | cancel_session_codes() marks DELIVERED->CANCELLED | Satisfied | Lines 324-346; returns count |
| STREAK-PROT-10 | PLAN 18-01 | close_session(retire=True/False) both paths | Satisfied | Lines 348-364; both paths tested |
| STREAK-PROT-11 | PLAN 18-01 | play_trivia methods return session_state | Satisfied | All 3 methods include `'session_state': session_state` in return dict |
| STREAK-PROT-12 | PLAN 18-01 | TriviaStreakStates StatesGroup | Satisfied | Lines 41-43 in game_user_handlers.py (2 states, in_timeout handled via lazy verification per PLAN) |
| STREAK-PROT-13 | PLAN 18-01 | trivia_answer handlers extended with protection logic | Satisfied | All 3 handlers route session_state actions |
| STREAK-PROT-14 | PLAN 18-01 | Handlers for protection accept/decline | Satisfied | Lines 487-529 in game_user_handlers.py |
| STREAK-PROT-15 | PLAN 18-01 | Handlers for retire/continue | Satisfied | Lines 532-566 in game_user_handlers.py |
| STREAK-PROT-16 | PLAN 18-01 | Timeout with expires_at and lazy verification | Satisfied | Lines 848-849 (set timeout), Lines 247-261 (check) in game_service.py |
| STREAK-PROT-17 | PLAN 18-01 | LucienVoice messages for protection/risk/timeout | Satisfied | 8 methods at lines 965-1035 in lucien_voice.py |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| ---- | ------- | -------- | ------ |
| `keyboards/callback_data.py:620-628` | Dead `question_idx` field in callback classes | Warning | Bloating callback data with unused field |
| `tests/conftest.py` | Hardcoded Termux path at line 13 | Warning | Pre-existing; tests only run on developer's machine |
| `tests/conftest.py` | Duplicate fixture definitions | Warning | Pre-existing; not introduced by Phase 18 |
| `handlers/game_user_handlers.py:41-43` | TriviaStreakStates FSM states defined but never used for state transitions | Info | Design decision; routing via callback filters works correctly |
| `handlers/game_user_handlers.py` | `claimed_in_risk` action not explicitly handled | Info | Falls through to normal message display; works correctly |

No BLOCKER anti-patterns found. No TODO/FIXME/placeholder stubs in new code. No empty implementations. All functions within 50-line limit (new code). CR-01, WR-01, WR-05, IN-02 from code review were all fixed in commit `5d51f28`.

### Human Verification Required

These items require real Telegram bot interaction and cannot be fully verified through code inspection or unit tests:

#### 1. Protection keyboard flow

**Test:** Play a round of trivia (general, VIP, or simple) with an active promotion. Answer incorrectly.
**Expected:** Protection keyboard appears with two buttons: "Proteger (-{cost} besitos)" and "No proteger". Both buttons route correctly to accept/decline handlers.
**Why human:** Keyboard rendering and callback routing requires real Telegram client.

#### 2. Risk mode retire/continue flow

**Test:** Continue playing after reaching a streak tier. Verify retire/continue keyboard appears. Test both paths: (a) "Retirarse y conservar codigos" preserves codes, (b) "Continuar" sets risk mode and asks next question.
**Expected:** Both paths produce correct session mutations. Admin panel shows preserved codes after retire.
**Why human:** Multi-step FSM interaction with real Telegram callbacks.

#### 3. Timeout UX with 2-minute window

**Test:** Fail a trivia question without sufficient besitos for protection. Verify timeout message. Wait 2+ minutes, then interact again.
**Expected:** Session is expired, codes cancelled, user can start fresh.
**Why human:** Timer-based behavior requires waiting; end-to-end UX feedback.

### Gaps Summary

No gaps found. All 20 must-haves are verified through code inspection, test execution, and behavioral spot-checks. The remaining items flagged for human verification are standard Telegram UI flows that require real bot interaction.

Three minor warnings exist (dead `question_idx` field, hardcoded conftest path — pre-existing, duplicate fixtures — pre-existing) but none block the phase goal.

Full test suite shows 44 failed tests, but these are all pre-existing failures in unrelated domains (alembic environment-specific path, reward service, store service, daily gift, rate limit middleware, error handler middleware). The 17 Phase 18-specific tests all pass. No Phase 18 regression was introduced.

---

_Verified: 2026-05-23T03:10:00Z_
_Verifier: Claude (gsd-verifier)_
