"""
Tests de integración para gamification_user_handlers.

Usa SQLite en memoria + servicios reales + bot/eventos mockeados.
Verifica el flujo completo: handler -> servicio real -> DB -> respuesta.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from models.models import (
    BesitoTransaction, BesitoBalance, DailyGiftConfig, DailyGiftClaim,
    TransactionType, TransactionSource
)
from services.besito_service import BesitoService
from services.daily_gift_service import DailyGiftService

pytestmark = [pytest.mark.integration]


class TestShowBalanceIntegration:
    """Tests de integración para show_balance."""

    async def test_shows_balance_from_db(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Usa BesitoService real y verifica que el balance de DB se muestra."""
        tg_id = sample_user.telegram_id
        balance = BesitoBalance(
            user_id=tg_id, balance=1000,
            total_earned=1500, total_spent=500
        )
        db_session.add(balance)
        db_session.commit()

        real_service = BesitoService(db_session)
        user = make_user(user_id=tg_id)

        with patch("handlers.gamification_user_handlers.BesitoService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="my_balance", user=user)

            from handlers.gamification_user_handlers import show_balance
            await show_balance(cb)

            cb.message.edit_text.assert_called_once()
            text = cb.message.edit_text.call_args[0][0]
            assert "1000" in text

    async def test_shows_zero_when_no_balance(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Usuario sin balance registrado muestra 0."""
        real_service = BesitoService(db_session)
        user = make_user(user_id=sample_user.telegram_id)

        with patch("handlers.gamification_user_handlers.BesitoService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="my_balance", user=user)

            from handlers.gamification_user_handlers import show_balance
            await show_balance(cb)

            cb.message.edit_text.assert_called_once()
            text = cb.message.edit_text.call_args[0][0]
            assert "0" in text


class TestTransactionHistoryIntegration:
    """Tests de integración para show_transaction_history."""

    async def test_shows_transactions_from_db(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Crea transacciones en DB y verifica que aparecen."""
        tg_id = sample_user.telegram_id
        balance = BesitoBalance(
            user_id=tg_id, balance=100,
            total_earned=100, total_spent=0
        )
        db_session.add(balance)
        db_session.flush()

        tx = BesitoTransaction(
            user_id=tg_id,
            amount=50,
            type=TransactionType.CREDIT,
            source=TransactionSource.DAILY_GIFT,
        )
        db_session.add(tx)
        db_session.commit()

        real_service = BesitoService(db_session)
        user = make_user(user_id=tg_id)

        with patch("handlers.gamification_user_handlers.BesitoService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="transaction_history", user=user)

            from handlers.gamification_user_handlers import show_transaction_history
            await show_transaction_history(cb)

            cb.message.edit_text.assert_called_once()
            text = cb.message.edit_text.call_args[0][0]
            assert "+50" in text

    async def test_empty_history_message(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Usuario sin transacciones ve mensaje de vacio."""
        real_service = BesitoService(db_session)
        user = make_user(user_id=sample_user.telegram_id)

        with patch("handlers.gamification_user_handlers.BesitoService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="transaction_history", user=user)

            from handlers.gamification_user_handlers import show_transaction_history
            await show_transaction_history(cb)

            cb.message.edit_text.assert_called_once()
            text = cb.message.edit_text.call_args[0][0]
            assert "vacio" in text.lower() or "vacío" in text.lower()


class TestDailyGiftIntegration:
    """Tests de integracion para daily_gift_menu y claim_daily_gift."""

    async def test_claim_gift_persists_in_db(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Reclamar regalo persiste en DB y no se puede reclamar dos veces."""
        tg_id = sample_user.telegram_id
        config = DailyGiftConfig(besito_amount=10, is_active=True)
        db_session.add(config)
        db_session.commit()

        real_service = DailyGiftService(db_session)
        user = make_user(user_id=tg_id)

        with patch("handlers.gamification_user_handlers.DailyGiftService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="claim_gift", user=user)

            from handlers.gamification_user_handlers import claim_daily_gift
            await claim_daily_gift(cb)

            cb.message.edit_text.assert_called_once()

            # Verificar que la DB tiene el claim (user_id = telegram_id)
            claims = db_session.query(DailyGiftClaim).filter(
                DailyGiftClaim.user_id == tg_id
            ).all()
            assert len(claims) == 1

            # Segundo reclamo debe fallar
            cb2 = make_callback(data="claim_gift", user=user)
            await claim_daily_gift(cb2)

            cb2.message.edit_text.assert_called_once()
            text2 = cb2.message.edit_text.call_args[0][0]
            assert "ocurrio" in text2.lower() or "ocurrió" in text2.lower() or "esperar" in text2.lower()

    async def test_daily_gift_menu_shows_status(
        self, make_callback, make_user, db_session, sample_user
    ):
        """Menu de regalo diario muestra estado correcto basado en DB."""
        config = DailyGiftConfig(besito_amount=10, is_active=True)
        db_session.add(config)
        db_session.commit()

        real_service = DailyGiftService(db_session)
        user = make_user(user_id=sample_user.telegram_id)

        with patch("handlers.gamification_user_handlers.DailyGiftService") as mock:
            mock.return_value = real_service
            cb = make_callback(data="daily_gift", user=user)

            from handlers.gamification_user_handlers import daily_gift_menu
            await daily_gift_menu(cb)

            cb.message.edit_text.assert_called_once()
