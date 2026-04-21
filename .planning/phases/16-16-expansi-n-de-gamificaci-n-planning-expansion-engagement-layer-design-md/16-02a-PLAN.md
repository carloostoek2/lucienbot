---
phase: 16
plan: 16-02a
wave: 2
depends_on: ["16-01a"]
files_modified:
  - models/models.py
  - services/mission_service.py
  - tests/unit/test_mission_service.py
autonomous: true
type: auto
must_haves:
  - Admin can create and manage mission templates with type, target value, reward, weight, and VIP exclusivity
  - MissionTemplate CRUD operations are covered by unit tests
---

# Plan 16-02a: Misiones Dinámicas — Model, Migration, and Template CRUD

**Objective:** Implement the `MissionTemplate` model, its migration, and CRUD methods in `MissionService`.

**Requirements mapped:** ENG-03, ENG-06

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section III (Misiones Dinámicas)
- `services/mission_service.py`
- `models/models.py`

---

<task>
<name>Add MissionTemplate model to models.py</name>
<files>models/models.py</files>
<action>
In `models/models.py`, add `MissionTemplate` class immediately after the `Reward` class in the FASE 3 section with:
- `__tablename__ = 'mission_templates'`
- `id = Column(Integer, primary_key=True, index=True)`
- `name = Column(String(200), nullable=False)`
- `mission_type = Column(Enum(MissionType), nullable=False)`
- `target_value = Column(Integer, default=1, nullable=False)`
- `reward_id = Column(Integer, ForeignKey('rewards.id'), nullable=False)`
- `weight = Column(Integer, default=1, nullable=False)`
- `is_vip_exclusive = Column(Boolean, default=False)`
- `is_active = Column(Boolean, default=True)`
- `created_by = Column(BigInteger, nullable=True)`
- `created_at = Column(DateTime(timezone=True), server_default=func.now())`
- `reward = relationship('Reward')`
</action>
<verify>
<command>python -c "from models.models import MissionTemplate; print(MissionTemplate.__tablename__)"</command>
<expected>mission_templates</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Create Alembic migration for mission_templates table</name>
<files>alembic/versions/20250415_add_mission_templates_table.py</files>
<action>
Create `alembic/versions/20250415_add_mission_templates_table.py`:
- `revision = '20250415_mission_templates'`
- `down_revision = '20250415_daily_gift_streaks'`
- `upgrade()`: `op.create_table('mission_templates', ...)` with all columns
- `downgrade()`: `op.drop_table('mission_templates')`
</action>
<verify>
<command>alembic upgrade head && alembic downgrade -1</command>
<expected>0</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Extend MissionService with MissionTemplate CRUD</name>
<files>services/mission_service.py</files>
<action>
In `services/mission_service.py`:
1. Add `MissionTemplate` to the imports from `models.models`.
2. Add the CRUD methods after the existing `delete_mission` method, before statistics:

```python
def create_mission_template(self, name: str, mission_type: MissionType,
                            target_value: int, reward_id: int,
                            weight: int = 1, is_vip_exclusive: bool = False,
                            created_by: int = None) -> MissionTemplate:
    db = self._get_db()
    template = MissionTemplate(
        name=name, mission_type=mission_type, target_value=target_value,
        reward_id=reward_id, weight=weight, is_vip_exclusive=is_vip_exclusive,
        created_by=created_by, is_active=True
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    logger.info(f"MissionTemplate creada: {name} (ID: {template.id})")
    return template

def get_mission_template(self, template_id: int) -> Optional[MissionTemplate]:
    return self._get_db().query(MissionTemplate).filter(
        MissionTemplate.id == template_id
    ).first()

def get_all_mission_templates(self, active_only: bool = True) -> List[MissionTemplate]:
    db = self._get_db()
    query = db.query(MissionTemplate)
    if active_only:
        query = query.filter(MissionTemplate.is_active == True)
    return query.order_by(desc(MissionTemplate.created_at)).all()

def update_mission_template(self, template_id: int, **kwargs) -> bool:
    db = self._get_db()
    template = self.get_mission_template(template_id)
    if not template:
        return False
    allowed = ['name', 'mission_type', 'target_value', 'reward_id',
               'weight', 'is_vip_exclusive', 'is_active']
    for field, value in kwargs.items():
        if field in allowed and hasattr(template, field):
            setattr(template, field, value)
    db.commit()
    logger.info(f"MissionTemplate {template_id} actualizada")
    return True

def delete_mission_template(self, template_id: int) -> bool:
    template = self.get_mission_template(template_id)
    if not template:
        logger.warning(f"MissionTemplate {template_id} no encontrada")
        return False
    db = self._get_db()
    db.delete(template)
    db.commit()
    logger.info(f"MissionTemplate {template_id} eliminada")
    return True
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_mission_service.py -k "TestMissionTemplateCRUD"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for MissionTemplate CRUD</name>
<files>tests/unit/test_mission_service.py</files>
<action>
Append to `tests/unit/test_mission_service.py`:

```python
@pytest.mark.unit
class TestMissionTemplateCRUD:
    def test_create_mission_template(self, db_session, sample_reward):
        service = MissionService(db_session)
        template = service.create_mission_template(
            name="Test Template",
            mission_type=MissionType.REACTION_COUNT,
            target_value=5,
            reward_id=sample_reward.id,
            weight=2,
            is_vip_exclusive=False
        )
        assert template.name == "Test Template"
        assert template.weight == 2

    def test_get_all_mission_templates(self, db_session, sample_reward):
        service = MissionService(db_session)
        service.create_mission_template("T1", MissionType.REACTION_COUNT, 1, sample_reward.id)
        service.create_mission_template("T2", MissionType.REACTION_COUNT, 1, sample_reward.id, is_active=False)
        templates = service.get_all_mission_templates()
        assert all(t.is_active for t in templates)

    def test_update_mission_template(self, db_session, sample_reward):
        service = MissionService(db_session)
        t = service.create_mission_template("Old", MissionType.REACTION_COUNT, 1, sample_reward.id)
        ok = service.update_mission_template(t.id, name="New", weight=10)
        assert ok is True
        assert service.get_mission_template(t.id).name == "New"

    def test_delete_mission_template(self, db_session, sample_reward):
        service = MissionService(db_session)
        t = service.create_mission_template("Del", MissionType.REACTION_COUNT, 1, sample_reward.id)
        ok = service.delete_mission_template(t.id)
        assert ok is True
        assert service.get_mission_template(t.id) is None
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_mission_service.py -k "TestMissionTemplateCRUD"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
