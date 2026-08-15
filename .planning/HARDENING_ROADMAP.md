# Hardening Roadmap

Living hoja de ruta for telegram-bot-hardener work. Protects 3 critical systems (gamification, narrative, channels-VIP) plus atomicity / EventBus / `get_service` contracts.

**Last refresh:** 2026-07-06 · **Detail archive:** [HARDENING_ROADMAP_HISTORY.md](./HARDENING_ROADMAP_HISTORY.md) · **Decisions:** [decisions.md](../decisions.md)

---

## Quick path

| Field | Value |
|-------|--------|
| **Current focus** | Reaction ecosystem (broadcast reactions) — pool items 1–3 done; 3B optional deferred |
| **Latest closed** | `reaction-ecosystem-week3-tight` (3A tests only: `tracking_failed` admin path) |
| **Status** | Ready for next item or pause |
| **3 crit** | Protected on all recent pools (0 attributable gold regressions) |

### Do next (max 4)

| # | Candidate | Why | Risk |
|---|-----------|-----|------|
| 1 | Reaction 3B: extract-only slim `check_and_register_reaction` (≤50 LOC, no tx change) | Maint. debt left from week3 option A | Low |
| 2 | EventBus / structured logging remaining high-value (promo, backpack if surfaced) | Builds pool 35 Item 3 | Low |
| 3 | Test gaps: FSM real Redis sim, more gamif caps/property, VIP edges | Post pool 35 open gaps | Low |
| 4 | Health / rate smarter extensions | Observability debt residual | Low–med |

**Out of current pool (do not mix with 0-behavior hardening):**

- `credit_besitos(commit=False)` REACTION atomicity — **DEFER** (`decisions.md`; high blast radius)
- Prod fix `tracking_failed` retry/repair — feature behavior, evaluate separately

### Pool close phrase (verbatim)

> Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

### Checklist before starting next item

- [ ] Impact map names 3 crit + contracts
- [ ] PLAN is 0 behavior / 0 atomicity unless feature is explicit
- [ ] 6-agent sequence planned (impact → plan → execute → arch → test-guardian → tests)
- [ ] Golds list copied from last SUMMARY of related domain

---

## 1. Initial Analysis (status)

Original scan (2026-06-08). Full prose: history archive §1.

| Finding | Status | Closed by |
|---------|--------|-----------|
| Middleware incomplete (rate + idemp not global) | **Closed** | gsd-mw-hardening + pool 35 Redis optional |
| Session / `get_service` leaks | **Closed** | Session unification tirón |
| Cross-domain Besito held in services | **Mostly closed** | Items 5–6, 10; story kept on purpose |
| Atomicity / race gaps (gamif + VIP edges) | **Mostly closed** | Golds + pool 33–35 edges |
| Callback answer / error paths | **Closed** | Error + Idempotency middleware |
| Long admin wizards >50 LOC / multi-service | **Mostly closed** | Items 7–9, 34 reward, 35 promo; residual only if resurfaced |
| Test reality (mocks hide bugs) | **Mostly closed** | Pools 33–34 |
| Logging + health | **Mostly closed** | Item 11 + pool 34 Item 4 |
| In-mem rate/idemp multi-instance | **Closed** | Pool 35 Item 1 (optional Redis + fallback) |
| Docs drift | **Ongoing** | claude-md-sync + documentador |

**Always in mind:** channel-VIP · gamification · narrative.

---

## 2. Decisions (core only)

Full item entries live in `decisions.md`. Strategy locked:

| Decision | Rule |
|----------|------|
| Pipeline | impact → gsd-planner → gsd-executor → arch-enforcer → test-guardian → tests |
| Batch size | Max **4** items per pool; documentador at close |
| Scope default | **0/0/0** — no behavior, no atomicity, no scope creep unless feature pool |
| EventBus | Notifications only — listeners **MUST NOT** credit/debit |
| Besito cross-domain | Locals `BesitoService(db=…)` at credit/debit sites; not held in `__init__` |
| Handlers | Exactly **1** service via `with get_service(X)`; pure helpers for ≤50 LOC |
| Golds | Copy al pie (`cross_service_atomicity`, reaction chains, daily atomic, …) |
| Pool phrase | Verbatim string in Quick path |

