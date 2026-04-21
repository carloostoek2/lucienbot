---
phase: 16
plan: 16-02b
wave: 3
depends_on: ["16-02a"]
files_modified:
  - services/mission_service.py
  - services/scheduler_service.py
  - handlers/engagement_admin_handlers.py
  - tests/unit/test_mission_service.py
autonomous: true
type: auto
must_haves:
  - Every day at 00:01, the bot generates 3+ daily missions from templates automatically
  - Admin can view the list of mission templates through a pure handler
  - Previous auto-generated daily missions are deactivated before new ones are created
---

# Plan 16-02b: Misiones Dinámicas — Daily Generation, Scheduler, and Admin Handlers

**Objective:** Implement daily mission generation from templates, register the scheduler job, and add admin handlers.

**Requirements mapped:** ENG-03, ENG-07

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section III (Misiones Dinámicas)
- `services/mission_service.py`
- `services/scheduler_service.py`

---

<task>
<name>Implement generate_daily_missions_from_templates in MissionService</name>
<files>services/mission_service.py</files>
<action>
Add to `services/mission_service.py`:

```python
import random
from datetime import datetime, timedelta, timezone

def generate_daily_missions_from_templates(self) -> List[Mission]:
    db = self._get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1) - timedelta(seconds=1)

    # Deactivate previous auto-generated daily missions
    old_dailies = db.query(Mission).filter(
        Mission.name.like("[Daily] %"),
        Mission.frequency == MissionFrequency.RECURRING,
        Mission.is_active == True
    ).all()
    for old in old_dailies:
        old.is_active = False
    db.commit()

    created = []

    # Connection mission: claim Ritmo
    connection_reward = db.query(Reward).filter(
        Reward.is_active == True,
        Reward.reward_type == RewardType.BESITOS
    ).first()
    connection = Mission(
        name="[Daily] Ritmo Diario",
        description="Reclama tu Ritmo Diario",
        mission_type=MissionType.DAILY_GIFT_TOTAL,
        target_value=1,
        reward_id=connection_reward.id if connection_reward else None,
        frequency=MissionFrequency.RECURRING,
        cooldown_hours=24,
        start_date=today_start,
        end_date=today_end,
        is_active=True
    )
    db.add(connection)
    created.append(connection)

    templates = self.get_all_mission_templates(active_only=True)
    vip_templates = [t for t in templates if t.is_vip_exclusive]
    free_templates = [t for t in templates if not t.is_vip_exclusive]

    selected = []
    if free_templates:
        selected.extend(random.choices(
            free_templates,
            weights=[t.weight for t in free_templates],
            k=min(2, len(free_templates))
        ))
    if vip_templates:
        selected.extend(random.choices(
            vip_templates,
            weights=[t.weight for t in vip_templates],
            k=1
        ))

    for template in selected:
        reward = db.query(Reward).filter(
            Reward.id == template.reward_id,
            Reward.is_active == True
        ).first()
        if not reward:
            logger.warning(f"Daily mission skipped: reward {template.reward_id} inactive")
            continue
        mission = Mission(
            name=f"[Daily] {template.name}",
            description=template.name,
            mission_type=template.mission_type,
            target_value=template.target_value,
            reward_id=template.reward_id,
            frequency=MissionFrequency.RECURRING,
            cooldown_hours=24,
            start_date=today_start,
            end_date=today_end,
            is_active=True
        )
        db.add(mission)
        created.append(mission)

    db.commit()
    logger.info(f"Daily missions generated: {len(created)}")
    return created
```

Add imports at top: `import random`, `from datetime import datetime, timedelta, timezone`, `from models.models import Reward, RewardType`.
</action>
<verify>
<command>pytest -xvs tests/unit/test_mission_service.py -k "TestDailyMissionGeneration"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add scheduler job for daily mission generation</name>
<files>services/scheduler_service.py</files>
<action>
In `services/scheduler_service.py`:

1. Add import: `from services.mission_service import MissionService`

2. Add module-level job function before `SchedulerService` class:

```python
async def _generate_daily_missions_job():
    """Genera misiones diarias desde templates (llamado por APScheduler)."""
    db = SessionLocal()
    try:
        mission_service = MissionService(db)
        mission_service.generate_daily_missions_from_templates()
        db.commit()
        logger.info("Daily missions generated from templates")
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating daily missions: {e}")
    finally:
        db.close()
```

3. In `SchedulerService.start()`, add after the backup job:

```python
        self._scheduler.add_job(
            _generate_daily_missions_job,
            trigger="cron",
            hour=0, minute=1,
            id="generate_daily_missions",
            name="Generate daily missions from templates",
            replace_existing=True,
        )
```
</action>
<verify>
<command>grep -c "generate_daily_missions" services/scheduler_service.py</command>
<expected>3</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add admin handlers for MissionTemplate CRUD</name>
<files>handlers/engagement_admin_handlers.py</files>
<action>
Append to `handlers/engagement_admin_handlers.py`:

```python
from services.mission_service import MissionService
from models.models import MissionType


@router.callback_query(F.data == "admin_mission_templates")
async def admin_mission_templates_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(LucienVoice.not_admin_error(), show_alert=True)
        return

    service = MissionService()
    try:
        templates = service.get_all_mission_templates()
    finally:
        service.close()

    text = "🎩 <b>Lucien:</b>\n\n<i>Plantillas de misiones dinámicas...</i>\n\n"
    if not templates:
        text += "No hay plantillas configuradas."
    else:
        for t in templates:
            vip_badge = "💎" if t.is_vip_exclusive else ""
            text += f"{vip_badge} <b>{t.name}</b> | Peso: {t.weight}\n"

    await callback.message.edit_text(text, reply_markup=back_keyboard("admin_gamification"), parse_mode="HTML")
    await callback.answer()
```
</action>
<verify>
<command>grep -c "admin_mission_templates" handlers/engagement_admin_handlers.py</command>
<expected>1</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for daily mission generation</name>
<files>tests/unit/test_mission_service.py</files>
<action>
Append to `tests/unit/test_mission_service.py`:

```python
@pytest.mark.unit
class TestDailyMissionGeneration:
    def test_generates_connection_mission(self, db_session, sample_reward):
        service = MissionService(db_session)
        missions = service.generate_daily_missions_from_templates()
        assert any(m.mission_type == MissionType.DAILY_GIFT_TOTAL for m in missions)

    def test_deactivates_previous_dailies(self, db_session, sample_reward):
        service = MissionService(db_session)
        old = service.create_mission(
            name="[Daily] Old", mission_type=MissionType.REACTION_COUNT,
            target_value=1, reward_id=sample_reward.id,
            frequency=MissionFrequency.RECURRING
        )
        service.generate_daily_missions_from_templates()
        db_session.refresh(old)
        assert old.is_active is False

    def test_daily_missions_have_today_dates(self, db_session, sample_reward):
        service = MissionService(db_session)
        service.create_mission_template("T", MissionType.REACTION_COUNT, 1, sample_reward.id)
        missions = service.generate_daily_missions_from_templates()
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        for m in missions:
            assert m.start_date.date() == today
            assert m.end_date.date() == today
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_mission_service.py -k "TestDailyMissionGeneration"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
