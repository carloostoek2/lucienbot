---
phase: 16
slug: 16-expansi-n-de-gamificaci-n-planning-expansion-engagement-layer-design-md
status: planned
plans_count: 10
waves_count: 5
---

# Phase 16: Expansión de gamificación (Engagement Layer)

**Goal:** Implement the "Engagement Layer" expansion of gamification: Ritmo Diario (daily streaks + passive offline income), Senderos Narrativos (curated story paths), Misiones Dinámicas (daily rotating missions), Susurros de Diana (daily random reward whisper system), and Estadísticas Anónimas (anonymous percentiles).

**Design reference:** `.planning/expansion_engagement_layer/DESIGN.md`

**Constraints (non-negotiable):**
- Single economy: besitos only
- Extend existing services only (DailyGiftService, StoryService, RewardService, MissionService, BesitoService)
- Absolute anonymity — no user-to-user exposure
- VIP vs Free as business driver
- Every action advances MissionService
- Every reward goes through RewardService.deliver_reward()
- Handlers must be pure (1 service call each)
- Max 50 lines per function
- Enum-first Alembic migrations

---

## Sub-Plans

| Plan | Wave | Name | Depends On | Status |
|------|------|------|------------|--------|
| 16-01a | 1 | Ritmo Diario — Migrations, Models, Service Core | — | Planned |
| 16-01b | 1 | Ritmo Diario — Handlers, Keyboards, Voice, Bot Wiring | 16-01a | Planned |
| 16-02a | 2 | Misiones Dinámicas — Model, Migration, CRUD | 16-01a | Planned |
| 16-02b | 2 | Misiones Dinámicas — Daily Generation, Scheduler, Admin Handlers | 16-02a | Planned |
| 16-03a | 3 | Senderos Narrativos — Models, Migrations, StoryService Methods | 16-01a, 16-02a | Planned |
| 16-03b | 3 | Senderos Narrativos — Handlers, Keyboards, Voice, Admin UI | 16-03a | Planned |
| 16-04a | 4 | Susurros de Diana — Models, Migrations, RewardService Methods | 16-01a, 16-02a, 16-03a | Planned |
| 16-04b | 4 | Susurros de Diana — Handlers, Keyboards, Voice, Admin UI | 16-04a | Planned |
| 16-05a | 5 | Percentiles Anónimos — Service Methods and Tests | 16-01a, 16-02a, 16-03a, 16-04a | Planned |
| 16-05b | 5 | Percentiles UI, VIP Streak Recovery Finalization, Full Suite | 16-05a | Planned |

---

## Requirements Mapping

| Requirement | Description | Covered In |
|-------------|-------------|------------|
| ENG-01 | Ritmo Diario: streak tracking, passive income, VIP differentiation | 16-01a, 16-01b |
| ENG-02 | Senderos Narrativos: curated paths, progress tracking, unlock conditions | 16-03a, 16-03b |
| ENG-03 | Misiones Dinámicas: daily rotating missions from templates | 16-02a, 16-02b |
| ENG-04 | Susurros de Diana: daily weighted random rewards from pools | 16-04a, 16-04b |
| ENG-05 | Estadísticas Anónimas: percentile queries without leaderboards | 16-05a, 16-05b |
| ENG-06 | Enum-first Alembic migrations for TransactionSource and MissionType | 16-01a, 16-02a, 16-03a, 16-04a |
| ENG-07 | Pure handlers: engagement_user_handlers.py and engagement_admin_handlers.py | 16-01b, 16-02b, 16-03b, 16-04b, 16-05b |

---

## Files to Create

- `handlers/engagement_user_handlers.py`
- `handlers/engagement_admin_handlers.py`
- Alembic migrations (enum-first, then tables)

## Files to Modify

- `models/models.py`
- `services/daily_gift_service.py`
- `services/mission_service.py`
- `services/story_service.py`
- `services/reward_service.py`
- `services/besito_service.py`
- `services/scheduler_service.py`
- `handlers/engagement_user_handlers.py`
- `handlers/engagement_admin_handlers.py`
- `keyboards/inline_keyboards.py`
- `utils/lucien_voice.py`
- `bot.py`
- `handlers/__init__.py`
- `tests/unit/test_daily_gift_service.py`
- `tests/unit/test_story_service.py`
- `tests/unit/test_mission_service.py`
- `tests/unit/test_reward_service.py`
- `tests/unit/test_besito_service.py`

---

## Execution Order

1. Run **16-01a** (Wave 1) — enums, DailyGiftStreak, Ritmo service logic, tests
2. Run **16-01b** (Wave 1) — Ritmo handlers, keyboards, voice, bot wiring
3. Run **16-02a** (Wave 2) — MissionTemplate model, migration, CRUD, tests
4. Run **16-02b** (Wave 2) — daily mission generation, scheduler job, admin handlers
5. Run **16-03a** (Wave 3) — StoryPath, node unlocks, StoryService methods, tests
6. Run **16-03b** (Wave 3) — Senderos handlers, keyboards, voice, admin UI
7. Run **16-04a** (Wave 4) — WhisperRewardPool, RewardService methods, tests
8. Run **16-04b** (Wave 4) — Susurros handlers, keyboards, voice, admin UI
9. Run **16-05a** (Wave 5) — percentile service methods and tests
10. Run **16-05b** (Wave 5) — percentile UI, VIP streak recovery finalization, full test suite

---

## Success Criteria

- [ ] All 10 sub-plans executed
- [ ] `pytest tests/ -x` passes
- [ ] `alembic upgrade head` applies cleanly
- [ ] Handlers contain zero business logic (verified by code review)
- [ ] No new services created
- [ ] All user-facing actions advance MissionService
- [ ] All rewards flow through RewardService.deliver_reward()
