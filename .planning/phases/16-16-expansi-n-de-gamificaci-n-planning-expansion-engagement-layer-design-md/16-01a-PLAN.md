---
phase: 16
plan: 16-01a
wave: 1
depends_on: []
files_modified:
  - models/models.py
  - services/daily_gift_service.py
  - tests/unit/test_daily_gift_service.py
autonomous: true
type: auto
must_haves:
  - User can claim Ritmo Diario and receive streak-based bonus besitos
  - VIP users get higher base amounts, larger passive caps, and monthly streak recovery
  - All enum migrations apply cleanly before any code references new values
---

# Plan 16-01a: Ritmo Diario — Migrations, Models, and Service Core

**Objective:** Implement the database foundation and core service logic for Ritmo Diario (daily streaks + passive offline income + VIP differentiation).

**Requirements mapped:** ENG-01, ENG-06

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section I (Ritmo Diario)
- `.planning/phases/16-16-expansi-n-de-gamificaci-n-planning-expansion-engagement-layer-design-md/16-RESEARCH.md`
- `models/CLAUDE.md` (enum-first migration rules)
- `services/daily_gift_service.py` (existing DailyGiftService)

---

<task>
<name>Enum-first migrations for TransactionSource and MissionType</name>
<files>alembic/versions/20250415_add_story_path_and_whisper_to_transaction_source.py, alembic/versions/20250415_add_story_node_visit_whisper_claim_streak_recover_to_mission_type.py</files>
<action>
Create two Alembic migration files:

1. `alembic/versions/20250415_add_story_path_and_whisper_to_transaction_source.py`:
   - `revision = '20250415_story_whisper_enum'`
   - `down_revision = '20250407_add_game_and_anonymous_message_cost_to_transaction_source'` (use the exact revision ID of the current latest migration)
   - In `upgrade()`: execute the two ALTER TYPE statements with `IF NOT EXISTS`
   - In `downgrade()`: `pass` with a comment `# PostgreSQL does not support dropping enum values; downgrade is a no-op`

2. `alembic/versions/20250415_add_story_node_visit_whisper_claim_streak_recover_to_mission_type.py`:
   - `revision = '20250415_missiontype_engagement'`
   - `down_revision = '20250415_story_whisper_enum'`
   - In `upgrade()`: three `op.execute` calls adding `STORY_NODE_VISIT`, `WHISPER_CLAIM`, `STREAK_RECOVER` to `missiontype` with `IF NOT EXISTS`
   - In `downgrade()`: `pass` with comment about PostgreSQL limitation
</action>
<verify>
<command>alembic upgrade head && alembic downgrade -1</command>
<expected>0</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add DailyGiftStreak model, enums, and create table migration</name>
<files>models/models.py, alembic/versions/20250415_add_daily_gift_streaks_table.py</files>
<action>
In `models/models.py`:
1. Add `STORY_PATH = "story_path"` and `WHISPER = "whisper"` to `TransactionSource` enum.
2. Add `STORY_NODE_VISIT = "story_node_visit"`, `WHISPER_CLAIM = "whisper_claim"`, `STREAK_RECOVER = "streak_recover"` to `MissionType` enum.
3. Add `DailyGiftStreak` class immediately after `DailyGiftClaim` in the FASE 1 section with columns: id, user_id (BigInteger, unique), current_streak, last_claimed_at (DateTime tz-aware), recoveries_used_this_month, updated_at.

Create `alembic/versions/20250415_add_daily_gift_streaks_table.py`:
- `revision = '20250415_daily_gift_streaks'`
- `down_revision = '20250415_missiontype_engagement'`
- `upgrade()`: `op.create_table('daily_gift_streaks', ...)` with all columns from `DailyGiftStreak`
- `downgrade()`: `op.drop_table('daily_gift_streaks')`
</action>
<verify>
<command>python -c "from models.models import DailyGiftStreak, TransactionSource, MissionType; print(TransactionSource.STORY_PATH.value, MissionType.WHISPER_CLAIM.value, DailyGiftStreak.__tablename__)"</command>
<expected>story_path whisper_claim daily_gift_streaks</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Extend DailyGiftService with streak and passive logic</name>
<files>services/daily_gift_service.py</files>
<action>
Extend `services/daily_gift_service.py` with the following methods (max 50 lines each; split helper methods as needed):

1. `get_or_create_streak(self, user_id: int) -> DailyGiftStreak`:
   - Query `DailyGiftStreak` by `user_id`
   - If not found:
     - Create with `current_streak=0`, `recoveries_used_this_month=0`
     - **Migration logic for existing users**: If user has DailyGiftClaim history:
       1. Query all claims for user ordered by `claimed_at DESC`
       2. Start from most recent claim, count backwards checking each claim date
       3. Break chain if gap between consecutive claims > 24 hours
       4. Set `current_streak` to count and `last_claimed_at` to most recent claim date
   - Return streak

2. `calculate_passive_income(self, user_id: int, is_vip: bool) -> int`:
   - Get last claim from `DailyGiftClaim` ordered by `claimed_at` desc
   - If no last claim, return 0
   - `hours_offline = (datetime.now(timezone.utc) - last_claim.claimed_at).total_seconds() / 3600`
   - `cap = 24 if is_vip else 8`
   - `rate = 1`
   - Return `int(min(hours_offline, cap) * rate)`

