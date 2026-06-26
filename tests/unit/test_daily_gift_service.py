"""
Tests unitarios para DailyGiftService.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoBalance,
    BesitoTransaction,
    DailyGiftClaim,
    DailyGiftConfig,
    TransactionSource,
)
from services.besito_service import BesitoService
from services.daily_gift_service import DailyGiftService


@pytest.mark.unit
class TestDailyGiftConfig:
    """Tests para configuración del regalo diario"""

    def test_get_config_creates_default(self, db_session):
        """Test get_config crea configuración por defecto cuando no existe"""
        service = DailyGiftService(db_session)

        config = service.get_config()

        assert config is not None
        assert config.besito_amount == 10
        assert config.is_active is True

    def test_update_config(self, db_session, sample_admin):
        """Test actualizar configuración del regalo diario"""
        service = DailyGiftService(db_session)
        service.get_config()

        config = service.update_config(besito_amount=25, admin_id=sample_admin.telegram_id)

        assert config.besito_amount == 25
        assert config.updated_by == sample_admin.telegram_id

    def test_is_active(self, db_session):
        """Test verificar si el regalo diario está activo"""
        service = DailyGiftService(db_session)
        service.get_config()

        assert service.is_active() is True

        config = service.get_config()
        config.is_active = False
        db_session.commit()

        assert service.is_active() is False

    def test_get_gift_amount_active(self, db_session):
        """Test obtener cantidad de besitos cuando está activo"""
        service = DailyGiftService(db_session)
        service.get_config()

        assert service.get_gift_amount() == 10

    def test_get_gift_amount_inactive(self, db_session):
        """Test obtener cantidad de besitos cuando está inactivo retorna 0"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        assert service.get_gift_amount() == 0


