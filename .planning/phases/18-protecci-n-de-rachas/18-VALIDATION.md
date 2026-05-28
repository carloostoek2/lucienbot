---
phase: 18
slug: protecci-n-de-rachas
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -k "streak_session or streak_protection" -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -k "streak_session or streak_protection" -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | D-01 | T-18-01 / N/A | CANCELLED added to enum with lowercase "cancelled" | unit | `pytest tests/ -k "streak_promotion_code" -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | D-03, D-04 | T-18-02 / N/A | StreakSession model with UUID PK, session_id FK on StreakPromotionCode | unit | `pytest tests/ -k "streak_session" -q` | ❌ W0 | ⬜ pending |
| 18-01-07 | 01 | 2 | D-05, D-06, D-07 | T-18-03 / balance | protect_streak() debits besitos atomically with session update in single service method | unit | `pytest tests/ -k "protect_streak" -q` | ❌ W0 | ⬜ pending |
| 18-01-08 | 01 | 2 | D-08, D-13, D-14 | T-18-04 / state | Failed protection cancels all session codes; timeout expires session | unit | `pytest tests/ -k "cancel_session" -q` | ❌ W0 | ⬜ pending |
| 18-01-09 | 01 | 3 | D-10, D-11, D-12 | T-18-05 / state | Retire preserves codes; continue sets risk mode; failure in risk mode cancels all | integration | `pytest tests/ -k "risk_mode" -q` | ❌ W0 | ⬜ pending |
| 18-01-10 | 01 | 3 | D-16, D-17 | T-18-06 / callback | FSM states set correctly; callback data validated; handlers don't break existing trivia | integration | `pytest tests/ -k "trivia_promo" -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_streak_protection.py` — stubs for StreakSession model + protection service logic
- [ ] `tests/test_streak_fsm.py` — stubs for streak FSM state transitions (matches plan Task 0.2)
- [ ] `tests/conftest.py` — shared fixtures (existing infrastructure)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Timeout UX flow | D-13, D-14 | Timer-based interaction requires real Telegram client | Send /trivia_promo, fail a question without besitos, verify 2-min timeout message, wait 2+ min, verify session expired |
| End-to-end retire/continue | D-10, D-11, D-12 | Multi-step FSM with real Telegram callbacks | Play trivia promo to tier, verify choice keyboard appears, test both paths, verify code states in admin panel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