3. `get_ritmo_status(self, user_id: int, is_vip: bool) -> dict`:
   - Call `can_claim(user_id)` to get eligibility
   - `base_amount = self.get_gift_amount() * (2 if is_vip else 1)`
   - `passive = self.calculate_passive_income(user_id, is_vip)`
   - `streak = self.get_or_create_streak(user_id)`
   - `multiplier = min(streak.current_streak * (20 if is_vip else 10), 100 if is_vip else 50)`
   - `total = int((base_amount + passive) * (1 + multiplier / 100))`
   - Return dict with all values

4. `claim_ritmo(self, user_id: int, is_vip: bool, bot=None) -> dict`:
   - Get `can_claim, _, msg = self.can_claim(user_id)`
   - If not `can_claim`, return `{"success": False, "message": msg}`
   - `status = self.get_ritmo_status(user_id, is_vip)`
   - `total_amount = status["total_amount"]`
   - `passive = status["passive_amount"]`
   - Credit besitos: `self._get_besito_service().credit_besitos(user_id, total_amount, TransactionSource.DAILY_GIFT, "Ritmo Diario reclamado")`
   - Update streak: get streak, check if `> 48h` since `last_claimed_at`. If break and `is_vip` and `recoveries_used_this_month < 1`, increment `recoveries_used_this_month` and keep streak. Otherwise reset to 0. If no break, increment streak by 1. Set `last_claimed_at = datetime.now(timezone.utc)`.
   - Also create a `DailyGiftClaim` record with `besitos_received=total_amount`
   - Advance mission: `mission_service = MissionService(self._get_db()); await mission_service.increment_progress_and_deliver(user_id, MissionType.DAILY_GIFT_TOTAL, amount=1, bot=bot)`
   - Commit and return success dict

Add imports: `from models.models import DailyGiftStreak, MissionType`, `from services.mission_service import MissionService`.
</action>
<verify>
<command>pytest -xvs tests/unit/test_daily_gift_service.py -k "TestDailyGiftStreak or TestDailyGiftPassive or TestDailyGiftRitmoClaim"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for streak and passive logic</name>
<files>tests/unit/test_daily_gift_service.py</files>
<action>
Append to `tests/unit/test_daily_gift_service.py`:

```python
@pytest.mark.unit
class TestDailyGiftStreak:
    def test_get_or_create_streak_new_user(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        streak = service.get_or_create_streak(sample_user.id)
        assert streak.user_id == sample_user.id
        assert streak.current_streak == 0

    def test_streak_increments_on_claim(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        import asyncio
        asyncio.run(service.claim_ritmo(sample_user.id, is_vip=False))
        streak = service.get_or_create_streak(sample_user.id)
        assert streak.current_streak == 1

    def test_streak_breaks_after_48h(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        from datetime import datetime, timedelta, timezone
        streak = service.get_or_create_streak(sample_user.id)
        streak.current_streak = 5
        streak.last_claimed_at = datetime.now(timezone.utc) - timedelta(hours=49)
        db_session.commit()
        import asyncio
        asyncio.run(service.claim_ritmo(sample_user.id, is_vip=False))
        db_session.refresh(streak)
        assert streak.current_streak == 0

    def test_vip_recover_streak_once_per_month(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        from datetime import datetime, timedelta, timezone
        streak = service.get_or_create_streak(sample_user.id)
        streak.current_streak = 5
        streak.last_claimed_at = datetime.now(timezone.utc) - timedelta(hours=49)
        db_session.commit()
        import asyncio
        asyncio.run(service.claim_ritmo(sample_user.id, is_vip=True))
        db_session.refresh(streak)
        assert streak.current_streak == 5
        assert streak.recoveries_used_this_month == 1


@pytest.mark.unit
class TestDailyGiftPassive:
    def test_passive_zero_when_no_claims(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        assert service.calculate_passive_income(sample_user.id, is_vip=False) == 0

    def test_passive_capped_for_free(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        from datetime import datetime, timedelta, timezone
        claim = DailyGiftClaim(
            user_id=sample_user.id,
            besitos_received=10,
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=12)
        )
        db_session.add(claim)
        db_session.commit()
        assert service.calculate_passive_income(sample_user.id, is_vip=False) == 8

    def test_passive_capped_for_vip(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        from datetime import datetime, timedelta, timezone
        claim = DailyGiftClaim(
            user_id=sample_user.id,
            besitos_received=10,
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=30)
        )
        db_session.add(claim)
        db_session.commit()
        assert service.calculate_passive_income(sample_user.id, is_vip=True) == 24


@pytest.mark.unit
class TestDailyGiftRitmoClaim:
    def test_get_ritmo_status_structure(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        status = service.get_ritmo_status(sample_user.id, is_vip=False)
        assert "can_claim" in status
        assert "base_amount" in status
        assert "passive_amount" in status
        assert "streak" in status
        assert "multiplier_percent" in status
        assert "total_amount" in status

    def test_claim_ritmo_credits_besitos(self, db_session, sample_user):
        service = DailyGiftService(db_session)
        import asyncio
        result = asyncio.run(service.claim_ritmo(sample_user.id, is_vip=False))
        assert result["success"] is True
        assert result["amount"] > 0
        balance = service.besito_service.get_balance(sample_user.id)
        assert balance == result["amount"]
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_daily_gift_service.py</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
