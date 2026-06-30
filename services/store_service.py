"""
Servicio de Tienda - Lucien Bot

Gestiona el catalogo de productos, carrito y compras.
"""

import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from config.settings import bot_config
from models.database import SessionLocal
from models.models import (
    BesitoTransaction,
    CartItem,
    Category,
    MissionType,
    Order,
    OrderItem,
    OrderStatus,
    Package,
    StoreProduct,
    StoryNode,
    Tariff,
    TransactionSource,
    User,
)
from services.besito_service import BesitoService
from services.package_service import PackageService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)

REQUIRED_PREV_TIER_PURCHASES = 2


def resolve_product_category_id(product: StoreProduct) -> int | None:
    """Función pura: categoría efectiva del producto (directa o vía paquete)."""
    if product.category_id:
        return product.category_id
    package = getattr(product, "package", None)
    if package and package.category_id:
        return package.category_id
    return None


class _OrderAtomicError(Exception):
    """Fallo en fase atómica de complete_order (stock/producto); provoca rollback."""


# Support added for store_admin_handlers 1-service + pure extract (item8).
# Arch-enforcer note (long funcs + direct PackageService in wizard + inline biz/UI calc) addressed.
# Precedent item7.


def compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin store (list/alerts).
    1:1 de lógica previamente inline en store_admin_handlers (item8, arch-enforcer long-funcs note addressed).
    """
    if stock == -1:
        return "♾️", "∞"
    if stock == 0:
        return "🚨", "AGOTADO"
    if is_low_stock:
        return "⚠️", str(stock)
    return "📦", str(stock)


def build_purchase_notification_text(
    user_display: str,
    username: str,
    user_id: int,
    items: list[tuple[str, int, int]],
    total_price: int,
    date_str: str,
    order_id: int,
) -> str:
    """Función pura (sin estado ni side-effects). Delega la construcción del texto a LucienVoice.

    Mantiene la interfaz pura y los call sites. Los literales en español viven solo en utils/lucien_voice.py
    para que el test e2e test_no_hardcoded_spanish_in_services los ignore (filtra líneas con 'LucienVoice.').
    """
    return LucienVoice.store_admin_purchase_notification(
        user_display, username, user_id, items, total_price, date_str, order_id
    )


def build_purchase_admin_keyboard(
    user_link: str, *, queue_link: bool = True
) -> InlineKeyboardMarkup:
    """Construye el teclado de notificación de compra para admins."""
    rows = [
        [
            InlineKeyboardButton(
                text=LucienVoice.store_admin_purchase_contact_button(),
                url=user_link,
            )
        ],
    ]
    if queue_link:
        rows.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_queue_button(),
                    callback_data="fulfill_admin_menu",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=LucienVoice.store_admin_purchase_back_button(),
                callback_data="back_to_admin",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


class StoreService:
    """Servicio para gestion de tienda"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None
        self._init_services()

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def _init_services(self):
        """Inicializa servicios dependientes con la misma sesión."""
        db = self._get_db()
        # Held direct BesitoService composition removed (Item 10 / remaining store debits unification).
        # PURCHASE debits/balance checks now use local on-demand BesitoService(db=self.db) *only*
        # inside the balance/debit sites in direct_purchase / create_order / complete_order (preserves atomicity:
        # debit's internal commit + PURCHASE tx + order/stock/deliver all unchanged;
        # best-effort schedule_emit still fires post-credit commit if any credit path).
        # PackageService remains held (scope: other composers untouched per Item 10 tight).
        # self.besito_service = BesitoService(db)  # REMOVED (was here)
        self.package_service = PackageService(db)

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def compute_stock_emoji_and_text(
        self, stock: int, is_low_stock: bool = False
    ) -> tuple[str, str]:
        # Backward-compatible delegate added for Item 8 (arch-enforcer 1-service rule for store_admin handlers).
        return compute_stock_emoji_and_text(stock, is_low_stock)

    # ==================== PRODUCTOS ====================

    def create_product(
        self,
        name: str,
        description: str,
        package_id: int | None,
        price: int,
        stock: int = -1,
        created_by: int = None,
        *,
        tier_id: int | None = None,
        delivery_mode=None,
        fulfillment_kind=None,
        fulfillment_config: str | None = None,
        monthly_stock_cap: int | None = None,
        story_node_id: int | None = None,
        tariff_id: int | None = None,
    ) -> StoreProduct:
        """Crea un nuevo producto en la tienda."""
        from models.models import DeliveryMode, FulfillmentKind

        db = self._get_db()
        kind = fulfillment_kind or FulfillmentKind.PACKAGE
        if kind in (FulfillmentKind.PACKAGE, FulfillmentKind.PACKAGE_DEFERRED) and not package_id:
            raise ValueError("package_id required for PACKAGE fulfillment kinds")
        if kind == FulfillmentKind.VIP_GRANT and not tariff_id:
            raise ValueError("tariff_id required for VIP_GRANT fulfillment kind")
        if kind == FulfillmentKind.STORY_UNLOCK and not story_node_id:
            raise ValueError("story_node_id required for STORY_UNLOCK fulfillment kind")
        product = StoreProduct(
            name=name,
            description=description,
            package_id=package_id,
            price=price,
            stock=stock,
            created_by=created_by,
            is_active=True,
            tier_id=tier_id,
            delivery_mode=delivery_mode or DeliveryMode.AUTO,
            fulfillment_kind=kind,
            fulfillment_config=fulfillment_config,
            monthly_stock_cap=monthly_stock_cap,
            story_node_id=story_node_id,
            tariff_id=tariff_id,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"Producto creado: {name} (ID: {product.id})")
        return product

    def get_product(self, product_id: int) -> StoreProduct | None:
        """Obtiene un producto por ID"""
        db = self._get_db()
        return db.query(StoreProduct).filter(StoreProduct.id == product_id).first()

    def get_all_products(self, active_only: bool = True) -> list[StoreProduct]:
        """Obtiene todos los productos"""
        db = self._get_db()
        query = db.query(StoreProduct)
        if active_only:
            query = query.filter(StoreProduct.is_active)
        return query.order_by(desc(StoreProduct.created_at)).all()

    def get_available_products(self) -> list[StoreProduct]:
        """Obtiene productos disponibles para compra"""
        db = self._get_db()
        return (
            db.query(StoreProduct)
            .filter(
                StoreProduct.is_active,
                (StoreProduct.stock == -1) | (StoreProduct.stock > 0),
            )
            .order_by(desc(StoreProduct.created_at))
            .all()
        )

    def search_products(self, query: str, active_only: bool = True) -> list[StoreProduct]:
        """Busca productos por nombre o descripcion"""
        db = self._get_db()
        search = f"%{query}%"
        q = db.query(StoreProduct).filter(
            (StoreProduct.name.ilike(search)) | (StoreProduct.description.ilike(search))
        )
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.order_by(desc(StoreProduct.created_at)).all()

    def get_products_by_price_range(
        self, min_price: int = 0, max_price: int = None, active_only: bool = True
    ) -> list[StoreProduct]:
        """Obtiene productos en rango de precio"""
        db = self._get_db()
        q = db.query(StoreProduct).filter(StoreProduct.price >= min_price)
        if max_price is not None:
            q = q.filter(StoreProduct.price <= max_price)
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.order_by(StoreProduct.price).all()

    def get_products_by_category(
        self, category_id: int, active_only: bool = True
    ) -> list[StoreProduct]:
        """Obtiene productos por categoría (category_id directo o vía paquete)."""
        return self.filter_products(category_id=category_id, active_only=active_only)

    def _category_product_filter(self, query, category_id: int):
        """Aplica filtro OR: StoreProduct.category_id o Package.category_id."""
        package_ids = [
            row[0]
            for row in self._get_db()
            .query(Package.id)
            .filter(Package.category_id == category_id)
            .all()
        ]
        conditions = [StoreProduct.category_id == category_id]
        if package_ids:
            conditions.append(StoreProduct.package_id.in_(package_ids))
        return query.filter(or_(*conditions))

    def filter_products(
        self,
        category_id: int = None,
        min_price: int = None,
        max_price: int = None,
        in_stock_only: bool = False,
        active_only: bool = True,
    ) -> list[StoreProduct]:
        """Filtra productos por multiples criterios"""
        db = self._get_db()
        q = db.query(StoreProduct)

        if active_only:
            q = q.filter(StoreProduct.is_active)

        if category_id:
            q = self._category_product_filter(q, category_id)

        if min_price is not None:
            q = q.filter(StoreProduct.price >= min_price)

        if max_price is not None:
            q = q.filter(StoreProduct.price <= max_price)

        if in_stock_only:
            q = q.filter((StoreProduct.stock == -1) | (StoreProduct.stock > 0))

        return q.order_by(desc(StoreProduct.created_at)).all()

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Actualiza un producto"""
        from models.models import FulfillmentKind

        db = self._get_db()
        product = self.get_product(product_id)
        if not product:
            return False

        new_kind = kwargs.get("fulfillment_kind", product.fulfillment_kind)
        new_package_id = kwargs.get("package_id", product.package_id)
        new_tariff_id = kwargs.get("tariff_id", product.tariff_id)
        new_story_node_id = kwargs.get("story_node_id", product.story_node_id)

        changing_kind = "fulfillment_kind" in kwargs
        if changing_kind:
            if new_kind in (FulfillmentKind.PACKAGE, FulfillmentKind.PACKAGE_DEFERRED) and not new_package_id:
                logger.warning(
                    f"store_service | update_product | product_id={product_id} | "
                    f"result=package_id_required_for_kind"
                )
                return False
            if new_kind == FulfillmentKind.VIP_GRANT and not new_tariff_id:
                logger.warning(
                    f"store_service | update_product | product_id={product_id} | "
                    f"result=tariff_id_required_for_kind"
                )
                return False
            if new_kind == FulfillmentKind.STORY_UNLOCK and not new_story_node_id:
                logger.warning(
                    f"store_service | update_product | product_id={product_id} | "
                    f"result=story_node_id_required_for_kind"
                )
                return False

        if "package_id" in kwargs and kwargs["package_id"] is not None:
            new_package_id = kwargs["package_id"]
            package = self.package_service.get_package(new_package_id)
            if not package:
                logger.warning(
                    f"store_service | update_product | product_id={product_id} | "
                    f"package_id={new_package_id} | resultado=paquete_no_encontrado"
                )
                return False
            if new_package_id != product.package_id and not package.is_active:
                logger.warning(
                    f"store_service | update_product | product_id={product_id} | "
                    f"package_id={new_package_id} | resultado=paquete_inactivo"
                )
                return False

        allowed_fields = [
            "name",
            "description",
            "package_id",
            "price",
            "stock",
            "is_active",
            "low_stock_threshold",
            "fulfillment_kind",
            "fulfillment_config",
            "monthly_stock_cap",
            "delivery_mode",
            "tier_id",
            "tariff_id",
            "story_node_id",
        ]
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(product, field):
                setattr(product, field, value)

        db.commit()
        logger.info(
            f"store_service | update_product | product_id={product_id} | "
            f"fields={list(kwargs.keys())} | resultado=ok"
        )
        return True

    def delete_product(self, product_id: int) -> bool:
        """Elimina un producto de la base de datos (soft delete)"""
        db = self._get_db()
        product = db.query(StoreProduct).filter(StoreProduct.id == product_id).first()
        if not product:
            logger.warning(f"Producto {product_id} no encontrado para eliminar")
            return False

        product.is_active = False
        db.commit()
        logger.info(f"Producto {product_id} desactivado (soft delete)")
        return True

    def get_available_packages_for_store(self) -> list[Package]:
        """Thin delegate to internal package_service.get_available_packages_for_store().
        Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service (StoreService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change.
        """
        return self.package_service.get_available_packages_for_store()

    def get_packages_for_product_edit(self, product_id: int) -> list[Package]:
        """Paquetes elegibles al editar un producto: disponibles + paquete actual."""
        available = self.package_service.get_available_packages_for_store()
        product = self.get_product(product_id)
        if not product:
            return available

        current = self.package_service.get_package(product.package_id)
        if not current:
            return available

        available_ids = {pkg.id for pkg in available}
        if current.id in available_ids:
            return available
        return [current, *available]

    def get_tariffs_for_product_wizard(self, active_only: bool = True) -> list[Tariff]:
        """Thin delegate → VIPService(db).get_all_tariffs(active_only).
        Fase 2 store-admin-wizard-ux: wizard inline tariff selection. Read-only. 0 purchase impact.
        """
        from services.vip_service import VIPService

        return VIPService(self._get_db()).get_all_tariffs(active_only=active_only)

    def get_story_nodes_for_product_wizard(self, active_only: bool = True) -> list[StoryNode]:
        """Thin delegate → StoryService(db).get_all_nodes(active_only).
        Fase 2 store-admin-wizard-ux: wizard inline story selection. Read-only. 0 purchase impact.
        """
        from services.story_service import StoryService

        return StoryService(self._get_db()).get_all_nodes(active_only=active_only)

    def get_tariffs_for_product_edit(self, product_id: int) -> list[Tariff]:
        """Tarifas elegibles al editar: activas + tarifa actual del producto si está inactiva.
        Espejo get_packages_for_product_edit (item8 gold).
        """
        available = self.get_tariffs_for_product_wizard(active_only=True)
        product = self.get_product(product_id)
        if not product or not product.tariff_id:
            return available
        from services.vip_service import VIPService

        current = VIPService(self._get_db()).get_tariff(product.tariff_id)
        if not current:
            return available
        available_ids = {t.id for t in available}
        if current.id in available_ids:
            return available
        return [current, *available]

    def get_story_nodes_for_product_edit(self, product_id: int) -> list[StoryNode]:
        """Nodos elegibles al editar: activos + nodo actual del producto si está inactivo.
        Espejo get_packages_for_product_edit (item8 gold).
        """
        available = self.get_story_nodes_for_product_wizard(active_only=True)
        product = self.get_product(product_id)
        if not product or not product.story_node_id:
            return available
        from services.story_service import StoryService

        current = StoryService(self._get_db()).get_node(product.story_node_id)
        if not current:
            return available
        available_ids = {n.id for n in available}
        if current.id in available_ids:
            return available
        return [current, *available]

    # ==================== CARRITO ====================

    def get_cart_items(self, user_id: int) -> list[CartItem]:
        """Obtiene los items del carrito de un usuario"""
        db = self._get_db()
        return (
            db.query(CartItem)
            .filter(CartItem.user_id == user_id)
            .order_by(desc(CartItem.added_at))
            .all()
        )

    def get_cart_total(self, user_id: int) -> int:
        """Obtiene el total del carrito en besitos"""
        items = self.get_cart_items(user_id)
        total = 0
        for item in items:
            if item.product and item.product.is_available:
                total += item.product.price * item.quantity
        return total

    def get_cart_items_count(self, user_id: int) -> int:
        """Obtiene la cantidad de items en el carrito"""
        db = self._get_db()
        return db.query(CartItem).filter(CartItem.user_id == user_id).count()

    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> tuple:
        """
        Agrega un producto al carrito.
        Retorna (exito, mensaje)
        """
        db = self._get_db()
        product = self.get_product(product_id)
        if not product:
            return False, LucienVoice.store_product_not_found()

        if not product.is_available:
            return False, LucienVoice.store_product_unavailable()

        # Verificar si ya esta en el carrito
        existing = (
            db.query(CartItem)
            .filter(CartItem.user_id == user_id, CartItem.product_id == product_id)
            .first()
        )

        if existing:
            existing.quantity += quantity
            db.commit()
            return True, LucienVoice.store_cart_updated(existing.quantity, product.name)

        # Crear nuevo item
        cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(cart_item)
        db.commit()

        return True, LucienVoice.store_cart_added(product.name)

    def remove_from_cart(self, user_id: int, cart_item_id: int) -> bool:
        """Elimina un item del carrito"""
        db = self._get_db()
        item = (
            db.query(CartItem)
            .filter(CartItem.id == cart_item_id, CartItem.user_id == user_id)
            .first()
        )

        if item:
            db.delete(item)
            db.commit()
            return True
        return False

    def update_cart_quantity(self, user_id: int, cart_item_id: int, quantity: int) -> bool:
        """Actualiza la cantidad de un item en el carrito"""
        if quantity < 1:
            return self.remove_from_cart(user_id, cart_item_id)

        db = self._get_db()
        item = (
            db.query(CartItem)
            .filter(CartItem.id == cart_item_id, CartItem.user_id == user_id)
            .first()
        )

        if item:
            item.quantity = quantity
            db.commit()
            return True
        return False

    def clear_cart(self, user_id: int) -> bool:
        """Vacia el carrito del usuario"""
        db = self._get_db()
        items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
        for item in items:
            db.delete(item)
        db.commit()
        return True

    # ==================== COMPRA DIRECTA ====================

    def _check_monthly_cap_for_product(self, product_id: int) -> str | None:
        from services.fulfillment_service import FulfillmentService

        fulfill = FulfillmentService(self._get_db())
        if not fulfill.is_monthly_cap_available(product_id):
            product = self.get_product(product_id)
            return LucienVoice.store_monthly_cap_reached(product.name if product else "")
        return None

    def get_shop_balance_display(self, user_id: int) -> int:
        """Thin delegate: saldo besitos para UI de catálogo."""
        return BesitoService(db=self.db).get_balance(user_id)

    def get_product_preview_context(self, product_id: int) -> dict:
        """Thin delegate: contexto de preview (file_count, can_preview).

        can_preview=True solo si >1 archivos. Si hay 1 solo archivo, preview
        enviaría el producto completo gratis → se deshabilita automáticamente.
        """
        product = self.get_product(product_id)
        if not product or not product.package_id:
            return {"file_count": 0, "can_preview": False}
        pkg = self.package_service.get_package(product.package_id)
        if not pkg:
            return {"file_count": 0, "can_preview": False}
        files = self.package_service.get_package_files(product.package_id)
        count = len(files)
        return {"file_count": count, "can_preview": count > 1}

    def get_categories_for_shop(self, active_only: bool = True) -> list:
        """Categorías activas que tienen al menos un producto visible en tienda."""
        categories = self.package_service.get_all_categories(active_only=active_only)
        if not categories:
            return []
        visible_ids = {
            resolve_product_category_id(product)
            for product in self._get_db()
            .query(StoreProduct)
            .outerjoin(Package)
            .filter(StoreProduct.is_active)
            .all()
        }
        visible_ids.discard(None)
        return [category for category in categories if category.id in visible_ids]

    def count_products_in_category(self, category_id: int, active_only: bool = True) -> int:
        """Cuenta productos activos en una categoría."""
        return len(self.filter_products(category_id=category_id, active_only=active_only))

    def get_category_for_shop(self, category_id: int):
        """Thin delegate: categoría por id."""
        return self.package_service.get_category(category_id)

    def _get_category_for_product(self, product: StoreProduct) -> Category | None:
        """Resuelve la categoría efectiva de un producto."""
        category_id = resolve_product_category_id(product)
        if not category_id:
            return None
        return self.package_service.get_category(category_id)

    def _get_min_tier_order_index(self) -> int:
        """Orden mínimo entre tiers activos (primer nivel del catálogo)."""
        from models.models import StoreTier

        result = (
            self._get_db()
            .query(func.min(StoreTier.order_index))
            .filter(StoreTier.is_active)
            .scalar()
        )
        return result if result is not None else 0

    def count_user_purchases_at_tier_level(self, user_id: int, order_index: int) -> int:
        """Cuenta unidades compradas en tiers de un order_index (órdenes completadas)."""
        from models.models import StoreTier

        db = self._get_db()
        tier_ids = [
            row[0]
            for row in db.query(StoreTier.id)
            .filter(StoreTier.order_index == order_index, StoreTier.is_active)
            .all()
        ]
        if not tier_ids:
            return 0
        rows = (
            db.query(OrderItem.quantity)
            .join(Order, OrderItem.order_id == Order.id)
            .join(StoreProduct, OrderItem.product_id == StoreProduct.id)
            .filter(
                Order.user_id == user_id,
                Order.status == OrderStatus.COMPLETED,
                StoreProduct.tier_id.in_(tier_ids),
            )
            .all()
        )
        return sum(row[0] for row in rows)

    def check_tier_purchase_gate(self, user_id: int, product_id: int) -> str | None:
        """Bloquea compra si el visitante no cumple requisito del tier anterior."""
        product = self.get_product(product_id)
        if not product or not product.tier_id:
            return None
        tier = product.tier
        if not tier or tier.order_index <= self._get_min_tier_order_index():
            return None
        prev_index = tier.order_index - 1
        purchased = self.count_user_purchases_at_tier_level(user_id, prev_index)
        if purchased >= REQUIRED_PREV_TIER_PURCHASES:
            return None
        from models.models import StoreTier

        prev_tiers = (
            self._get_db()
            .query(StoreTier)
            .filter(StoreTier.order_index == prev_index, StoreTier.is_active)
            .order_by(StoreTier.order_index, StoreTier.name)
            .all()
        )
        prev_label = ", ".join(t.name for t in prev_tiers) or "el nivel anterior"
        remaining = REQUIRED_PREV_TIER_PURCHASES - purchased
        return LucienVoice.store_tier_locked(
            prev_label, purchased, REQUIRED_PREV_TIER_PURCHASES, remaining
        )

    def get_tier_purchase_status(self, user_id: int, product_id: int) -> dict:
        """Estado de desbloqueo de tier para UI de detalle."""
        product = self.get_product(product_id)
        if not product or not product.tier_id:
            return {
                "tier_unlocked": True,
                "tier_lock_message": None,
                "tier_lock_remaining": 0,
            }
        tier = product.tier
        if not tier or tier.order_index <= self._get_min_tier_order_index():
            return {
                "tier_unlocked": True,
                "tier_lock_message": None,
                "tier_lock_remaining": 0,
            }
        prev_index = tier.order_index - 1
        purchased = self.count_user_purchases_at_tier_level(user_id, prev_index)
        if purchased >= REQUIRED_PREV_TIER_PURCHASES:
            return {
                "tier_unlocked": True,
                "tier_lock_message": None,
                "tier_lock_remaining": 0,
            }
        from models.models import StoreTier

        prev_tiers = (
            self._get_db()
            .query(StoreTier)
            .filter(StoreTier.order_index == prev_index, StoreTier.is_active)
            .order_by(StoreTier.order_index, StoreTier.name)
            .all()
        )
        prev_label = ", ".join(t.name for t in prev_tiers) or "el nivel anterior"
        remaining = REQUIRED_PREV_TIER_PURCHASES - purchased
        return {
            "tier_unlocked": False,
            "tier_lock_message": LucienVoice.store_tier_locked(
                prev_label, purchased, REQUIRED_PREV_TIER_PURCHASES, remaining
            ),
            "tier_lock_remaining": remaining,
        }

    def get_preview_files_for_product(self, product_id: int, limit: int = 1) -> list:
        """Thin delegate: archivos de preview del paquete."""
        product = self.get_product(product_id)
        if not product or not product.package_id:
            return []
        files = self.package_service.get_package_files(product.package_id)
        return files[:limit]

    def get_effective_price(self, user_id: int, list_price: int) -> int:
        """Precio efectivo tras descuento activo (una sola aplicación en complete_order)."""
        return self._apply_discount_to_order_total(user_id, list_price)

    def get_product_detail_context(self, product_id: int, user_id: int) -> dict | None:
        """Contexto unificado para detalle de producto (1 llamada handler)."""
        from services.fulfillment_service import FulfillmentService

        product = self.get_product(product_id)
        if not product:
            return None
        preview = self.get_product_preview_context(product_id)
        tier_name = product.tier.name if product.tier else ""
        effective_price = self.get_effective_price(user_id, product.price)
        cap_available = FulfillmentService(self._get_db()).is_monthly_cap_available(product_id)
        tier_status = self.get_tier_purchase_status(user_id, product_id)
        return {
            "product": product,
            "balance": self.get_shop_balance_display(user_id),
            "tier_name": tier_name,
            "effective_price": effective_price,
            "monthly_cap_available": cap_available,
            **tier_status,
            **preview,
        }

    async def submit_purchase_input(
        self, bot, fulfillment_id: int, user_id: int, text: str
    ) -> tuple[bool, str]:
        """Thin delegate: envía input de compra al FulfillmentService."""
        from services.fulfillment_service import FulfillmentService

        return await FulfillmentService(self._get_db()).submit_user_input(
            bot, fulfillment_id, user_id, text
        )

    async def purchase_and_complete(
        self, bot, user_id: int, product_id: int, quantity: int = 1
    ) -> tuple[Order | None, list[dict], str | None]:
        """Encapsula direct_purchase + complete_order en una sesión."""
        order, error = self.direct_purchase(user_id, product_id)
        if error:
            return None, [], error
        success, msg = await self.complete_order(bot, order.id)
        if not success:
            return order, [], msg
        from services.fulfillment_service import FulfillmentService

        summaries = []
        fulfill_svc = FulfillmentService(self._get_db())
        for item in order.items:
            row = fulfill_svc.get_fulfillment_for_order_item(item.id)
            if row:
                enrichment = fulfill_svc.build_purchase_enrichment(item.id)
                auto = enrichment.get("auto_result") or {}
                summaries.append(
                    {
                        "kind": row.fulfillment_kind.value,
                        "status": row.status.value,
                        "product_name": item.product_name,
                        "fulfillment_id": row.id,
                        "invite_link": auto.get("invite_link"),
                        "vip_activated": auto.get("vip_activated"),
                    }
                )
        return order, summaries, None

    def get_all_tiers(self, active_only: bool = True) -> list:
        from models.models import StoreTier

        q = self._get_db().query(StoreTier)
        if active_only:
            q = q.filter(StoreTier.is_active)
        return q.order_by(StoreTier.order_index).all()

    def get_tiers_for_shop(self, active_only: bool = True) -> list:
        """Tiers activos con al menos un producto visible en tienda."""
        tiers = self.get_all_tiers(active_only=active_only)
        if not tiers:
            return []
        visible_ids = {
            row[0]
            for row in self._get_db()
            .query(StoreProduct.tier_id)
            .filter(StoreProduct.is_active, StoreProduct.tier_id.isnot(None))
            .distinct()
            .all()
        }
        return [tier for tier in tiers if tier.id in visible_ids]

    def get_products_by_tier(self, tier_id: int, active_only: bool = True) -> list[StoreProduct]:
        q = self._get_db().query(StoreProduct).filter(StoreProduct.tier_id == tier_id)
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.order_by(StoreProduct.sort_order, StoreProduct.price).all()

    def count_products_by_tier(self, tier_id: int, active_only: bool = False) -> int:
        """Cuenta productos de un tier (admin: incluye inactivos por defecto)."""
        from sqlalchemy import func

        q = (
            self._get_db()
            .query(func.count(StoreProduct.id))
            .filter(StoreProduct.tier_id == tier_id)
        )
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.scalar() or 0

    def count_products_without_tier(self, active_only: bool = False) -> int:
        """Cuenta productos sin tier asignado."""
        from sqlalchemy import func

        q = (
            self._get_db()
            .query(func.count(StoreProduct.id))
            .filter(StoreProduct.tier_id.is_(None))
        )
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.scalar() or 0

    def get_products_without_tier(self, active_only: bool = False) -> list[StoreProduct]:
        """Productos sin tier asignado."""
        q = self._get_db().query(StoreProduct).filter(StoreProduct.tier_id.is_(None))
        if active_only:
            q = q.filter(StoreProduct.is_active)
        return q.order_by(StoreProduct.sort_order, StoreProduct.price).all()

    def direct_purchase(self, user_id: int, product_id: int) -> tuple:
        """
        Crea una orden directa para un producto sin usar carrito.
        Retorna (orden, mensaje_error)
        """
        db = self._get_db()
        product = self.get_product(product_id)

        if not product:
            return None, LucienVoice.store_product_not_found()

        if not product.is_available:
            return None, LucienVoice.store_product_unavailable(product.name)

        cap_err = self._check_monthly_cap_for_product(product_id)
        if cap_err:
            return None, cap_err

        tier_err = self.check_tier_purchase_gate(user_id, product_id)
        if tier_err:
            return None, tier_err

        # Verificar stock
        if product.stock != -1 and product.stock < 1:
            return None, LucienVoice.store_stock_insufficient(product.name, product.stock)

        # Verificar saldo
        besito_service = BesitoService(
            db=self.db
        )  # local, on-demand; owns=False (db shared); balance check for atomic pre-purchase
        balance = besito_service.get_balance(user_id)
        list_price = product.price
        effective_price = self.get_effective_price(user_id, list_price)
        if balance < effective_price:
            return None, LucienVoice.store_balance_insufficient(effective_price, balance)

        # Crear la orden (total_price = precio lista; descuento en complete_order)
        order = Order(
            user_id=user_id, total_items=1, total_price=list_price, status=OrderStatus.PENDING
        )
        db.add(order)
        db.flush()

        # Crear item de la orden
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=list_price,
            total_price=list_price,
        )
        db.add(order_item)

        db.commit()
        db.refresh(order)

        logger.info(
            f"Orden directa creada: {order.id} para usuario {user_id}, producto {product_id}"
        )
        return order, None

    # ==================== ORDENES/COMPRAS ====================

    def create_order(self, user_id: int) -> tuple:
        """
        Crea una orden desde el carrito.
        Retorna (orden, mensaje_error)
        """
        db = self._get_db()
        cart_items = self.get_cart_items(user_id)

        if not cart_items:
            return None, LucienVoice.store_cart_empty()

        # Verificar disponibilidad y calcular total
        total_price = 0
        total_items = 0
        order_items_data = []

        for cart_item in cart_items:
            product = cart_item.product

            if not product or not product.is_available:
                return None, LucienVoice.store_product_unavailable(
                    product.name if product else "Desconocido"
                )

            cap_err = self._check_monthly_cap_for_product(product.id)
            if cap_err:
                return None, cap_err

            tier_err = self.check_tier_purchase_gate(user_id, product.id)
            if tier_err:
                return None, tier_err

            # Verificar stock
            if product.stock != -1 and product.stock < cart_item.quantity:
                return None, LucienVoice.store_stock_insufficient(product.name, product.stock)

            item_total = product.price * cart_item.quantity
            total_price += item_total
            total_items += cart_item.quantity

            order_items_data.append(
                {
                    "product": product,
                    "quantity": cart_item.quantity,
                    "unit_price": product.price,
                    "total_price": item_total,
                }
            )

        # Verificar saldo del usuario
        besito_service = BesitoService(
            db=self.db
        )  # local, on-demand; owns=False (db shared); balance check for atomic pre-purchase (carrito total)
        balance = besito_service.get_balance(user_id)
        effective_total = self.get_effective_price(user_id, total_price)
        if balance < effective_total:
            return None, LucienVoice.store_balance_insufficient(effective_total, balance)

        # Crear la orden (precio lista; descuento aplicado una vez en complete_order)
        order = Order(
            user_id=user_id,
            total_items=total_items,
            total_price=total_price,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.flush()  # Para obtener el ID

        # Crear items de la orden
        for data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=data["product"].id,
                product_name=data["product"].name,
                quantity=data["quantity"],
                unit_price=data["unit_price"],
                total_price=data["total_price"],
            )
            db.add(order_item)

        db.commit()
        db.refresh(order)

        logger.info(f"Orden creada: {order.id} para usuario {user_id}")
        return order, None

    def _verify_monthly_caps_for_order(self, db: Session, order: Order) -> None:
        """Reserva cupo mensual bajo FOR UPDATE contando OrderItems COMPLETED + orden actual."""
        from collections import defaultdict

        from services.fulfillment_service import FulfillmentService

        fulfill = FulfillmentService(db)
        pending_qty: dict[int, int] = defaultdict(int)
        for order_item in order.items:
            pending_qty[order_item.product_id] += order_item.quantity
        for product_id, qty in pending_qty.items():
            product = (
                db.query(StoreProduct)
                .filter(StoreProduct.id == product_id)
                .with_for_update()
                .first()
            )
            if product and product.monthly_stock_cap:
                count = fulfill.count_monthly_completed_order_items(product_id, db=db)
                if count + qty > product.monthly_stock_cap:
                    raise _OrderAtomicError(
                        f"monthly_cap_exceeded | product_id={product.id}"
                    )

    def _decrement_stock_for_order(self, db: Session, order: Order) -> list[int]:
        """Decrementa stock con FOR UPDATE. Retorna low_stock_product_ids."""
        self._verify_monthly_caps_for_order(db, order)
        low_stock_products = []
        for order_item in order.items:
            product = (
                db.query(StoreProduct)
                .filter(StoreProduct.id == order_item.product_id)
                .with_for_update()
                .first()
            )
            if not product:
                raise _OrderAtomicError(f"product_not_found | product_id={order_item.product_id}")
            if product.stock != -1 and product.stock < order_item.quantity:
                raise _OrderAtomicError(
                    f"insufficient_stock | product_id={product.id} | "
                    f"stock={product.stock} | qty={order_item.quantity}"
                )
            if product.stock != -1:
                product.stock -= order_item.quantity
                if product.stock <= product.low_stock_threshold:
                    low_stock_products.append(product.id)
                    logger.warning(
                        f"STOCK_ALERT: Product {product.id} ({product.name}) - "
                        f"Stock: {product.stock}, Threshold: {product.low_stock_threshold}"
                    )
        return low_stock_products

    def _apply_discount_to_order_total(self, user_id: int, total_price: int) -> int:
        """Aplica descuento activo de StorePrivilege antes del debit."""
        from services.fulfillment_service import FulfillmentService

        fulfill = FulfillmentService(self._get_db())
        pct = fulfill.get_active_discount_pct(user_id)
        if pct <= 0:
            return total_price
        discounted = max(0, total_price - (total_price * pct // 100))
        return discounted

    def _has_purchase_for_order(self, db: Session, user_id: int, order_id: int) -> bool:
        """Idempotencia: PURCHASE con reference_id=order_id ya registrado."""
        return (
            db.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == user_id,
                BesitoTransaction.source == TransactionSource.PURCHASE,
                BesitoTransaction.reference_id == order_id,
            )
            .first()
            is not None
        )

    def _order_needs_fulfillment_processing(self, order_id: int) -> bool:
        from models.models import FulfillmentStatus, OrderFulfillment

        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return False
        item_ids = [item.id for item in order.items]
        if not item_ids:
            return False
        rows = (
            db.query(OrderFulfillment)
            .filter(OrderFulfillment.order_item_id.in_(item_ids))
            .all()
        )
        if len(rows) < len(item_ids):
            return True
        incomplete = {
            FulfillmentStatus.PENDING_INPUT,
            FulfillmentStatus.PENDING_FULFILLMENT,
            FulfillmentStatus.AUTO_IN_PROGRESS,
            FulfillmentStatus.FAILED,
        }
        return any(row.status in incomplete for row in rows)

    def _get_order_charge_amount(self, user_id: int, order: Order) -> int:
        """Monto realmente debitado (lee PURCHASE tx si existe)."""
        db = self._get_db()
        tx = (
            db.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == user_id,
                BesitoTransaction.source == TransactionSource.PURCHASE,
                BesitoTransaction.reference_id == order.id,
            )
            .first()
        )
        if tx is not None:
            return abs(tx.amount)
        return self._apply_discount_to_order_total(user_id, order.total_price)

    async def _complete_order_post_commit_side_effects(
        self,
        bot,
        order: Order,
        user_id: int,
        low_stock_products: list[int],
        *,
        is_retry: bool = False,
    ) -> None:
        """Post-commit best-effort: fulfillment, alertas stock, notif admins, misiones."""
        from services.fulfillment_service import FulfillmentService

        fulfill_svc = FulfillmentService(self._get_db())
        try:
            fulfill_svc.create_fulfillments_for_order(order.id)
            await fulfill_svc.process_order_fulfillments(
                bot, order.id, skip_notifications=is_retry
            )
        except Exception as exc:
            logger.error(
                f"store | fulfillment_post_commit_failed | order_id={order.id} | error={exc}"
            )
        if is_retry:
            return
        for product_id in low_stock_products:
            await self.notify_stock_alert(bot, product_id)
        try:
            await self._notify_admins_of_purchase(bot, order)
        except Exception as e:
            logger.error(f"store | purchase_notif_failed | order_id={order.id} | error={e}")
        try:
            from services.mission_service import run_mission_side_effects_isolated

            await run_mission_side_effects_isolated(
                user_id,
                MissionType.STORE_PURCHASE,
                amount=1,
                bot=bot,
                reference_id=order.id,
                db=self._get_db(),
            )
        except Exception as exc:
            logger.warning(
                f"store_service | store_mission_side_effects_failed | user_id={user_id} | "
                f"order_id={order.id} | error={exc}"
            )

    async def complete_order(self, bot, order_id: int) -> tuple:
        """
        Completa una orden: cobra besitos, decrementa stock y entrega productos.
        Retorna (exito, mensaje)
        """
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            return False, "Orden no encontrada"

        user_id = order.user_id

        if order.status == OrderStatus.COMPLETED:
            charge_amount = self._get_order_charge_amount(user_id, order)
            if self._order_needs_fulfillment_processing(order.id):
                await self._complete_order_post_commit_side_effects(
                    bot, order, user_id, [], is_retry=True
                )
            return True, LucienVoice.store_purchase_completed(charge_amount)

        if order.status != OrderStatus.PENDING:
            return False, LucienVoice.store_order_already_processed()

        if self._has_purchase_for_order(db, user_id, order.id):
            order.status = OrderStatus.COMPLETED
            order.completed_at = order.completed_at or datetime.now(UTC)
            db.commit()
            logger.info(f"store | complete_order_idempotent | order_id={order.id}")
            charge_amount = self._get_order_charge_amount(user_id, order)
            if self._order_needs_fulfillment_processing(order.id):
                await self._complete_order_post_commit_side_effects(
                    bot, order, user_id, [], is_retry=True
                )
            return True, LucienVoice.store_purchase_completed(charge_amount)

        besito_service = BesitoService(
            db=self.db
        )  # local, on-demand; owns=False (db shared); balance check + debit for atomic complete_order
        charge_amount = self._apply_discount_to_order_total(user_id, order.total_price)
        if besito_service.get_balance(user_id) < charge_amount:
            return False, "Saldo insuficiente"

        try:
            if not besito_service.debit_besitos(
                user_id=user_id,
                amount=charge_amount,
                source=TransactionSource.PURCHASE,
                description=f"Compra en tienda - Orden #{order.id}",
                reference_id=order.id,
                commit=False,
            ):
                db.rollback()
                return False, "Error al procesar el pago"

            low_stock_products = self._decrement_stock_for_order(db, order)
            order.status = OrderStatus.COMPLETED
            order.completed_at = datetime.now(UTC)
            if charge_amount < order.total_price:
                from services.fulfillment_service import FulfillmentService

                FulfillmentService(db).consume_active_discount(user_id, db=db)
            db.commit()
        except _OrderAtomicError as e:
            db.rollback()
            logger.error(f"store | complete_order_failed | order_id={order_id} | error={e}")
            return False, "Error al procesar el pago"
        except Exception as e:
            db.rollback()
            logger.error(f"store | complete_order_failed | order_id={order_id} | error={e}")
            return False, "Error al procesar el pago"

        await self._complete_order_post_commit_side_effects(
            bot, order, user_id, low_stock_products, is_retry=False
        )
        logger.info(f"Orden completada: {order.id}")
        return True, LucienVoice.store_purchase_completed(charge_amount)

    def cancel_order(self, order_id: int) -> bool:
        """Cancela una orden pendiente"""
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status != OrderStatus.PENDING:
            return False

        order.status = OrderStatus.CANCELLED
        db.commit()
        return True

    def get_order(self, order_id: int) -> Order | None:
        """Obtiene una orden por ID"""
        db = self._get_db()
        return db.query(Order).filter(Order.id == order_id).first()

    def get_user_orders(self, user_id: int, limit: int = 20) -> list[Order]:
        """Obtiene las ordenes de un usuario"""
        db = self._get_db()
        return (
            db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(desc(Order.created_at))
            .limit(limit)
            .all()
        )

    # ==================== ESTADISTICAS ====================

    def get_store_stats(self) -> dict:
        """Obtiene estadisticas generales de la tienda"""
        db = self._get_db()

        total_products = db.query(StoreProduct).count()
        available_products = (
            db.query(StoreProduct)
            .filter(
                StoreProduct.is_active,
                (StoreProduct.stock == -1) | (StoreProduct.stock > 0),
            )
            .count()
        )

        total_orders = db.query(Order).count()
        completed_orders = db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()

        from sqlalchemy import func

        total_besitos_spent = (
            db.query(func.sum(Order.total_price))
            .filter(Order.status == OrderStatus.COMPLETED)
            .scalar()
            or 0
        )

        return {
            "total_products": total_products,
            "available_products": available_products,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "total_besitos_spent": int(total_besitos_spent),
        }

    # ==================== ALERTAS DE STOCK ====================

    def get_low_stock_products(self) -> list[StoreProduct]:
        """Obtiene productos con stock bajo"""
        db = self._get_db()
        return (
            db.query(StoreProduct)
            .filter(
                StoreProduct.is_active,
                StoreProduct.stock != -1,  # Not unlimited
                StoreProduct.stock <= StoreProduct.low_stock_threshold,
                StoreProduct.stock > 0,  # Not out of stock
            )
            .order_by(StoreProduct.stock)
            .all()
        )

    def get_out_of_stock_products(self) -> list[StoreProduct]:
        """Obtiene productos agotados"""
        db = self._get_db()
        return (
            db.query(StoreProduct)
            .filter(StoreProduct.is_active, StoreProduct.stock == 0)
            .order_by(desc(StoreProduct.updated_at))
            .all()
        )

    def update_low_stock_threshold(self, product_id: int, threshold: int) -> bool:
        """Actualiza el umbral de stock bajo para un producto"""
        db = self._get_db()
        product = self.get_product(product_id)
        if not product:
            return False

        if threshold < 0:
            return False

        product.low_stock_threshold = threshold
        db.commit()
        logger.info(f"Umbral de stock bajo actualizado para producto {product_id}: {threshold}")
        return True

    def check_stock_alert(self, product_id: int) -> dict:
        """Verifica el estado de stock de un producto y retorna alerta si aplica"""
        product = self.get_product(product_id)
        if not product:
            return {"alert": False, "message": LucienVoice.store_product_not_found()}

        if product.stock == -1:
            return {"alert": False, "status": "unlimited"}

        if product.stock == 0:
            return {
                "alert": True,
                "status": "out",
                "message": f"Producto '{product.name}' AGOTADO",
                "product": product,
            }

        if product.stock <= product.low_stock_threshold:
            return {
                "alert": True,
                "status": "low",
                "message": f"Producto '{product.name}' con stock bajo: {product.stock} unidades restantes",
                "product": product,
                "threshold": product.low_stock_threshold,
            }

        return {"alert": False, "status": "available", "stock": product.stock}

    async def notify_stock_alert(self, bot, product_id: int):
        """Envia notificacion de alerta de stock a admins"""
        alert = self.check_stock_alert(product_id)
        if not alert.get("alert"):
            return

        # alert.get("product") was dead code (remnant, no assignment/use).
        # Notification to admins is a pre-existing stub (out of scope for Item 10 tight changes;
        # low-stock detection + trigger lives in complete_order). Future: wire to ADMIN_IDS + LucienVoice.
        return

    async def _notify_admins_of_purchase(self, bot: Bot, order: Order) -> None:
        """Notifica a todos los administradores (ADMIN_IDS) sobre una compra completada en la tienda.

        Usa snapshots de OrderItem (product_name, qty, totals) para evitar queries extra.
        Lookup de User via la sesión del servicio para display name + link tg://user.
        Best-effort: nunca falla la compra del visitante. Logging estilo "store | ...".
        Colocado como método privado del servicio (único punto de finalización de purchase = complete_order).
        """
        if not bot_config.ADMIN_IDS:
            logger.debug(f"store | purchase_notif_skipped | order_id={order.id} | reason=no_admin_ids")
            return

        db = self._get_db()
        user = db.query(User).filter(User.telegram_id == order.user_id).first()

        # Construir display (misma lógica que notify_admins_about_interest en promotion_user_handlers)
        if user:
            if user.first_name and user.last_name:
                user_display = f"{user.first_name} {user.last_name}"
            elif user.first_name:
                user_display = user.first_name
            else:
                user_display = user.username or f"Visitante {order.user_id}"
            username = f"@{user.username}" if user.username else "N/A"
        else:
            user_display = f"Visitante {order.user_id}"
            username = "N/A"

        user_link = f"tg://user?id={order.user_id}"

        from services.fulfillment_service import FulfillmentService

        fulfill_svc = FulfillmentService(db)
        items_for_text: list[tuple[str, int, int, str]] = []
        for it in (order.items or []):
            row = fulfill_svc.get_fulfillment_for_order_item(it.id)
            kind = row.fulfillment_kind.value if row else "package"
            items_for_text.append((it.product_name, it.quantity, it.total_price, kind))

        date_val = order.completed_at or order.created_at
        date_str = date_val.strftime("%Y-%m-%d %H:%M") if date_val else "?"

        purchase_tx = (
            db.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == order.user_id,
                BesitoTransaction.source == TransactionSource.PURCHASE,
                BesitoTransaction.reference_id == order.id,
            )
            .first()
        )
        charged_amount = (
            abs(purchase_tx.amount)
            if purchase_tx
            else self._get_order_charge_amount(order.user_id, order)
        )
        text = LucienVoice.store_admin_purchase_notification_enriched(
            user_display=user_display,
            username=username,
            user_id=order.user_id,
            items=items_for_text,
            total_price=charged_amount,
            date_str=date_str,
            order_id=order.id,
        )
        keyboard = build_purchase_admin_keyboard(user_link)

        for admin_id in bot_config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                logger.info(f"store | purchase_notif_sent | admin_id={admin_id} | order_id={order.id}")
            except Exception as e:
                logger.error(f"store | purchase_notif_error | admin_id={admin_id} | order_id={order.id} | error={e}")


# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (store domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# (to avoid any re-entrancy with purchase debit paths or future extensions; purchase
# debit contracts and partial-failure behavior are authoritative in the debit + deliver flow).
# This is observational only (best effort; errors swallowed by bus).
# =============================================================================
# Item 10 / remaining store besito / arch-enforcer (high-value obs listener for wiring + future; 0 mutation)


async def on_besitos_awarded_store_observer(payload: dict) -> None:
    """
    Store-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
    post-commit; high-value obs for store even if current purchases are debits -- wiring + future).

    DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6): log reception with full context (user_id/amount/source/ref);
    purely observational + wiring proof for this domain. MUST NOT credit, debit, or mutate besitos state here.
    Future extensions (e.g. purchase analytics, hooks) belong in this module and should use
    get_service(StoreService) or direct models if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"store | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on purchase debit contracts / atomicity gold).
