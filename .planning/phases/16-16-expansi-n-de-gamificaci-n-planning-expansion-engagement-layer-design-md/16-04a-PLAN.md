---
phase: 16
plan: 16-04a
wave: 4
depends_on: ["16-01a", "16-02a", "16-03a"]
files_modified:
  - models/models.py
  - services/reward_service.py
  - tests/unit/test_reward_service.py
autonomous: true
type: auto
must_haves:
  - User can claim one free daily whisper and, if VIP, one VIP daily whisper
  - Whisper rewards are selected by weighted random choice from configurable pools
  - Duplicate daily claims are blocked and race conditions are protected against
---

# Plan 16-04a: Susurros de Diana — Models, Migrations, and RewardService Methods

**Objective:** Implement the database schema and core service logic for the Susurros de Diana daily reward whisper system.

**Requirements mapped:** ENG-04, ENG-06

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section IV (Susurros de Diana)
- `services/reward_service.py`
- `models/models.py`

---

<task>
<name>Add Whisper models to models.py</name>
<files>models/models.py</files>
<action>
In `models/models.py`:
1. Ensure `from sqlalchemy import Date` is imported (add if missing).
2. Add `WhisperRewardPool`, `WhisperRewardItem`, and `WhisperClaim` classes immediately after the `UserRewardHistory` class in the FASE 3 section.

`WhisperRewardPool`:
- `__tablename__ = 'whisper_reward_pools'`
- `id = Column(Integer, primary_key=True, index=True)`
- `name = Column(String(200), nullable=False)`
- `code = Column(String(50), unique=True, nullable=False, index=True)`
- `is_active = Column(Boolean, default=True)`
- `created_at = Column(DateTime(timezone=True), server_default=func.now())`
- `items = relationship('WhisperRewardItem', back_populates='pool', cascade='all, delete-orphan')`

`WhisperRewardItem`:
- `__tablename__ = 'whisper_reward_items'`
- `id = Column(Integer, primary_key=True, index=True)`
- `pool_id = Column(Integer, ForeignKey('whisper_reward_pools.id'), nullable=False, index=True)`
- `reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=False)`
- `weight = Column(Integer, default=1, nullable=False)`
- `pool = relationship('WhisperRewardPool', back_populates='items')`
- `reward = relationship('Reward')`

`WhisperClaim`:
- `__tablename__ = 'whisper_claims'`
- `id = Column(Integer, primary_key=True, index=True)`
- `user_id = Column(BigInteger, nullable=False, index=True)`
- `claim_date = Column(Date, nullable=False)`
- `pool_id = Column(Integer, ForeignKey('whisper_reward_pools.id'), nullable=False)`
- `reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=False)`
- `claimed_at = Column(DateTime(timezone=True), server_default=func.now())`
- `__table_args__ = (UniqueConstraint('user_id', 'claim_date', 'pool_id', name='uq_user_whisper_daily'),)`
</action>
<verify>
<command>python -c "from models.models import WhisperRewardPool, WhisperRewardItem, WhisperClaim; print(WhisperRewardPool.__tablename__, WhisperRewardItem.__tablename__, WhisperClaim.__tablename__)"</command>
<expected>whisper_reward_pools whisper_reward_items whisper_claims</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Create Alembic migrations for whisper tables</name>
<files>alembic/versions/20250415_add_whisper_reward_pools.py, alembic/versions/20250415_add_whisper_reward_items.py, alembic/versions/20250415_add_whisper_claims.py</files>
<action>
Create three migration files:

1. `alembic/versions/20250415_add_whisper_reward_pools.py`:
   - `revision = '20250415_whisper_pools'`
   - `down_revision = '20250415_user_story_path_progress'`
   - `upgrade()`: create `whisper_reward_pools`
   - `downgrade()`: drop `whisper_reward_pools`

