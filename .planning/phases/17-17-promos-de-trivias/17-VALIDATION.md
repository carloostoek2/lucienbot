---
phase: 17
slug: 17-promos-de-trivias
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 17 — Validation Strategy

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
| 17-01-01 | 01 | 1 | STREAK-PROMO-01 | T-17-01 / — | Admin-only access via is_admin() | unit | `pytest tests/unit/test_streak_promotion_service.py -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | STREAK-PROMO-01 | — | Idempotent migration | integration | `alembic upgrade head && alembic downgrade -1` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 2 | STREAK-PROMO-02 | T-17-03 / — | GameService integration, streak hook | unit | `pytest tests/unit/test_game_service.py -q` | ✅ | ⬜ pending |
| 17-01-04 | 01 | 3 | STREAK-PROMO-03 | T-17-01 / T-17-02 | Admin auth + callback validation | integration | `pytest tests/integration/test_streak_promotion_handler.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_streak_promotion_service.py` — stubs for StreakPromotionService
- [ ] `tests/integration/test_streak_promotion_handler.py` — stubs for admin handlers
- [ ] `tests/unit/test_game_service.py` — extend with streak promotion hook tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin UI: crear promoción con niveles | STREAK-PROMO-03 | Telegram UI interaction | /admin → Promos de Racha → Crear → configurar niveles → verificar en DB |
| Usuario recibe código al alcanzar racha | STREAK-PROMO-02 | End-to-end streak flow | Jugar trivia hasta alcanzar racha configurada, verificar notificación y código |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