@pytest.mark.unit
class TestDailyGiftClaims:
    """Tests para reclamos del regalo diario"""

    def test_can_claim_first_time(self, db_session, sample_user):
        """Test primer reclamo siempre permite"""
        service = DailyGiftService(db_session)

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is True
        assert remaining is None
        assert "puedes reclamar" in msg.lower()

    def test_can_claim_cooldown_active(self, db_session, sample_user):
        """Test cooldown de 24 horas impide reclamo"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(claim)
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is False
        assert remaining is not None
        assert "debes esperar" in msg.lower()

    def test_can_claim_after_24_hours(self, db_session, sample_user):
        """Test después de 24 horas se puede reclamar de nuevo"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=25),
        )
        db_session.add(claim)
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is True
        assert remaining is None

    def test_can_claim_inactive(self, db_session, sample_user):
        """Test cuando el regalo diario está inactivo no se puede reclamar"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is False
        assert "no está disponible" in msg.lower()

    def test_claim_gift_success(self, db_session, sample_user):
        """Test reclamar regalo acredita besitos y crea registro"""
        service = DailyGiftService(db_session)

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is True
        assert amount == 10
        balance = (
            service.besito_service.get_balance(sample_user.telegram_id)
            if hasattr(service, "besito_service")
            else BesitoService(db_session).get_balance(sample_user.telegram_id)
        )  # 1-line fix + guard post local-in-claim (F5); daily precedent
        assert balance == 10

        history = service.get_claim_history(sample_user.telegram_id)
        assert len(history) == 1
        assert history[0].besitos_received == 10

    def test_claim_gift_cooldown_blocks(self, db_session, sample_user):
        """Test reclamar durante cooldown falla"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(claim)
        db_session.commit()

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is False
        assert amount is None
        assert "debes esperar" in msg.lower()

    def test_claim_gift_inactive(self, db_session, sample_user):
        """Test reclamar cuando está inactivo falla"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is False
        assert amount is None
        assert "no está disponible" in msg.lower()


@pytest.mark.unit
class TestDailyGiftStats:
    """Tests para estadísticas del regalo diario"""

    def test_get_total_claims_today(self, db_session, sample_user):
        """Test contar reclamos del día actual"""
        service = DailyGiftService(db_session)
        # Reclamo de hoy
        claim1 = DailyGiftClaim(user_id=sample_user.telegram_id, besitos_received=10)
        db_session.add(claim1)
        # Reclamo de ayer
        claim2 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add(claim2)
        db_session.commit()

        total = service.get_total_claims_today()

        assert total == 1

    def test_get_total_besitos_given_today(self, db_session, sample_user):
        """Test sumar besitos entregados hoy"""
        service = DailyGiftService(db_session)
        claim1 = DailyGiftClaim(user_id=sample_user.telegram_id, besitos_received=10)
        claim2 = DailyGiftClaim(user_id=999999, besitos_received=5)
        claim3 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=20,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add_all([claim1, claim2, claim3])
        db_session.commit()

        total = service.get_total_besitos_given_today()

        assert total == 15

    def test_get_claim_history_order(self, db_session, sample_user):
        """Test historial de reclamos ordenado descendente por fecha"""
        service = DailyGiftService(db_session)
        claim1 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=2),
        )
        claim2 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        claim3 = DailyGiftClaim(
            user_id=sample_user.telegram_id, besitos_received=10, claimed_at=datetime.now(UTC)
        )
        db_session.add_all([claim1, claim2, claim3])
        db_session.commit()

        history = service.get_claim_history(sample_user.telegram_id)

        assert len(history) == 3
        assert history[0].claimed_at >= history[1].claimed_at >= history[2].claimed_at

    def test_get_claim_history_respects_limit(self, db_session, sample_user):
        """Test historial respeta el límite"""
        service = DailyGiftService(db_session)
        for i in range(5):
            claim = DailyGiftClaim(
                user_id=sample_user.telegram_id,
                besitos_received=10,
                claimed_at=datetime.now(UTC) - timedelta(hours=i),
            )
            db_session.add(claim)
        db_session.commit()

        history = service.get_claim_history(sample_user.telegram_id, limit=3)

        assert len(history) == 3


@pytest.mark.unit
class TestDailyGiftConcurrentClaim:
    """
    DESIRED CONTRACT (Item 4 / F2 gamif daily): concurrent claim (first time race window) -> at most 1 success/claim row/credit.
    Copia gather+to_thread+return_exceptions + successes filter + <=1 + count<=1 de broadcast/besito concurrent (file variant si coop, aquí db_session por unit).
    Usa sample TG (contract). Build on daily atomic pilot in cross (claim+credit visibility post internal).
    """

    def _create_engine_and_session(self, tmp_path):
        """SQLite file + TestSession (gold pattern: besito concurrent + daily atomicity)."""
        db_path = tmp_path / "test_daily_concurrent.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa: N806
        return engine, TestSession

    async def test_concurrent_first_claims_at_most_one_succeeds(self, tmp_path):
        """Two concurrent first claims: at most 1 succeeds (claim row + credit); no double besitos.

        Uses isolated file SQLite + separate TestSession per thread (not SessionLocal/prod DB).
        """
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        tg = 77709010

        setup = TestSession()
        try:
            setup.add_all(
                [
                    DailyGiftConfig(besito_amount=10, is_active=True),
                    BesitoBalance(user_id=tg, balance=0, total_earned=0, total_spent=0),
                ]
            )
            setup.commit()
        finally:
            setup.close()

        def _claim_with_own_session():
            sess = TestSession()
            try:
                with patch("services.event_bus.schedule_emit"):
                    return DailyGiftService(sess).claim_gift(tg)
            finally:
                sess.close()

        try:
            results = await asyncio.gather(
                asyncio.to_thread(_claim_with_own_session),
                asyncio.to_thread(_claim_with_own_session),
                return_exceptions=True,
            )

            successes = [r for r in results if isinstance(r, tuple) and r[0] is True]
            assert len(successes) <= 1

            verify = TestSession()
            try:
                claim_count = (
                    verify.query(DailyGiftClaim).filter(DailyGiftClaim.user_id == tg).count()
                )
                assert claim_count <= 1
                assert BesitoService(verify).get_balance(tg) <= 10
            finally:
                verify.close()
        finally:
            engine.dispose()

    def test_property_kept_for_guard_and_compat(self, db_session, sample_user):
        """Post Item 6: @property besito_service kept (for test guards/compat + hasattr precedent) even though claim_gift uses local inside."""
        service = DailyGiftService(db_session)
        assert hasattr(service, "besito_service")
        # property still instantiates (lazy) for guards in 1-line sites / cross atomicity patches
        _ = service.besito_service  # access ok
        service.close()

    def test_claim_gift_uses_local_besito_inside(
        self, db_session, sample_user, sample_daily_gift_config
    ):
        """
        DESIRED CONTRACT (Item 6): claim_gift uses local BesitoService(db=self._get_db()) *only inside*
        the credit block (not the held prop for the credit path); schedule_emit still fires best-effort from
        the local credit; claim row + DAILY_GIFT tx + balance persist on happy; 0 behavior/0 atomicity change.
        Guards in tests (hasattr + fallback) continue to work.
        """
        service = DailyGiftService(db_session)
        with patch("services.event_bus.schedule_emit") as mock_emit:
            success, amt, msg = service.claim_gift(sample_user.telegram_id)
            assert success is True
            assert amt == 10
            assert mock_emit.called  # from inside the *local* Besito(db=_get_db()) credit inside claim_gift (Item 6); real path
        # credit survives + DAILY_GIFT tx present (re-query) + balance delta
        tx = (
            db_session.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == sample_user.telegram_id,
                BesitoTransaction.source == TransactionSource.DAILY_GIFT,
            )
            .first()
        )
        assert tx is not None
        assert tx.amount == 10
        final_bal = BesitoService(db_session).get_balance(sample_user.telegram_id)
        assert final_bal == 10
        service.close()


@pytest.mark.unit
class TestGamifDailyCapsExplicit:
    """Explicit daily cap: once-per-day claim enforced (per PLAN F2 caps hygiene).
    Real DailyGiftService + credit path. Copy daily guards + 1-line/guard style if bal.
    0 beh change. UI/return messages pinned for hygiene.
    """

    def test_claim_gift_once_per_day_explicit(self, db_session, sample_user):
        """First claim succeeds (credit + claim row); second same day blocks with cooldown msg.
        Exercises the daily cap explicitly (no two claims within 24h window).
        """
        service = DailyGiftService(db_session)

        # First claim: success
        ok1, amt1, msg1 = service.claim_gift(sample_user.telegram_id)
        assert ok1 is True
        assert amt1 == 10
        # 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service
        bal = (
            BesitoService(db=db_session).get_balance(sample_user.telegram_id)
            if not hasattr(service, "besito_service")
            else service.besito_service.get_balance(sample_user.telegram_id)
        )
        assert bal == 10

        # force not hasattr path for guard fidelity (per review; bare object to hit independent BesitoService branch)
        bare = object()
        bal_bare = (
            BesitoService(db=db_session).get_balance(sample_user.telegram_id)
            if not hasattr(bare, "besito_service")
            else getattr(bare, "besito_service", None)
        )
        assert bal_bare == 10

        # Second claim immediately (same day): must block
        ok2, amt2, msg2 = service.claim_gift(sample_user.telegram_id)
        assert ok2 is False
        assert amt2 is None
        assert "debes esperar" in (msg2 or "").lower() or "cooldown" in (msg2 or "").lower() or "esperar" in (msg2 or "").lower()

        # Balance unchanged (cap protected)
        bal2 = BesitoService(db=db_session).get_balance(sample_user.telegram_id)
        assert bal2 == 10