---

## 3. How we proceed

```
impact-analyzer → gsd-planner → gsd-executor → arch-enforcer → test-guardian → pytest golds
                                                                    ↓
                                                         documentador (pool close)
```

| Gate | Pass signal |
|------|-------------|
| Executor | Self-check **PASSED** + GSD pre-log |
| Arch | **PASS** or **PASS WITH NOTES**, **0 critical** |
| Tests | Golds green; **0 attributable** regressions |
| Test-guardian | **"suite protege adecuadamente"** |
| Documentador | ROADMAP Quick path + Done index + Gaps refreshed |

**pytest flags (default):**  
`-q --tb=line -p no:cov --override-ini="addopts="` + PLAN `-k` filters + gold re-runs.

---

## 4. What Has Been Done (index)

Detail for each pool: [HISTORY](./HARDENING_ROADMAP_HISTORY.md) §4 + per-item `SUMMARY.md` / agent-memory reports.  
**documentador rule:** append **one compact row** (or short block ≤15 lines) here; put narrative in SUMMARY + history only if needed.

### Index (newest first)

| When | Pool / phase | Items | Outcome (one line) | Artifacts |
|------|--------------|-------|--------------------|-----------|
| 2026-07-06 | reaction-ecosystem-week3-tight | 3A | Admin `tracking_failed` tests (handler + pure publish); 0 prod | `quick/20260706-reaction-ecosystem-week3-tight/` |
| 2026-07-06 | reaction-ecosystem-week2 | 2/4 | Parity goldens, `message_id=0`, full_chain migrate, CLAUDE rewrite, credit defer; **0 prod** | `quick/20260706-reaction-ecosystem-week2/` + documentador week2 |
| 2026-07-05 | reaction-ecosystem-week1 | 1/4 | Unified markup, `process_channel_reaction`, validators, slim handler | `quick/20260705-reaction-ecosystem-week1/` + documentador week1 |
| 2026-07-02 | vip-subscriber-admin-profiles | 1/1 feature | Paginated VIP admin profiles + extend/grant/debit/kick; review 0 open | `36-*-SUMMARY` + documentador |
| 2026-06-28 | store catalog tier nav | 1/36 | Shop nav → catalog tiers (not package categories) | `34-store-catalog-tier-nav` |
| 2026-06-26 | Pool 35 | 4/4 | Redis rate/idemp · promo wizard 1svc · EventBus streak · deeper edges tests | `35-full-pool-close.md` |
| 2026-06-26 | Pool 34 | 4/4 | User-flow reality · reward_admin puros · test gaps · obs/docs hygiene | `34-*-SUMMARY` |
| 2026-06-26 | Pool 33 | 4/4 | Store purchase integration reality + promo me-interesa | `33-test-reality-pool-close.md` |
| 2026-06-23 | Broadcast link buttons | 2 | Button catalog + max-1 optional wizard URL | `20260623-broadcast-link-buttons-*` |
| 2026-06-15 | Phase 30 channel admin | feature | Custodio guards, real TG grant, messages, individual pending | `30-channel-admin-*` |
| 2026-06-11 | claude-md-sync meta | docs | Hardener 6-agent + documentador codified as standard | documentador claude-md-sync |
| ~2026-06 | Items 7–11 / pools | multi | 1svc+puros wizards · store Besito locals · HealthService | phases 25–29 SUMMARYs |
| Foundational | MW · session · EventBus · Besito 5–6 | multi | Rate/idemp global · get_service · listeners · locals | HISTORY §4 head |

### Patterns established (reuse)

