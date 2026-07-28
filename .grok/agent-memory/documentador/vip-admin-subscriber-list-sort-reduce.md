# Tirón / Pool Documentation Report (documentador) — VIP Admin List Sort + Reduce Time

**Pool context:** Hardener-agile **1-item** standalone quick (`vip-admin-subscriber-list-sort-reduce`). **Product feature** (not `--hardening` mode) on channels-VIP admin surface: newest-first subscriber list + reduce remaining VIP time without kick/ban/deactivate. Source of truth: SUMMARY + PLAN + gsd + impact/arch/test-guardian/review. Documentador: **0 code changes**.

**Date:** 2026-07-28  
**Agent:** documentador (post-pool close)  
**Mode:** product feature quick — **do not** use hardening pool-close phrase verbatim; **do not** bloat HARDENING_ROADMAP.

**Sources (truth, no invention):**
- `.planning/quick/20260728-vip-admin-subscriber-list-sort-reduce/{PLAN.md, SUMMARY.md}`
- `.planning/quick/gsd-vip-admin-subscriber-list-sort-reduce.log`
- `.grok/agent-memory/impact-analyzer/vip-admin-subscriber-list-sort-reduce.md`
- `.grok/agent-memory/arch-enforcer/vip-admin-subscriber-list-sort-reduce.md`
- `.grok/agent-memory/test-guardian/vip-admin-subscriber-list-sort-reduce.md`
- `.grok/agent-memory/review/vip-admin-subscriber-list-sort-reduce.md`

---

## Pool / Item (1/1 COMPLETE)

| Field | Value |
|-------|--------|
| Item | vip-admin-subscriber-list-sort-reduce |
| Type | Feature (admin VIP list + reduce time) |
| Effort (review) | 3 |
| Sequence | impact → planner → executor (TDD 3 tasks) → arch → test-guardian → review 2 rounds → documentador |

**What shipped (from SUMMARY):**
1. **List order:** `get_subscriber_list_page` → `created_at.desc(), id.desc()` (newest subscribe first; id tiebreak).
2. **Reduce service:** `VIPService.admin_reduce_subscription_time` mutates **only** `end_date` earlier; rejects `would_expire` / `not_earlier` / `invalid_args` / `not_found` / `inactive` with zero mutation where applicable; never ban / `is_active=False` / EventBus.
3. **Admin FSM:** reduce → mode (days\|date) → free text → confirm; confirm = exactly 1 `get_service(VIPService)`.
4. **UI:** profile «⏱ Reducir tiempo», mode keyboard, Lucien voice strings.
5. **Pure helpers:** `parse_reduce_days_input`, `parse_reduce_end_date_input` (DD/MM/YYYY end-of-day UTC).

**Deviation:** Split `_is_valid_reduce_args` + `_compute_reduced_end_candidate` + `_log_reduce_result` so `admin_reduce_subscription_time` ≤50 LOC (auto-fix LOC).

---

## Outcomes + Verifs

| Gate | Result |
|------|--------|
| Executor self-check | **PASSED** (3/3 tasks + Fix Round 1) |
| Targeted | **94 → 99 passed** post Fix Round 1 (sqlite DATABASE_URL) |
| VIP golds | **306 passed**, 8 xfailed |
| Atomicity/reaction/daily/invariants | **94 passed**, 1 fail non-attributable (broadcast MissingGreenlet) |
| Arch-enforcer | **PASS WITH NOTES**, **0 critical** |
| Test-guardian | **"suite protege adecuadamente"** |
| Review | effort **3**, rounds **2**, **4** test suggestions fixed, final **0 open** |

### Commits

| SHA | Message |
|-----|---------|
| `a1d4be3` | feat(vip): newest-first list + admin reduce time service |
| `c463b4d` | feat(vip): reduce-time UI surface and parse helpers |
| `ab630e7` | feat(vip): admin FSM to reduce subscription time without kick |
| `7a65964` | test(vip): cover reduce not_found/inactive and sort id tiebreak |

### Review Fix Round 1 (tests only)

1. Real-DB `not_found` + `inactive` reduce codes  
2. Sort `id.desc` tiebreak when same `created_at`  
3. Handler confirm date-mode kwargs + no revoke  
4. `not_earlier` when `new_end == current`  

---

## Residuals (classified)

| title | clase | por_qué |
|-------|-------|---------|
| `search_active_subscribers` still `end_date.asc` | **out-of-scope** | Explicit PLAN non-goal; only list page reordered |
| MissingGreenlet broadcast `test_real_with_get_service_usage_in_test` | **out-of-scope** | Env/asyncpg flake; not VIP reduce/sort surface |

---

## 3 critical systems + contracts

| System | Impact |
|--------|--------|
| Gamificación | **None** — no BesitoService / credit / debit / reaction / daily on reduce path |
| Narrativa | **None** |
| Canales-VIP | **Controlled** — sort + earlier `end_date` only while active and `end_date > now`; scheduler remains sole kick path for true expiry |

**Contracts:** reduce MUST NOT ban/revoke/EventBus; confirm 1× `get_service(VIPService)`; pure parse helpers; `is_admin` on all reduce entrypoints; logging standard.

---

## Learnings / Patterns (reusable)

- **Reduce-without-kick pattern:** Inverse of extend via end_date-only mutate (copy `grant_internal_vip_access_for_subscription` load+aware+commit shape) **but omit** EventBus / tariff swap / ban. Explicit anti-pattern: never reuse `admin_revoke_subscription` for shorten-time.
- **would_expire gate:** Candidate `end_date` must stay `> now`; reject before commit so scheduler never kicks as side-effect of successful reduce.
- **Result codes stable for handlers:** `ok` \| `not_found` \| `inactive` \| `invalid_args` \| `would_expire` \| `not_earlier` — map in pure helper + unit real-DB for every code.
- **FSM mirror debit:** mode step extra; confirm 1 service; pure parsers with `"Función pura..."` docstring; LOC split helpers under service.
- **Sort key = first subscribe:** `created_at` (not updated on extend) + `id.desc` tiebreak; leave search order alone unless product asks.

---

## Docs updates (this invocation)

| Artifact | Action |
|----------|--------|
| SUMMARY | Completed: commits table, gates, review stats, residuals classified, pool_closed |
| This report | Created |
| `.grok/agent-memory/documentador/MEMORY.md` | Pointer added |
| `decisions.md` | Short durable entry: reduce-without-kick pattern |
| HARDENING_ROADMAP | **Not rewritten** (product feature quick, not hardening pool) |

GSD pre-log: `.planning/quick/gsd-documentador-vip-admin-subscriber-list-sort-reduce.log` (gitignored `*.log`).

---

## Handoff

Pool `vip-admin-subscriber-list-sort-reduce` cerrado — 1 ítem completado, tests passing, review 0 issues, commits hechos, documentación actualizada según scope.

Ready for user acceptance on admin list sort + reduce-time UX; optional follow-up only if product wants `search_active_subscribers` order aligned (currently out of scope).

---

*documentador (Lucien Bot) — 2026-07-28*  
*Refs: SUMMARY + PLAN + impact/arch/test-guardian/review + gsd log + commits a1d4be3..7a65964*
