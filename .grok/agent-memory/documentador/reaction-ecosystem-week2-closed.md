# Tirón / Pool Documentation Report (documentador) — reaction-ecosystem-week2

**Tirón context:** Hardener-agile effort=5, Item 2 of reaction pool of 4 — Week 2 broadcast reaction ecosystem tests + docs + debt closure (sistema crítico #1 gamification). Builds on Week 1 closed. Source of truth: PLAN + SUMMARY + gsd log + impact/arch/test-guardian reports. 0 production code changes by documentador.

**Date:** 2026-07-06  
**Agent:** documentador (post-item close; per `.grok/agents/documentador.md`)

**Sources (truth, no invention):**
- `.planning/quick/20260706-reaction-ecosystem-week2/{PLAN.md, SUMMARY.md}`
- `.planning/quick/gsd-reaction-ecosystem-week2.log`
- `.grok/agent-memory/{impact-analyzer,arch-enforcer,test-guardian}/reaction-ecosystem-week2.md`
- `.grok/agent-memory/documentador/reaction-ecosystem-week1-closed.md` (Week 1 baseline)

**Item (2/4 — Week 2 tests + docs + debt; reaction ecosystem hardening cluster Week 1+2 complete):**
- **Markup parity goldens:** `tests/unit/test_broadcast_channel_markup.py` — `_markup_structure()` helper + 4 tests lock send vs refresh identical structure (callbacks, row order, extra URL); text parity at zero counts; text differs only when N>0.
- **`message_id=0` test:** `test_message_mismatch_when_broadcast_stuck_at_message_id_zero` in `TestCheckAndRegisterReaction` — documents `tracking_failed` persistence (`message_id=0`); real TG `message_id` → `message_mismatch`; no `BroadcastReaction` row created.
- **full_chain migration:** `tests/integration/test_reaction_full_chain.py` — replaced pre-Week-1 handler mirror (`check_and_register_reaction` + manual `reactions_keyboard_with_counts`) with `process_channel_reaction` (Week 1 debt closed).
- **CLAUDE.md rewrite:** `services/broadcast/CLAUDE.md` — production paths (`process_channel_reaction`, `check_and_register_reaction`), return dict contract, validators, markup, message ID tracking, atomicity notes; `register_reaction` marked DEPRECATED legacy sync.
- **`credit_besitos` defer:** `decisions.md` entry — DEFER `credit_besitos(commit=False)`; split-tx intentional per Item 6; atomicity gold blast-radius; revisit only on production orphan-row incident.

**Outcomes + Verifs:**
- **Tests:** **117 green** (gold suite: markup 15p, reaction_flow 28p, full_chain 2p, cross 10p, invariants 1p, mission 4p, limit 3p, gamif -k reaction 23p, callbackdata 31p; broader smoke 106p). 0 failures.
- **Arch-enforcer:** **PASS**, **0 critical violations**. Week 2: tests + docs + decisions defer only; no production code changes; CLAUDE.md matches frozen production paths.
- **Test-guardian:** **"suite protege adecuadamente"**. Gate 45p (markup 15 + reaction_flow 28 + full_chain 2). Mock audit PASS.
- **Constraints:** 0 production code changes; 0 user-visible behavior; 0 atomicity change; EventBus observer untouched; Ruff clean.

**3 crit + contracts:**
- **Gamification (primary):** Tests+docs only; reaction credit/atomicity golds green unchanged; markup parity regression-locked; `message_id` validation contract tested+documented.
- **Narrative / Channel-VIP:** 0 direct impact.
- **Contracts:** get_service 1 call preserved (frozen); EventBus MUST NOT observer untouched; return dict contract documented; `credit_besitos(commit=False)` explicitly deferred.

**Metrics:**
- Files: 4 edited (3 test files, CLAUDE.md, decisions.md) + gsd log; **0 prod files**
- Tests added: 4 parity goldens + 1 message_id=0 + full_chain migration (2 tests updated)
- Arch: PASS 0 crit
- GSD: `gsd-reaction-ecosystem-week2.log` (5 tasks + SELF_CHECK PASSED)

**Learnings / Patterns:**
- **Parity golden tests** lock send/refresh structural contract without prod edits — if parity fails, test documents regression; do not "fix" prod in Week 2 scope.
- **`message_id=0` guard** ties `tracking_failed` persistence to `message_mismatch` validator — documents intentional strictness (do NOT relax `validate_broadcast_context_match`).
- **full_chain migration** closes Week 1 integration debt — integration tests must mirror production `process_channel_reaction` path, not deprecated handler orchestration.
- **`credit_besitos(commit=False)` defer** — split-tx blast radius to atomicity golds + EventBus timing too high; document DEFER with rationale beats risky prod spike.

**Cluster (reaction ecosystem hardening):**
- Pool items **Week 1 + Week 2 (1+2/4) COMPLETE**. Week 1: unified markup + `process_channel_reaction` + validators + slim handler (prod refactor, 101+ tests). Week 2: parity goldens + message_id=0 + full_chain + CLAUDE + defer (tests+docs, 117 gold suite, 0 prod). Reaction ecosystem hardening cluster cerrado en scope Week 1–2.

**Handoff:** Item 2/4 closed. Reaction ecosystem Week 1+2 cluster complete. Ready for next pool item or pause.

**Pool phrase (verbatim):** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

**Fin del item documentado. Hoja de ruta lista.** 🎩