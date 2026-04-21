---
phase: 16
plan: 16-03a
wave: 3
depends_on: ["16-01a", "16-02a"]
files_modified:
  - models/models.py
  - services/story_service.py
  - tests/unit/test_story_service.py
autonomous: true
type: auto
must_haves:
  - User can browse available curated story paths filtered by VIP status and attempt limits
  - Story nodes can require minimum streak days or total earned besitos to unlock
  - StoryPath CRUD and availability logic are covered by unit tests
---

# Plan 16-03a: Senderos Narrativos — Models, Migrations, and StoryService Methods

**Objective:** Implement the database schema and core service logic for curated story paths (Senderos Narrativos).

**Requirements mapped:** ENG-02, ENG-06

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section II (Senderos Narrativos)
- `services/story_service.py`
- `models/models.py`

---

<task>
<name>Extend StoryNode and add StoryPath models</name>
<files>models/models.py</files>
<action>
In `models/models.py`:
1. Inside the `StoryNode` class, add after `cost_besitos`:
```python
    unlock_required_streak = Column(Integer, nullable=True)
    unlock_required_besitos_total = Column(Integer, nullable=True)
```

2. Add `StoryPath` and `UserStoryPathProgress` classes immediately after the `StoryChoice` class in the FASE 6 section.

`StoryPath`:
- `__tablename__ = 'story_paths'`
- `id = Column(Integer, primary_key=True, index=True)`
- `name = Column(String(200), nullable=False)`
- `description = Column(Text, nullable=True)`
- `node_sequence = Column(Text, nullable=False, default='[]')`
- `reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=True)`
- `is_vip_exclusive = Column(Boolean, default=False)`
- `max_attempts = Column(Integer, default=1)`
- `valid_from = Column(DateTime(timezone=True), nullable=True)`
- `valid_until = Column(DateTime(timezone=True), nullable=True)`
- `is_active = Column(Boolean, default=True)`
- `created_by = Column(BigInteger, nullable=True)`
- `created_at = Column(DateTime(timezone=True), server_default=func.now())`
- `reward = relationship('Reward')`

`UserStoryPathProgress`:
- `__tablename__ = 'user_story_path_progress'`
- `id = Column(Integer, primary_key=True, index=True)`
- `user_id = Column(BigInteger, nullable=False, index=True)`
- `path_id = Column(Integer, ForeignKey('story_paths.id'), nullable=False)`
- `current_node_index = Column(Integer, default=0, nullable=False)`
- `attempts_used = Column(Integer, default=0, nullable=False)`
- `is_completed = Column(Boolean, default=False)`
- `started_at = Column(DateTime(timezone=True), server_default=func.now())`
- `completed_at = Column(DateTime(timezone=True), nullable=True)`
- `__table_args__ = (UniqueConstraint('user_id', 'path_id', name='uq_user_path_progress'),)`
</action>
<verify>
<command>python -c "from models.models import StoryNode, StoryPath, UserStoryPathProgress; print(hasattr(StoryNode, 'unlock_required_streak'), StoryPath.__tablename__, UserStoryPathProgress.__tablename__)"</command>
<expected>True story_paths user_story_path_progress</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Create Alembic migrations for StoryPath tables and StoryNode columns</name>
<files>alembic/versions/20250415_add_story_node_unlock_columns.py, alembic/versions/20250415_add_story_paths_table.py, alembic/versions/20250415_add_user_story_path_progress_table.py</files>
<action>
Create three migration files:

1. `alembic/versions/20250415_add_story_node_unlock_columns.py`:
   - `revision = '20250415_story_node_unlock'`
   - `down_revision = '20250415_mission_templates'`
   - `upgrade()`: `op.add_column('story_nodes', sa.Column('unlock_required_streak', sa.Integer(), nullable=True))` and `op.add_column('story_nodes', sa.Column('unlock_required_besitos_total', sa.Integer(), nullable=True))`
   - `downgrade()`: `op.drop_column('story_nodes', 'unlock_required_besitos_total')` then `op.drop_column('story_nodes', 'unlock_required_streak')`

2. `alembic/versions/20250415_add_story_paths_table.py`:
   - `revision = '20250415_story_paths'`
   - `down_revision = '20250415_story_node_unlock'`
   - `upgrade()`: `op.create_table('story_paths', ...)`
   - `downgrade()`: `op.drop_table('story_paths')`

3. `alembic/versions/20250415_add_user_story_path_progress_table.py`:
   - `revision = '20250415_user_story_path_progress'`
   - `down_revision = '20250415_story_paths'`
   - `upgrade()`: `op.create_table('user_story_path_progress', ..., sa.UniqueConstraint('user_id', 'path_id', name='uq_user_path_progress'))`
   - `downgrade()`: `op.drop_table('user_story_path_progress')`
