"""
Unit tests for TriviaConfigService (pilot contract tests following gold pattern).

Pilots established across domains (besito, vip, mission, store, daily_gift, analytics, health, etc.):
- @pytest.mark.unit
- Direct Service(db_session) injection for units (consistent)
- DESIRED CONTRACT docstrings for key behaviors
- Use telegram_id for users/admins
- datetime.now(UTC) aware
- Cover get (auto-create defaults), update (valid only, ignores bad), return shape, lifecycle
- Small focused tests, no prints, deterministic
- Mirrors test_daily_gift_service.py + test_health_service.py + test_analytics_service.py

TriviaConfigService manages minigame limits + trivia besitos earning caps (daily/weekly).
"""

import pytest

from models.models import TriviaConfig
from services.trivia_config_service import DEFAULTS, TriviaConfigService


@pytest.mark.unit
class TestTriviaConfigServiceLifecycle:
    """Lifecycle mirrors Health/Analytics own-session pattern."""

    def test_owns_session_when_no_db(self):
        svc = TriviaConfigService()
        assert svc._owns_session is True
        assert svc.db is None  # lazy
        svc.close()
        assert svc.db is None

    def test_uses_passed_db_no_own(self, db_session):
        svc = TriviaConfigService(db=db_session)
        assert svc._owns_session is False
        svc.close()
        # should not have closed the passed one
        assert svc.db is db_session


@pytest.mark.unit
class TestTriviaConfigGet:
    """DESIRED CONTRACT: get_config always returns full dict of limits; creates TriviaConfig row with DEFAULTS on first access."""

    def test_get_config_creates_defaults_when_missing(self, db_session):
        # ensure no row
        existing = db_session.query(TriviaConfig).first()
        assert existing is None

        svc = TriviaConfigService(db_session)
        cfg = svc.get_config()

        assert isinstance(cfg, dict)
        assert cfg["dice_limit_free"] == DEFAULTS["dice_limit_free"]
        assert cfg["trivia_besitos_weekly_vip"] == DEFAULTS["trivia_besitos_weekly_vip"]
        # all keys present
        for k in DEFAULTS:
            assert k in cfg

        # row was created
        row = db_session.query(TriviaConfig).first()
        assert row is not None
        assert row.dice_limit_free == DEFAULTS["dice_limit_free"]

    def test_get_config_returns_existing(self, db_session):
        # pre-create with defaults then mutate for custom values
        db_session.add(TriviaConfig(**DEFAULTS))
        db_session.commit()
        row = db_session.query(TriviaConfig).first()
        row.dice_limit_free = 3
        row.trivia_limit_vip = 99
        db_session.commit()

        svc = TriviaConfigService(db_session)
        cfg = svc.get_config()
        assert cfg["dice_limit_free"] == 3
        assert cfg["trivia_limit_vip"] == 99


@pytest.mark.unit
class TestTriviaConfigUpdate:
    """DESIRED CONTRACT: update_config only mutates provided valid (>=0 int) keys; always sets updated_by + updated_at; returns full current config; ignores invalid keys/values; creates row if missing."""

    def test_update_config_valid_fields(self, db_session, sample_admin):
        svc = TriviaConfigService(db_session)
        # trigger create
        svc.get_config()

        result = svc.update_config(
            admin_id=sample_admin.telegram_id,
            trivia_limit_free=7,
            dice_limit_vip=30,
            trivia_besitos_daily_free=12,
            trivia_besitos_weekly_vip=50,
        )

        assert result["trivia_limit_free"] == 7
        assert result["dice_limit_vip"] == 30
        assert result["trivia_besitos_daily_free"] == 12
        assert result["trivia_besitos_weekly_vip"] == 50

        # verify persisted + metadata
        row = db_session.query(TriviaConfig).first()
        assert row.trivia_limit_free == 7
        assert row.updated_by == sample_admin.telegram_id
        assert row.updated_at is not None

    def test_update_ignores_invalid_keys_and_negative_and_non_int(self, db_session, sample_admin):
        svc = TriviaConfigService(db_session)
        svc.get_config()

        # mix valid + junk
        result = svc.update_config(
            admin_id=sample_admin.telegram_id,
            trivia_limit_free=8,
            not_a_field=999,
            dice_limit_free=-5,  # negative must be ignored
            trivia_simple_limit_vip="bad",  # non-int ignored
            trivia_besitos_daily_vip=20,
        )

        assert result["trivia_limit_free"] == 8
        assert result["trivia_besitos_daily_vip"] == 20
        # defaults or previous not changed for bads
        assert (
            result["dice_limit_free"] == DEFAULTS["dice_limit_free"]
        )  # still default since neg ignored

        row = db_session.query(TriviaConfig).first()
        assert row.trivia_limit_free == 8
        assert row.dice_limit_free == DEFAULTS["dice_limit_free"]  # not -5
        assert row.updated_by == sample_admin.telegram_id

    def test_update_creates_row_if_missing(self, db_session, sample_admin):
        # no prior config
        assert db_session.query(TriviaConfig).first() is None

        svc = TriviaConfigService(db_session)
        result = svc.update_config(admin_id=sample_admin.telegram_id, trivia_limit_vip=42)

        assert result["trivia_limit_vip"] == 42
        row = db_session.query(TriviaConfig).first()
        assert row is not None
        assert row.trivia_limit_vip == 42
        assert row.updated_by == sample_admin.telegram_id


@pytest.mark.unit
class TestTriviaConfigContractShape:
    """Ensure shape and keys match contract used by game_service etc."""

    def test_get_config_has_all_expected_keys(self, db_session):
        svc = TriviaConfigService(db_session)
        cfg = svc.get_config()
        expected = set(DEFAULTS.keys())
        assert set(cfg.keys()) == expected


@pytest.mark.unit
class TestGamifTriviaCapsExplicit:
    """Explicit gamif caps from TriviaConfigService (PLAN F2 hygiene).
    Pins DEFAULTS values returned by get_config for dice/trivia limits (free/vip).
    Real service + db. 0 beh. Re-runs protect game limits paths.
    """

    def test_get_config_explicit_caps_defaults_pinned(self, db_session):
        """All key limits pinned explicitly per configured DEFAULTS.
        dice_limit_free=10, dice_vip=20, trivia_* free/vip as DEFAULTS.
        """
        svc = TriviaConfigService(db_session)
        cfg = svc.get_config()

        # Explicit pins (caps exercised and asserted)
        assert cfg["dice_limit_free"] == 10
        assert cfg["dice_limit_vip"] == 20
        assert cfg["trivia_limit_free"] == 5
        assert cfg["trivia_limit_vip"] == 10
        assert cfg["trivia_simple_limit_free"] == 5
        assert cfg["trivia_simple_limit_vip"] == 10
        assert cfg["trivia_besitos_daily_free"] == 10
        assert cfg["trivia_besitos_daily_vip"] == 15
        # full set present (contract)
        for k in DEFAULTS:
            assert k in cfg
            assert isinstance(cfg[k], int)
