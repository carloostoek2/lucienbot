"""
Tests de integración para promotion_user_handlers.

Usa SQLite en memoria + PromotionService real + bot mockeado.
Verifica el flujo completo para "Me Interesa": handler -> servicio real -> DB -> respuesta UI 1:1.
"""

from unittest.mock import patch

import pytest

from models.models import PromotionInterest
from services.promotion_service import PromotionService

pytestmark = [pytest.mark.integration]


class TestExpressInterestIntegration:
    """Tests de integración para express_interest (sistema 'Me Interesa')."""

    async def test_express_interest_success_real_flow(
        self, make_callback, make_user, db_session, sample_user, sample_promotion
    ):
        """Handler con PromotionService real -> crea fila en DB -> texto UI 1:1 (Lucien)."""
        real_service = PromotionService(db_session)
        user = make_user(user_id=sample_user.telegram_id)

        with patch("handlers.promotion_user_handlers.PromotionService") as mock_cls:
            mock_cls.return_value = real_service
            with patch(
                "handlers.promotion_user_handlers.notify_admins_about_interest"
            ) as mock_notify:
                cb = make_callback(data=f"offer_interest:{sample_promotion.id}", user=user)

                from handlers.promotion_user_handlers import express_interest
                from keyboards.callback_data import OfferInterestCallback

                await express_interest(
                    cb, OfferInterestCallback(promo_id=sample_promotion.id), cb.bot
                )

                # UI 1:1 (voz de Lucien)
                cb.message.edit_text.assert_called_once()
                text = cb.message.edit_text.call_args[0][0]
                assert "Diana ha sido notificada de su curiosidad" in text
                assert sample_promotion.name in text
                cb.answer.assert_called_once_with("Interes registrado")

                # DB side effect: fila de interés creada por servicio real
                interest = (
                    db_session.query(PromotionInterest)
                    .filter(
                        PromotionInterest.user_id == sample_user.telegram_id,
                        PromotionInterest.promotion_id == sample_promotion.id,
                    )
                    .first()
                )
                assert interest is not None
                mock_notify.assert_called_once()