</action>
<verify>
<command>alembic upgrade head && alembic downgrade -1</command>
<expected>0</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Extend StoryService with path CRUD, availability, and advancement</name>
<files>services/story_service.py</files>
<action>
In `services/story_service.py`:

1. Add to imports: `from models.models import StoryPath, UserStoryPathProgress`, `import json`, `from datetime import datetime, timezone`

2. Add methods after the existing `delete_choice` method:

```python
    def create_story_path(self, name: str, description: str,
                          node_sequence: list, reward_id: int = None,
                          is_vip_exclusive: bool = False,
                          max_attempts: int = 1,
                          valid_from: datetime = None,
                          valid_until: datetime = None,
                          created_by: int = None) -> StoryPath:
        path = StoryPath(
            name=name, description=description,
            node_sequence=json.dumps(node_sequence),
            reward_id=reward_id, is_vip_exclusive=is_vip_exclusive,
            max_attempts=max_attempts, valid_from=valid_from,
            valid_until=valid_until, created_by=created_by,
            is_active=True
        )
        self.db.add(path)
        self.db.commit()
        self.db.refresh(path)
        logger.info(f"StoryPath creado: {name} (ID: {path.id})")
        return path

    def get_story_path(self, path_id: int) -> Optional[StoryPath]:
        return self.db.query(StoryPath).filter(StoryPath.id == path_id).first()

    def list_active_story_paths(self) -> List[StoryPath]:
        now = datetime.now(timezone.utc)
        return self.db.query(StoryPath).filter(
            StoryPath.is_active == True,
            (StoryPath.valid_from == None) | (StoryPath.valid_from <= now),
            (StoryPath.valid_until == None) | (StoryPath.valid_until >= now)
        ).all()

    def list_available_paths(self, user_id: int, is_vip: bool) -> List[StoryPath]:
        paths = self.list_active_story_paths()
        if not is_vip:
            paths = [p for p in paths if not p.is_vip_exclusive]
        available = []
        for path in paths:
            progress = self.db.query(UserStoryPathProgress).filter(
                UserStoryPathProgress.user_id == user_id,
                UserStoryPathProgress.path_id == path.id
            ).first()
            attempts = progress.attempts_used if progress else 0
            if attempts < path.max_attempts:
                available.append(path)
        return available
```

3. Inside `can_access_node`, after the VIP check and before the cost_besitos check, add:

```python
        # Verificar desbloqueo por racha
        if node.unlock_required_streak:
            from models.models import DailyGiftStreak
            streak = self.db.query(DailyGiftStreak).filter(
                DailyGiftStreak.user_id == user_id
            ).first()
            current = streak.current_streak if streak else 0
            if current < node.unlock_required_streak:
                return False, f"Necesita una racha de {node.unlock_required_streak} días para desbloquear este fragmento"

        # Verificar desbloqueo por besitos acumulados
        if node.unlock_required_besitos_total:
            from models.models import BesitoBalance
            balance = self.db.query(BesitoBalance).filter(
                BesitoBalance.user_id == user_id
            ).first()
            earned = balance.total_earned if balance else 0
            if earned < node.unlock_required_besitos_total:
                return False, f"Necesita haber acumulado {node.unlock_required_besitos_total} besitos para desbloquear este fragmento"
```

4. Add after `list_available_paths`:

