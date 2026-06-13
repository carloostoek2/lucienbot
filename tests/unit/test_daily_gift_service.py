"""
Tests unitarios para DailyGiftService.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from models.models import BesitoTransaction, DailyGiftClaim, DailyGiftConfig, TransactionSource
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

    async def test_concurrent_first_claims_at_most_one_succeeds(self, db_session, sample_user):
        """
        Two concurrent first claims: at most 1 succeeds (claim row + credit); no double besitos.

        NOTE on fragility (shared db_session across to_thread): Session is not thread-safe.
        Real concurrent protection golds use file-based SQLite + isolated sessions (see cross_service_atomicity
        and the "file variant" comments). Here we tolerate exceptions in results (expected loser path when
        hitting unique on DailyGiftClaim or related during race) + explicit session cleanup before asserts.
        This reduces leaking IntegrityError as top-level test failure.
        """
        service = DailyGiftService(db_session)
        tg = sample_user.telegram_id

        # Pre-create config to avoid concurrent default creation inside claim_gift.get_config() (would hit UNIQUE on daily_gift_config.id=1 from 2 threads).
        # This lets the race be on the claim/credit path itself (the intended for this test).
        cfg = DailyGiftConfig(besito_amount=10, is_active=True)
        db_session.add(cfg)
        db_session.commit()
        db_session.expire_all()

        results = await asyncio.gather(
            asyncio.to_thread(service.claim_gift, tg),
            asyncio.to_thread(service.claim_gift, tg),
            return_exceptions=True,
        )

        # Explicitly tolerate exceptions in results: the "loser" of the first-claim race may surface
        # as IntegrityError (constraint) or other, caught inside claim_gift or bubbling from thread.
        # We only care that the *business* outcome (successes + claim rows + balance) respects the contract.
        successes = [r for r in results if isinstance(r, tuple) and r[0] is True]
        assert len(successes) <= 1

        # Note: we do NOT force rollback/expire here to avoid de-associating the tx from the test fixture
        # (which can trigger SAWarning + failures in some runs). The original expire_all() before gather
        # + the filter on results already provide the tolerance. Full isolation is in the integration
        # file-variant versions of concurrent atomicity tests.
        claim_count = db_session.query(DailyGiftClaim).filter(DailyGiftClaim.user_id == tg).count()
        assert claim_count <= 1

        bal = (
            service.besito_service.get_balance(tg)
            if hasattr(service, "besito_service")
            else BesitoService(db_session).get_balance(tg)
        )  # 1-line fix post local-in-claim (F5); daily precedent guard preserved
        assert bal <= 10  # default config amt; never double in race

        # Exceptions (e.g. IntegrityError) appearing in `results` are acceptable for the race loser path.
        # The test uses return_exceptions=True precisely because the second concurrent claim can hit
        # DB constraints (unique on claim or besito tx) or application checks. The filter + asserts
        # verify the contract regardless of whether the loser returned a tuple or an exception object.

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
