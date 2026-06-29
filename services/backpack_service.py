"""
BackpackService - Servicio de Mochila (Inventario de Usuario)

Gestiona el inventario personal del usuario: recompensas, compras y membresías VIP.
"""

import logging

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import Order, Package, Reward, StoreProduct, Subscription, UserRewardHistory
from services.besito_service import BesitoService
from services.package_service import PackageService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)


class BackpackService:
    """Servicio para gestionar la mochila del usuario"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def get_user_rewards(self, user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        """
        Obtiene el historial de recompensas del usuario.

        Args:
            user_id: ID del usuario
            limit: Límite de resultados
            offset: Offset para paginación

        Returns:
            Lista de diccionarios con información de recompensas
        """
        db = self._get_db()

        history = (
            db.query(UserRewardHistory)
            .filter(UserRewardHistory.user_id == user_id)
            .order_by(desc(UserRewardHistory.delivered_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        result = []
        for h in history:
            reward = db.query(Reward).filter(Reward.id == h.reward_id).first()
            if not reward:
                continue

            package_name = None
            if reward.package_id:
                pkg = db.query(Package).filter(Package.id == reward.package_id).first()
                package_name = pkg.name if pkg else None

            tariff_name = None
            if reward.tariff_id:
                from models.models import Tariff

                tariff = db.query(Tariff).filter(Tariff.id == reward.tariff_id).first()
                tariff_name = tariff.name if tariff else None

            mission_name = None
            if h.mission_id:
                from models.models import Mission

                mission = db.query(Mission).filter(Mission.id == h.mission_id).first()
                mission_name = mission.name if mission else None

            item = {
                "history_id": h.id,
                "reward_id": reward.id,
                "reward_name": reward.name,
                "reward_type": reward.reward_type.value if reward.reward_type else "BESITOS",
                "besito_amount": reward.besito_amount,
                "package_id": reward.package_id,
                "package_name": package_name,
                "tariff_id": reward.tariff_id,
                "tariff_name": tariff_name,
                "mission_name": mission_name,
                "delivered_at": h.delivered_at,
            }
            result.append(item)

        logger.info(
            f"backpack_service | get_user_rewards | user_id={user_id} | result=success: {len(result)}"
        )
        return result

    def get_user_purchases(self, user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        """
        Obtiene las compras completadas del usuario.

        Args:
            user_id: ID del usuario
            limit: Límite de resultados
            offset: Offset para paginación

        Returns:
            Lista de diccionarios con información de compras
        """
        db = self._get_db()

        from models.models import OrderStatus

        orders = (
            db.query(Order)
            .filter(Order.user_id == user_id, Order.status == OrderStatus.COMPLETED)
            .order_by(desc(Order.completed_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        result = []
        for order in orders:
            for item in order.items:
                product = db.query(StoreProduct).filter(StoreProduct.id == item.product_id).first()
                if not product:
                    continue

                package_name = None
                if product.package_id:
                    pkg = db.query(Package).filter(Package.id == product.package_id).first()
                    package_name = pkg.name if pkg else None

                entry = {
                    "order_id": order.id,
                    "order_item_id": item.id,
                    "product_id": product.id,
                    "product_name": item.product_name,
                    "package_id": product.package_id,
                    "package_name": package_name,
                    "quantity": item.quantity,
                    "total_price": item.total_price,
                    "purchased_at": order.completed_at,
                }
                entry.update(self._enrich_purchase_fulfillment(item.id))
                result.append(entry)

        logger.info(
            f"backpack_service | get_user_purchases | user_id={user_id} | result=success: {len(result)}"
        )
        return result

    def _enrich_purchase_fulfillment(self, order_item_id: int) -> dict:
        from services.fulfillment_service import FulfillmentService

        return FulfillmentService(self._get_db()).build_purchase_enrichment(order_item_id)

    def get_fulfillment_detail(self, user_id: int, fulfillment_id: int) -> dict | None:
        from models.models import OrderFulfillment

        row = (
            self._get_db()
            .query(OrderFulfillment)
            .filter(
                OrderFulfillment.id == fulfillment_id,
                OrderFulfillment.user_id == user_id,
            )
            .first()
        )
        if not row:
            return None
        base = self._enrich_purchase_fulfillment(row.order_item_id)
        base["product_name"] = row.product.name if row.product else ""
        return base

    async def retry_fulfillment_delivery(
        self, bot, user_id: int, fulfillment_id: int
    ) -> tuple[bool, str]:
        from services.fulfillment_service import FulfillmentService

        return await FulfillmentService(self._get_db()).retry_fulfillment_delivery(
            bot, user_id, fulfillment_id
        )

    def get_fulfillment_input_prompt(
        self, user_id: int, fulfillment_id: int
    ) -> tuple[bool, str]:
        from services.fulfillment_service import FulfillmentService

        return FulfillmentService(self._get_db()).get_user_input_prompt_message(
            user_id, fulfillment_id
        )

    async def submit_fulfillment_input(
        self, bot, user_id: int, fulfillment_id: int, text: str
    ) -> tuple[bool, str]:
        from services.fulfillment_service import FulfillmentService

        return await FulfillmentService(self._get_db()).submit_user_input(
            bot, fulfillment_id, user_id, text
        )

    async def resend_vip_invite_for_fulfillment(
        self, bot, user_id: int, fulfillment_id: int
    ) -> tuple[bool, str]:
        from services.fulfillment_service import FulfillmentService

        return await FulfillmentService(self._get_db()).resend_vip_invite_for_fulfillment(
            bot, user_id, fulfillment_id
        )

    def get_vip_subscriptions_for_backpack(self, user_id: int) -> list[dict]:
        """Thin delegate: suscripciones VIP para vista mochila."""
        return self.get_user_vip_subscriptions(user_id)

    def get_user_vip_subscriptions(self, user_id: int) -> list[dict]:
        """
        Obtiene las suscripciones VIP activas del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de diccionarios con información de suscripciones VIP
        """
        db = self._get_db()

        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.is_active)
            .all()
        )

        result = []
        for sub in subscriptions:
            from models.models import Tariff

            # Prefer direct tariff_id (new convention for internal grants); fallback to token for legacy/manual
            tariff_id = sub.tariff_id or (sub.token.tariff_id if sub.token else None)
            tariff_obj = (
                db.query(Tariff).filter(Tariff.id == tariff_id).first()
                if tariff_id
                else None
            )

            result.append(
                {
                    "subscription_id": sub.id,
                    "tariff_name": tariff_obj.name if tariff_obj else "Desconocida",
                    "start_date": sub.start_date,
                    "end_date": sub.end_date,
                    "is_active": sub.is_active,
                }
            )

        logger.info(
            f"backpack_service | get_user_vip_subscriptions | user_id={user_id} | result=success: {len(result)}"
        )
        return result

    def get_backpack_summary(self, user_id: int) -> dict:
        """
        Obtiene el resumen global de la mochila del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con conteos de recompensas, compras, VIP y balance de besitos
        """
        db = self._get_db()

        # Count rewards
        rewards_count = (
            db.query(UserRewardHistory).filter(UserRewardHistory.user_id == user_id).count()
        )

        # Count purchases
        from models.models import OrderStatus

        purchases_count = (
            db.query(Order)
            .filter(Order.user_id == user_id, Order.status == OrderStatus.COMPLETED)
            .count()
        )

        # Count VIP subscriptions
        vip_count = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.is_active)
            .count()
        )

        # Get besitos balance
        besito_service = BesitoService(db)
        besitos_balance = besito_service.get_balance(user_id)

        logger.info(f"backpack_service | get_backpack_summary | user_id={user_id} | result=success")
        return {
            "rewards_count": rewards_count,
            "purchases_count": purchases_count,
            "vip_count": vip_count,
            "besitos_balance": besitos_balance,
        }

    def user_has_package_entitlement(self, user_id: int, package_id: int) -> bool:
        """True si el usuario tiene derecho al paquete (recompensa o compra fulfilled)."""
        for reward in self.get_user_rewards(user_id, limit=200):
            if reward.get("package_id") == package_id:
                return True
        package_kinds = {"package", "package_deferred"}
        for purchase in self.get_user_purchases(user_id, limit=200):
            if purchase.get("fulfillment_status") != "fulfilled":
                continue
            if purchase.get("fulfillment_kind") not in package_kinds:
                continue
            pid = purchase.get("package_id") or (purchase.get("auto_result") or {}).get(
                "package_id"
            )
            if pid == package_id:
                return True
        return False

    async def deliver_package_content(self, bot, user_id: int, package_id: int) -> tuple[bool, str]:
        """
        Envía el contenido de un paquete al usuario.

        Args:
            bot: Instancia del bot
            user_id: ID del usuario
            package_id: ID del paquete

        Returns:
            Tuple (éxito, mensaje)
        """
        if not self.user_has_package_entitlement(user_id, package_id):
            logger.warning(
                f"backpack_service | deliver_package_content | user_id={user_id} | "
                f"package_id={package_id} | result=unauthorized"
            )
            return False, LucienVoice.package_not_found()
        package_service = PackageService(self.db)
        package = package_service.get_package(package_id)

        if not package:
            logger.warning(
                f"backpack_service | deliver_package_content | user_id={user_id} | package_id={package_id} | result=not_found"
            )
            return False, LucienVoice.package_not_found()

        success, message = await package_service.deliver_package_to_user(
            bot=bot,
            user_id=user_id,
            package_id=package_id,
            delivery_source="backpack",
        )

        logger.info(
            f"backpack_service | deliver_package_content | user_id={user_id} | package_id={package_id} | result={success}"
        )
        return success, message
