"""Tests unitarios para AnonymousMessageService (send_paid_anonymous_message)."""

from unittest.mock import patch

import pytest

from models.models import (
    AnonymousMessage,
    AnonymousMessageStatus,
    BesitoBalance,
    BesitoTransaction,
    TransactionSource,
    TransactionType,
)
from services.anonymous_message_service import ANONYMOUS_MESSAGE_COST, AnonymousMessageService


@pytest.mark.unit
class TestSendPaidAnonymousMessage:
    def test_send_paid_happy_path(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "Hola Diana"
        )

        assert success is True
        assert result == "ok"
        assert message is not None
        assert message.content == "Hola Diana"
        assert message.status == AnonymousMessageStatus.UNREAD

        re_msg = (
            db_session.query(AnonymousMessage)
            .filter_by(sender_id=sample_user.telegram_id)
            .first()
        )
        assert re_msg is not None

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 200 - ANONYMOUS_MESSAGE_COST
        assert re_bal.total_spent == ANONYMOUS_MESSAGE_COST

        txs = (
            db_session.query(BesitoTransaction)
            .filter_by(user_id=sample_user.telegram_id)
            .all()
        )
        assert len(txs) == 1
        tx = txs[0]
        assert tx.source == TransactionSource.ANONYMOUS_MESSAGE
        assert tx.type == TransactionType.DEBIT
        assert tx.amount == -ANONYMOUS_MESSAGE_COST
        assert tx.description == "Envío de mensaje anónimo a Diana"

    def test_send_paid_not_vip(self, db_session, sample_user):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "Hola"
        )

        assert success is False
        assert result == "not_vip"
        assert message is None
        assert db_session.query(AnonymousMessage).count() == 0

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 200
        assert re_bal.total_spent == 0

    def test_send_paid_insufficient_balance(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=10,
            total_earned=10,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "Hola"
        )

        assert success is False
        assert result == "insufficient_balance"
        assert message is None

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 10
        assert re_bal.total_spent == 0
        assert db_session.query(AnonymousMessage).count() == 0

    def test_send_paid_debit_failed_rolls_back(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        saved_tg = sample_user.telegram_id
        service = AnonymousMessageService(db_session)
        with patch(
            "services.anonymous_message_service.BesitoService.debit_besitos",
            return_value=False,
        ):
            success, result, message = service.send_paid_anonymous_message(
                saved_tg, "Hola Diana"
            )

        assert success is False
        assert result == "debit_failed"
        assert message is None
        assert db_session.query(AnonymousMessage).count() == 0

        re_bal = db_session.query(BesitoBalance).filter_by(user_id=saved_tg).first()
        assert re_bal.balance == 200
        assert re_bal.total_spent == 0
        assert db_session.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0

    def test_send_paid_debit_uses_commit_false(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        with patch(
            "services.anonymous_message_service.BesitoService.debit_besitos",
            return_value=True,
        ) as mock_debit:
            service.send_paid_anonymous_message(sample_user.telegram_id, "Hola Diana")

        mock_debit.assert_called_once()
        assert mock_debit.call_args.kwargs.get("commit") is False

    def test_send_paid_invalid_content_too_short(self, db_session, sample_subscription, sample_user):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "ab"
        )
        assert success is False
        assert result == "invalid_content"
        assert message is None
        assert db_session.query(AnonymousMessage).count() == 0

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 200
        assert re_bal.total_spent == 0

    def test_send_paid_invalid_content_too_long(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "x" * 4001
        )
        assert success is False
        assert result == "invalid_content"
        assert message is None
        assert db_session.query(AnonymousMessage).count() == 0

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 200
        assert re_bal.total_spent == 0

    def test_send_paid_invalid_content_whitespace_only(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "   "
        )
        assert success is False
        assert result == "invalid_content"
        assert message is None
        assert db_session.query(AnonymousMessage).count() == 0

        re_bal = (
            db_session.query(BesitoBalance)
            .filter_by(user_id=sample_user.telegram_id)
            .first()
        )
        assert re_bal.balance == 200
        assert re_bal.total_spent == 0

    def test_send_paid_content_strips_whitespace_boundary(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = AnonymousMessageService(db_session)
        success, result, message = service.send_paid_anonymous_message(
            sample_user.telegram_id, "  abc  "
        )
        assert success is True
        assert result == "ok"
        assert message.content == "abc"

        success2, result2, _ = service.send_paid_anonymous_message(
            sample_user.telegram_id, "x" * 4000
        )
        assert success2 is True
        assert result2 == "ok"

    def test_send_paid_internal_error_on_exception(
        self, db_session, sample_subscription, sample_user
    ):
        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=200,
            total_earned=200,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()
        saved_tg = sample_user.telegram_id

        service = AnonymousMessageService(db_session)
        with patch(
            "services.anonymous_message_service.BesitoService.debit_besitos",
            side_effect=RuntimeError("db boom"),
        ):
            success, result, message = service.send_paid_anonymous_message(
                saved_tg, "Hola Diana"
            )

        assert success is False
        assert result == "internal_error"
        assert message is None
        assert db_session.query(AnonymousMessage).filter_by(sender_id=saved_tg).count() == 0
        assert db_session.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0