| Pattern | Use when |
|---------|----------|
| `with get_service(X)` + thin service delegates | Multi-service wizard / handler |
| Pure helpers (`Función pura…`, verb+context+result) | Admin long funcs → ≤50 LOC |
| Local `BesitoService(db=self.db)` at credit/debit only | Cross-domain monetary ops |
| EventBus listener + MUST NOT + DESIRED + domain log | Observability after award |
| Integration: real service + class patch + UI 1:1 | Test reality (store/story/promo) |
| Optional Redis ctor + in-mem fallback | Middleware multi-instance |

### Latest pool block (documentador fills this)

**Pool: reaction-ecosystem (weeks 1–3 partial)**

| Item | Result | Arch | Test-guardian | Scope |
|------|--------|------|---------------|-------|
| Week 1 | Markup + `process_channel_reaction` + validators + slim handler | PWN 0 crit | suite protege | 0 UX change |
| Week 2 | Tests+docs+debt; credit_besitos defer | PASS 0 crit | suite protege | **0 prod** |
| Week 3 tight (3A) | `tracking_failed` admin/handler tests | (tests-only) | gate green | **0 prod** |

- **3 crit:** gamification reactions protected by golds; narr/channel 0 direct  
- **Phrase:** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.  
- **Handoff:** Week 1–2 cluster closed; 3A closed; optional 3B still open; 3D/3E out of hardening path  

---

## 5. What Is Missing / Roadmap

### Open gaps

| Gap | Priority | Notes |
|-----|----------|-------|
| Reaction 3B extract-only (`check_and_register_reaction` ≤50) | Med | Optional week3; no tx change |
| Residual admin long-funcs if resurfaced | Low | Most wizards closed (7–9, 34, 35) |
| FSM restart with **real Redis** (beyond Memory sim) | Med | Pool 35 used Memory fallback |
| Broader EventBus / logging (promo, backpack, …) | Med | Streak done in 35.3 |
| Health / rate smarter (per-action) | Low | Core /health exists |
| `credit_besitos(commit=False)` REACTION unify | **Deferred** | High blast; not in 0/0 pool |
| Prod `tracking_failed` repair | Separate feature | Not pure hardening |

### Proposed Next

See **Quick path → Do next**. Prefer items that:

1. Touch a critical system or a gold-protected contract  
2. Stay tight and verifiable  
3. Reuse an established pattern  

### Metrics of Success

| Metric | Target | Recent status |
|--------|--------|----------------|
| Arch critical violations | 0 | Achieved (PASS / PWN) |
| Attributable gold regressions | 0 | Achieved |
| Scope creep | 0/0/0 default | Achieved on hardening items |
| 3 crit + contracts | Explicitly protected | Achieved |
| Traceability | SUMMARY + gsd + agent reports + this index | Achieved |
| Documentador at pool close | Yes | Achieved |

### Next steps (operator)

1. Pick one row from **Do next** (or pause).  
2. Run 6-agent sequence; re-run domain golds.  
3. On pool close: documentador updates **Quick path**, **Done index**, **Latest pool block**, **Gaps**.  
4. Put long narrative in `SUMMARY.md` / agent-memory — **not** multi-page paste into this file.

---

## How documentador updates this file

Keep cognitive load low:

1. **Refresh Quick path** (current focus, latest closed, Do next table).  
2. **Add one index row** in §4 (newest first).  
3. **Replace Latest pool block** with compact table for the closed pool.  
4. **Refresh §5 Gaps + Proposed Next** (open items only).  
5. **One line** Metrics if numbers changed.  
6. Pool phrase **once** in the latest block (not repeated 10×).  
7. Full narrative → `SUMMARY.md` + optional append to `HARDENING_ROADMAP_HISTORY.md`.

---

**Sources:** SUMMARYs / PLANs / gsd logs / arch + test-guardian reports / documentador MEMORY. History of pre-redesign wall-of-text: `HARDENING_ROADMAP_HISTORY.md` (frozen snapshot 2026-07-06).
