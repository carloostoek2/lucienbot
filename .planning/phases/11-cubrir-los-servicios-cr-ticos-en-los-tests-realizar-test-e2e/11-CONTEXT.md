# Phase 11: Critical Services Test Coverage + E2E Tests — Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Source:** User-provided requirements via plan-phase prompt

<domain>
## Phase Boundary

Phase 11 expands test coverage from the 4 services currently covered (VIPService, ChannelService, BesitoService, MissionService) to:
1. All remaining business logic services
2. Cross-service integration flows (entry rituals, store transactions)
3. LucienVoice consistency validation
4. E2E tests covering complete user journeys

</domain>

<decisions>
## Implementation Decisions

### Test Coverage Strategy
- **Covered by existing tests:**
  - VIPService (unit tests)
  - ChannelService (unit tests)
  - BesitoService (unit tests)
  - MissionService (unit tests)
  - RateLimitMiddleware (unit tests)
  - Scheduler (unit tests)
  - VIP integration flow (integration tests)

- **New services needing test coverage:**
  - StoreService — transactions, balance deduction, stock management
  - PromotionService — code validation, discount application, usage limits
  - StoryService — node loading, archetype initialization, decision branching
  - AnalyticsService — metrics computation, CSV export
  - BackupService — backup/restore logic
  - UserService — profile management, role assignment
  - BroadcastService — message broadcast logic
  - DailyGiftService — gift mechanics
  - RewardService — reward delivery (used by MissionService)
  - PackageService — package management
  - BesitoService — COMPLETE coverage ( hugs, gifts, daily limits already tested but verify)
  - VIPService — COMPLETE coverage (verify)

### Entry Flow Tests (E2E Priority)
- Free channel entry: 30-second wait → auto-approval loop
- VIP channel entry: 3-phase ritual (confirm → align → deliver)
- Onboarding messages and menu system consistency
- Race conditions in concurrent entry requests
- Scheduler triggering for delayed approvals

### Race Condition Testing
- Store transactions: concurrent purchase of limited-stock packages
- Token redemption: concurrent redemption attempts with SELECT FOR UPDATE
- Besito transfers: simultaneous gift/spend operations
- Subscription creation: duplicate prevention

### LucienVoice Consistency
- All service message templates must follow Lucien's 3rd-person voice
- Test that error messages, confirmations, and greetings use consistent tone
- Verify no hardcoded strings outside message template classes

### Admin Wizard Testing
- Reward creation wizard: all steps (type → target → reward → confirmation)
- Level system management (create/edit/assign levels)
- Story administration: CRUD for story nodes, archetypes, and branches
- Promotion management: create/activate/deactivate codes

### Narrative System
- StoryService: node loading from DB, archetype initialization
- Decision branching: user choices lead to correct next nodes
- Archetypes: traits loaded correctly per archetype type
- Story administration: admin can create stories with nodes and choices

### Content Packages
- PackageService: create/activate/deactivate packages
- StoreService: purchase flow with promotion codes
- Stock management: -1 (unlimited), -2 (unavailable), finite numbers

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `CLAUDE.md` — Project guidelines, GSD workflow enforcement, security rules
- `@architecture.md` — Handler/service/model layer separation rules
- `@rules.md` — 50-line limit, naming conventions, logging rules

### Services (read to understand what to test)
- `services/store_service.py` — StoreService with purchase flow
- `services/promotion_service.py` — PromotionService with code validation
- `services/story_service.py` — StoryService with node/archetype management
- `services/vip_service.py` — VIPService (existing tests reference this)
- `services/channel_service.py` — ChannelService (existing tests reference this)
- `services/besito_service.py` — BesitoService (existing tests reference this)
- `services/mission_service.py` — MissionService (existing tests reference this)
- `services/user_service.py` — UserService
- `services/analytics_service.py` — AnalyticsService
- `services/backup_service.py` — BackupService
- `services/scheduler_service.py` — SchedulerService

### Existing Tests (read to understand patterns to follow)
- `tests/conftest.py` — Fixtures: db_session, sample_user, sample_vip_channel, sample_tariff, sample_token, sample_subscription, sample_pending_request, mock_bot
- `tests/unit/test_vip_service.py` — VIPService test patterns
- `tests/unit/test_channel_service.py` — ChannelService test patterns
- `tests/unit/test_besito_service.py` — BesitoService test patterns
- `tests/unit/test_mission_service.py` — MissionService test patterns
- `tests/integration/test_vip_flow.py` — Integration test patterns

### Key Models
- `models/models.py` — All SQLAlchemy models (User, Token, Subscription, Channel, etc.)

</canonical_refs>

<specifics>
## Specific Test Scenarios from User Requirements

1. **Free channel 30s delay:** Verify scheduler job processes pending request after wait_time_minutes, sends welcome + invite link
2. **VIP 3-phase ritual:** confirm → align → deliver; verify state transitions (vip_entry_stage 1→2→3), verify expired subscription blocks flow
3. **Store transaction race condition:** Two concurrent purchases of a package with stock=1; only one should succeed
4. **Token redemption race condition:** Concurrent redemption of same token; only one should succeed
5. **LucienVoice check:** grep for hardcoded Spanish strings in services (outside message template classes)
6. **Reward wizard:** Admin creates reward via all steps, verifies mission → reward linkage
7. **Story branching:** Create story with 2 choices at node A pointing to nodes B and C; verify correct node loads based on choice
8. **Promotion code:** Create code PROM001 with 3 uses; third redemption should fail

</specifics>

<deferred>
## Deferred Ideas

- UI/frontend tests (Phase 12 or later)
- Performance/load testing
- Database migration tests
- Redis-dependent tests (FSM storage)
- Multi-user concurrent stress tests

</deferred>

---

*Phase: 11-critical-services-tests*
*Context gathered: 2026-04-02 via plan-phase user input*
