---
phase: 10
slug: flujos-de-entrada-docs-req-fase10-md
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/ -q` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -q`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | free-delay | unit | `pytest tests/unit/test_channel_service.py -q` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 1 | vip-entry-model | unit | `pytest tests/unit/ -k user -q` | ✅ | ⬜ pending |
| 10-03-01 | 03 | 2 | scheduler-interval | unit | `pytest tests/unit/test_scheduler.py -q` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 2 | vip-handlers | unit | `pytest tests/unit/test_handlers.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_scheduler.py` — stubs for scheduler trigger verification
- [ ] `tests/unit/test_handlers.py` — stubs for VIP entry handler verification
- [ ] Existing `tests/conftest.py` covers shared fixtures from Phase 8

*Wave 0 needed for scheduler trigger config and handler callback routing tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Free channel 30s delay feels right | free-delay | Telegram timing is hard to automate in CI | 1) Request access to free channel. 2) Wait 30s. 3) Verify ritual message arrives with social buttons. |
| VIP 3-stage flow narrative | vip-ritual | UX/flow verification requires human judgment | 1) Redeem token. 2) Verify Fase 1 message + Continuar button. 3) Click through to Fase 3. 4) Verify invite link delivery. |
| Free welcome message on approval | free-welcome | Requires actual Telegram group join | 1) Approve pending request. 2) Verify welcome ritual message is sent with invite link. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