```python
    def start_path(self, user_id: int, path_id: int, is_vip: bool) -> tuple:
        path = self.get_story_path(path_id)
        if not path or not path.is_active:
            return False, "Este sendero no está disponible", None

        available = self.list_available_paths(user_id, is_vip)
        if path not in available:
            return False, "No puedes acceder a este sendero", None

        sequence = json.loads(path.node_sequence)
        if not sequence:
            return False, "El sendero está vacío", None

        first_node_id = sequence[0]
        can_access, reason = self.can_access_node(user_id, first_node_id, is_vip)
        if not can_access:
            return False, reason, None

        progress = UserStoryPathProgress(
            user_id=user_id, path_id=path_id,
            current_node_index=0, attempts_used=1
        )
        self.db.add(progress)
        self.advance_to_node(user_id, first_node_id, is_vip=is_vip)
        self.db.commit()
        logger.info(f"Usuario {user_id} inició sendero {path_id}")
        return True, None, progress

    async def advance_path(self, user_id: int, path_id: int, choice_id: int,
                           is_vip: bool, bot=None) -> tuple:
        path = self.get_story_path(path_id)
        if not path:
            return False, "Sendero no encontrado", None

        progress = self.db.query(UserStoryPathProgress).filter(
            UserStoryPathProgress.user_id == user_id,
            UserStoryPathProgress.path_id == path_id
        ).first()
        if not progress:
            return False, "Aún no has iniciado este sendero", None
        if progress.is_completed:
            return False, "Este sendero ya ha sido completado", None

        sequence = json.loads(path.node_sequence)
        if progress.current_node_index >= len(sequence):
            return False, "Sendero finalizado", None

        node_id = sequence[progress.current_node_index]
        success, msg, _ = self.advance_to_node(
            user_id, node_id, choice_id=choice_id, is_vip=is_vip
        )
        if not success:
            return False, msg, None

        progress.current_node_index += 1

        if progress.current_node_index >= len(sequence):
            progress.is_completed = True
            progress.completed_at = datetime.now(timezone.utc)
            if path.reward_id and bot:
                from services.reward_service import RewardService
                reward_service = RewardService(self.db)
                await reward_service.deliver_reward(
                    bot, user_id, path.reward_id
                )
            logger.info(f"Usuario {user_id} completó sendero {path_id}")

        from services.mission_service import MissionService
        mission_service = MissionService(self.db)
        await mission_service.increment_progress_and_deliver(
            user_id, MissionType.STORY_NODE_VISIT, amount=1, bot=bot
        )

        self.db.commit()
        return True, None, progress
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_story_service.py -k "TestStoryPathCRUD or TestStoryNodeUnlock or TestStoryPathProgress"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for StoryPath and advancement</name>
<files>tests/unit/test_story_service.py</files>
<action>
Append to `tests/unit/test_story_service.py`:

```python
@pytest.mark.unit
class TestStoryPathCRUD:
    def test_create_story_path(self, db_session, sample_admin):
        service = StoryService(db_session)
        path = service.create_story_path(
            name="El Camino Oscuro",
            description="Un sendero misterioso",
            node_sequence=[1, 2, 3],
            max_attempts=2,
            created_by=sample_admin.telegram_id
        )
        assert path.name == "El Camino Oscuro"
        assert json.loads(path.node_sequence) == [1, 2, 3]

    def test_list_available_paths_filters_vip(self, db_session, sample_user, sample_admin):
        service = StoryService(db_session)
        service.create_story_path("Free Path", "", [1], is_vip_exclusive=False, created_by=sample_admin.telegram_id)
        service.create_story_path("VIP Path", "", [1], is_vip_exclusive=True, created_by=sample_admin.telegram_id)
        free_paths = service.list_available_paths(sample_user.id, is_vip=False)
        assert all(not p.is_vip_exclusive for p in free_paths)

    def test_list_available_paths_respects_attempts(self, db_session, sample_user, sample_admin):
        service = StoryService(db_session)
        path = service.create_story_path("Limited", "", [1], max_attempts=1, created_by=sample_admin.telegram_id)
        from models.models import UserStoryPathProgress
        progress = UserStoryPathProgress(user_id=sample_user.id, path_id=path.id, attempts_used=1)
        db_session.add(progress)
        db_session.commit()
        available = service.list_available_paths(sample_user.id, is_vip=False)
        assert path not in available


@pytest.mark.unit
class TestStoryNodeUnlock:
    def test_can_access_node_blocks_by_streak(self, db_session, sample_user, sample_admin):
        service = StoryService(db_session)
        node = service.create_node("Locked", "Locked", NodeType.NARRATIVE, chapter=1, unlock_required_streak=5)
        can_access, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can_access is False
        assert "racha" in reason.lower()

    def test_can_access_node_allows_when_streak_met(self, db_session, sample_user, sample_admin):
        service = StoryService(db_session)
        from models.models import DailyGiftStreak
        streak = DailyGiftStreak(user_id=sample_user.id, current_streak=5)
        db_session.add(streak)
        db_session.commit()
        node = service.create_node("Open", "Open", NodeType.NARRATIVE, chapter=1, unlock_required_streak=5)
        can_access, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can_access is True


@pytest.mark.unit
class TestStoryPathProgress:
    def test_start_path(self, db_session, sample_user, sample_admin):
        service = StoryService(db_session)
        from models.models import BesitoBalance
        bb = BesitoBalance(user_id=sample_user.id, balance=100, total_earned=100, total_spent=0)
        db_session.add(bb)
        node = service.create_node("Start", "Start node", NodeType.NARRATIVE, chapter=1)
        path = service.create_story_path("P", "", [node.id], created_by=sample_admin.telegram_id)
        success, msg, progress = service.start_path(sample_user.id, path.id, is_vip=False)
        assert success is True
        assert progress.current_node_index == 0
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_story_service.py</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