2. `alembic/versions/20250415_add_whisper_reward_items.py`:
   - `revision = '20250415_whisper_items'`
   - `down_revision = '20250415_whisper_pools'`
   - `upgrade()`: create `whisper_reward_items`
   - `downgrade()`: drop `whisper_reward_items`

3. `alembic/versions/20250415_add_whisper_claims.py`:
   - `revision = '20250415_whisper_claims'`
   - `down_revision = '20250415_whisper_items'`
   - `upgrade()`: create `whisper_claims` with unique constraint
   - `downgrade()`: drop `whisper_claims`
</action>
<verify>
<command>alembic upgrade head && alembic downgrade -1</command>
<expected>0</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Extend RewardService with whisper pool CRUD and claim logic</name>
<files>services/reward_service.py</files>
<action>
In `services/reward_service.py`:

1. Add to imports: `from models.models import WhisperRewardPool, WhisperRewardItem, WhisperClaim` and `from datetime import date` and `import random`

2. Add methods before `deliver_reward`:

```python
    def create_whisper_pool(self, name: str, code: str) -> WhisperRewardPool:
        pool = WhisperRewardPool(name=name, code=code, is_active=True)
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)
        logger.info(f"WhisperPool creado: {name} ({code})")
        return pool

    def get_whisper_pool_by_code(self, code: str) -> Optional[WhisperRewardPool]:
        return self.db.query(WhisperRewardPool).filter(
            WhisperRewardPool.code == code,
            WhisperRewardPool.is_active == True
        ).first()

    def add_item_to_whisper_pool(self, pool_id: int, reward_id: int,
                                 weight: int = 1) -> WhisperRewardItem:
        item = WhisperRewardItem(
            pool_id=pool_id, reward_id=reward_id, weight=weight
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info(f"WhisperItem agregado: pool={pool_id}, reward={reward_id}")
        return item

    def remove_item_from_whisper_pool(self, item_id: int) -> bool:
        item = self.db.query(WhisperRewardItem).filter(
            WhisperRewardItem.id == item_id
        ).first()
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        logger.info(f"WhisperItem eliminado: {item_id}")
        return True

    def list_whisper_pools(self) -> List[WhisperRewardPool]:
        return self.db.query(WhisperRewardPool).order_by(
            WhisperRewardPool.created_at.desc()
        ).all()

    def can_claim_whisper(self, user_id: int, is_vip: bool) -> dict:
        today = date.today()
        free_pool = self.get_whisper_pool_by_code("free_daily")
        vip_pool = self.get_whisper_pool_by_code("vip_daily")

        free_claimed = 0
        if free_pool:
            free_claimed = self.db.query(WhisperClaim).filter(
                WhisperClaim.user_id == user_id,
                WhisperClaim.claim_date == today,
                WhisperClaim.pool_id == free_pool.id
            ).count()

        vip_claimed = 0
        if vip_pool:
            vip_claimed = self.db.query(WhisperClaim).filter(
                WhisperClaim.user_id == user_id,
                WhisperClaim.claim_date == today,
                WhisperClaim.pool_id == vip_pool.id
            ).count()

        return {
            "free_daily": free_pool is not None and free_claimed == 0,
            "vip_daily": is_vip and vip_pool is not None and vip_claimed == 0,
            "free_claimed_today": free_claimed,
            "vip_claimed_today": vip_claimed
        }

    async def claim_whisper(self, user_id: int, pool_code: str, bot=None) -> dict:
        pool = self.get_whisper_pool_by_code(pool_code)
        if not pool:
            return {"success": False, "message": "Pool no encontrado"}

        # Lock user-scoped row to prevent race conditions
        self.besito_service.get_or_create_balance(user_id, lock=True)

        today = date.today()
        existing = self.db.query(WhisperClaim).filter(
            WhisperClaim.user_id == user_id,
            WhisperClaim.claim_date == today,
            WhisperClaim.pool_id == pool.id
        ).first()
        if existing:
            self.db.rollback()
            return {"success": False, "message": "Ya reclamaste este susurro hoy"}

        items = self.db.query(WhisperRewardItem).filter(
            WhisperRewardItem.pool_id == pool.id
        ).all()
        if not items:
            self.db.rollback()
            return {"success": False, "message": "El pool está vacío"}

        selected = random.choices(
            items, weights=[i.weight for i in items], k=1
        )[0]

        success, msg = await self.deliver_reward(
            bot, user_id, selected.reward_id
        )
        if not success:
            self.db.rollback()
            return {"success": False, "message": msg}

        claim = WhisperClaim(
            user_id=user_id,
            claim_date=today,
            pool_id=pool.id,
            reward_id=selected.reward_id
        )
        self.db.add(claim)

        from services.mission_service import MissionService
        mission_service = MissionService(self.db)
        await mission_service.increment_progress_and_deliver(
            user_id, MissionType.WHISPER_CLAIM, amount=1, bot=bot
        )

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            return {"success": False, "message": "Ya reclamaste este susurro hoy"}

        reward = self.get_reward(selected.reward_id)
        return {
            "success": True,
            "reward_name": reward.name if reward else "Misterio",
            "message": msg
        }
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_reward_service.py -k "TestWhisperPoolCRUD or TestWhisperClaim"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for whisper pools, limits, and claims</name>
<files>tests/unit/test_reward_service.py</files>
<action>
Append to `tests/unit/test_reward_service.py`:

```python
@pytest.mark.unit
class TestWhisperPoolCRUD:
    def test_create_whisper_pool(self, db_session):
        service = RewardService(db_session)
        pool = service.create_whisper_pool("Free Daily", "free_daily")
        assert pool.code == "free_daily"
        assert pool.is_active is True

    def test_add_item_to_pool(self, db_session, sample_reward):
        service = RewardService(db_session)
        pool = service.create_whisper_pool("Free Daily", "free_daily")
        item = service.add_item_to_whisper_pool(pool.id, sample_reward.id, weight=5)
        assert item.pool_id == pool.id
        assert item.weight == 5

    def test_remove_item_from_pool(self, db_session, sample_reward):
        service = RewardService(db_session)
        pool = service.create_whisper_pool("Free Daily", "free_daily")
        item = service.add_item_to_whisper_pool(pool.id, sample_reward.id)
        ok = service.remove_item_from_whisper_pool(item.id)
        assert ok is True


