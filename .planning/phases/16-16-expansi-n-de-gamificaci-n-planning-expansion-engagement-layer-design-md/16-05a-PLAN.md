---
phase: 16
plan: 16-05a
wave: 5
depends_on: ["16-01a", "16-02a", "16-03a", "16-04a"]
files_modified:
  - services/besito_service.py
  - services/mission_service.py
  - tests/unit/test_besito_service.py
  - tests/unit/test_mission_service.py
autonomous: true
type: auto
must_haves:
  - User can view anonymous percentile for besitos and mission completions
  - Percentiles are displayed as soft buckets (top 5%, top 10%, top 20%, top 50%, top 100%) without exact ranks or names
  - Percentile logic is covered by unit tests for both services
---

# Plan 16-05a: Percentiles Anónimos — Service Methods and Tests

**Objective:** Implement anonymous percentile queries for besitos and missions with SQLite/PostgreSQL compatibility.

**Requirements mapped:** ENG-05

**Context references:**
- `.planning/expansion_engagement_layer/DESIGN.md` Section V (Estadísticas Anónimas)
- `services/besito_service.py`
- `services/mission_service.py`
- `.planning/phases/16-16-expansi-n-de-gamificaci-n-planning-expansion-engagement-layer-design-md/16-RESEARCH.md`

---

<task>
<name>Implement get_percentile in BesitoService</name>
<files>services/besito_service.py</files>
<action>
Add to `services/besito_service.py`:

```python
    def get_percentile(self, user_id: int) -> str:
        db = self._get_db()
        balances = db.query(BesitoBalance).order_by(
            BesitoBalance.balance.desc()
        ).all()

        if not balances:
            return "top 100%"

        rank = None
        for i, b in enumerate(balances, start=1):
            if b.user_id == user_id:
                rank = i
                break

        if rank is None:
            return "top 100%"

        total = len(balances)
        ratio = rank / total

        if ratio <= 0.05:
            return "top 5%"
        elif ratio <= 0.10:
            return "top 10%"
        elif ratio <= 0.20:
            return "top 20%"
        elif ratio <= 0.50:
            return "top 50%"
        return "top 100%"
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_besito_service.py -k "TestBesitoPercentile"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Implement get_percentile in MissionService</name>
<files>services/mission_service.py</files>
<action>
Add to `services/mission_service.py`:

```python
    def get_percentile(self, user_id: int) -> str:
        db = self._get_db()
        from sqlalchemy import func
        subquery = db.query(
            UserMissionProgress.user_id,
            func.count(UserMissionProgress.id).label("completed_count")
        ).filter(
            UserMissionProgress.is_completed == True
        ).group_by(
            UserMissionProgress.user_id
        ).subquery()

        results = db.query(
            subquery.c.user_id,
            subquery.c.completed_count
        ).order_by(
            subquery.c.completed_count.desc()
        ).all()

        if not results:
            return "top 100%"

        rank = None
        for i, (uid, _) in enumerate(results, start=1):
            if uid == user_id:
                rank = i
                break

        if rank is None:
            return "top 100%"

        total = len(results)
        ratio = rank / total

        if ratio <= 0.05:
            return "top 5%"
        elif ratio <= 0.10:
            return "top 10%"
        elif ratio <= 0.20:
            return "top 20%"
        elif ratio <= 0.50:
            return "top 50%"
        return "top 100%"
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_mission_service.py -k "TestMissionPercentile"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>

<task>
<name>Add unit tests for percentile logic</name>
<files>tests/unit/test_besito_service.py, tests/unit/test_mission_service.py</files>
<action>
Append to `tests/unit/test_besito_service.py`:

```python
@pytest.mark.unit
class TestBesitoPercentile:
    def test_get_percentile_top_user(self, db_session, sample_user):
        service = BesitoService(db_session)
        result = service.get_percentile(sample_user.id)
        assert result == "top 5%"

    def test_get_percentile_middle_user(self, db_session):
        service = BesitoService(db_session)
        from models.models import User
        u1 = User(telegram_id=900001, username="a")
        u2 = User(telegram_id=900002, username="b")
        u3 = User(telegram_id=900003, username="c")
        db_session.add_all([u1, u2, u3])
        db_session.commit()
        service.credit_besitos(u1.id, 300, TransactionSource.DAILY_GIFT)
        service.credit_besitos(u2.id, 200, TransactionSource.DAILY_GIFT)
        service.credit_besitos(u3.id, 100, TransactionSource.DAILY_GIFT)
        assert service.get_percentile(u2.id) == "top 50%"
```

Append to `tests/unit/test_mission_service.py`:

```python
@pytest.mark.unit
class TestMissionPercentile:
    def test_get_percentile_no_missions(self, db_session, sample_user):
        service = MissionService(db_session)
        result = service.get_percentile(sample_user.id)
        assert result == "top 100%"

    def test_get_percentile_with_completions(self, db_session, sample_user):
        service = MissionService(db_session)
        from models.models import User, Mission, UserMissionProgress
        u2 = User(telegram_id=900004, username="d")
        db_session.add(u2)
        db_session.commit()
        m = Mission(name="P", mission_type=MissionType.REACTION_COUNT, target_value=1, is_active=True)
        db_session.add(m)
        db_session.commit()
        p1 = UserMissionProgress(user_id=sample_user.id, mission_id=m.id, target_value=1, current_value=1, is_completed=True)
        p2 = UserMissionProgress(user_id=u2.id, mission_id=m.id, target_value=1, current_value=1, is_completed=True)
        db_session.add_all([p1, p2])
        db_session.commit()
        assert service.get_percentile(sample_user.id) == "top 5%"
        assert service.get_percentile(u2.id) == "top 50%"
```
</action>
<verify>
<command>pytest -xvs tests/unit/test_besito_service.py -k "TestBesitoPercentile" && pytest -xvs tests/unit/test_mission_service.py -k "TestMissionPercentile"</command>
<expected>passed</expected>
</verify>
<done>false</done>
</task>