@pytest.mark.unit
class TestWhisperClaim:
    def test_can_claim_whisper_eligible(self, db_session, sample_user):
        service = RewardService(db_session)
        service.create_whisper_pool("Free Daily", "free_daily")
        status = service.can_claim_whisper(sample_user.id, is_vip=False)
        assert status["free_daily"] is True

    def test_claim_whisper_records_claim(self, db_session, sample_user, sample_reward, mock_bot):
        import asyncio
        service = RewardService(db_session)
        pool = service.create_whisper_pool("Free Daily", "free_daily")
        service.add_item_to_whisper_pool(pool.id, sample_reward.id, weight=1)
        result = asyncio.run(service.claim_whisper(sample_user.id, "free_daily", bot=mock_bot))
        assert result["success"] is True
        from models.models import WhisperClaim
        claims = db_session.query(WhisperClaim).all()
        assert len(claims) == 1

    def test_claim_whisper_blocks_duplicate(self, db_session, sample_user, sample_reward, mock_bot):
        import asyncio
        service = RewardService(db_session)
        pool = service.create_whisper_pool("Free Daily", "free_daily")
        service.add_item_to_whisper_pool(pool.id, sample_reward.id, weight=1)
        asyncio.run(service.claim_whisper(sample_user.id, "free_daily", bot=mock_bot))
        result = asyncio.run(service.claim_whisper(sample_user.id, "free_daily", bot=mock_bot))
        assert result["success"] is False
        assert "hoy" in result["message"].lower()
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_reward_service.py -k "TestWhisperPoolCRUD or TestWhisperClaim"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
