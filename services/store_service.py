"""
Servicio de Tienda - Lucien Bot

Gestiona el catalogo de productos, carrito y compras.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import StoreProduct, CartItem, Order, OrderItem, OrderStatus, Package
from models.database import SessionLocal
from services.besito_service import BesitoService
from services.package_service import PackageService
from models.models import TransactionSource
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)


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
        self.besito_service = BesitoService(db)
        self.package_service = PackageService(db)

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
    
    # ==================== PRODUCTOS ====================

    def create_product(self, name: str, description: str, package_id: int,
                       price: int, stock: int = -1, created_by: int = None) -> StoreProduct:
        """Crea un nuevo producto en la tienda"""
        db = self._get_db()
        product = StoreProduct(
            name=name,
            description=description,
            package_id=package_id,
            price=price,
            stock=stock,
            created_by=created_by,
            is_active=True
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"Producto creado: {name} (ID: {product.id})")
        return product

    def get_product(self, product_id: int) -> Optional[StoreProduct]:
        """Obtiene un producto por ID"""
        db = self._get_db()
        return db.query(StoreProduct).filter(StoreProduct.id == product_id).first()

    def get_all_products(self, active_only: bool = True) -> List[StoreProduct]:
        """Obtiene todos los productos"""
        db = self._get_db()
        query = db.query(StoreProduct)
        if active_only:
            query = query.filter(StoreProduct.is_active == True)
        return query.order_by(desc(StoreProduct.created_at)).all()

    def get_available_products(self) -> List[StoreProduct]:
        """Obtiene productos disponibles para compra"""
        db = self._get_db()
        return db.query(StoreProduct).filter(
            StoreProduct.is_active == True,
            (StoreProduct.stock == -1) | (StoreProduct.stock > 0)
        ).order_by(desc(StoreProduct.created_at)).all()

    def search_products(self, query: str, active_only: bool = True) -> List[StoreProduct]:
        """Busca productos por nombre o descripcion"""
        db = self._get_db()
        search = f"%{query}%"
        q = db.query(StoreProduct).filter(
            (StoreProduct.name.ilike(search)) | (StoreProduct.description.ilike(search))
        )
        if active_only:
            q = q.filter(StoreProduct.is_active == True)
        return q.order_by(desc(StoreProduct.created_at)).all()

    def get_products_by_price_range(self, min_price: int = 0, max_price: int = None,
                                    active_only: bool = True) -> List[StoreProduct]:
        """Obtiene productos en rango de precio"""
        db = self._get_db()
        q = db.query(StoreProduct).filter(StoreProduct.price >= min_price)
        if max_price is not None:
            q = q.filter(StoreProduct.price <= max_price)
        if active_only:
            q = q.filter(StoreProduct.is_active == True)
        return q.order_by(StoreProduct.price).all()

    def get_products_by_category(self, category_id: int, active_only: bool = True) -> List[StoreProduct]:
        """Obtiene productos por categoria (via package)"""
        db = self._get_db()
        # Get packages in category
        packages = db.query(Package).filter(Package.category_id == category_id).all()
        package_ids = [p.id for p in packages]

        q = db.query(StoreProduct).filter(StoreProduct.package_id.in_(package_ids))
        if active_only:
            q = q.filter(StoreProduct.is_active == True)
        return q.order_by(desc(StoreProduct.created_at)).all()

    def filter_products(self, category_id: int = None, min_price: int = None,
                        max_price: int = None, in_stock_only: bool = False,
                        active_only: bool = True) -> List[StoreProduct]:
        """Filtra productos por multiples criterios"""
        db = self._get_db()
        q = db.query(StoreProduct)

        if active_only:
            q = q.filter(StoreProduct.is_active == True)

        if category_id:
            packages = db.query(Package).filter(Package.category_id == category_id).all()
            package_ids = [p.id for p in packages]
            q = q.filter(StoreProduct.package_id.in_(package_ids))

        if min_price is not None:
            q = q.filter(StoreProduct.price >= min_price)

        if max_price is not None:
            q = q.filter(StoreProduct.price <= max_price)

        if in_stock_only:
            q = q.filter(
                (StoreProduct.stock == -1) | (StoreProduct.stock > 0)
            )

        return q.order_by(desc(StoreProduct.created_at)).all()

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Actualiza un producto"""
        db = self._get_db()
        product = self.get_product(product_id)
        if not product:
            return False

        allowed_fields = ['name', 'description', 'price', 'stock', 'is_active', 'low_stock_threshold']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(product, field):
                setattr(product, field, value)

        db.commit()
        logger.info(f"Producto {product_id} actualizado")
        return True

    def delete_product(self, product_id: int) -> bool:
        """Elimina (desactiva) un producto"""
        return self.update_product(product_id, is_active=False)

    # ==================== CARRITO ====================

    def get_cart_items(self, user_id: int) -> List[CartItem]:
        """Obtiene los items del carrito de un usuario"""
        db = self._get_db()
        return db.query(CartItem).filter(
            CartItem.user_id == user_id
        ).order_by(desc(CartItem.added_at)).all()

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
        existing = db.query(CartItem).filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id
        ).first()

        if existing:
            existing.quantity += quantity
            db.commit()
            return True, LucienVoice.store_cart_updated(existing.quantity, product.name)

        # Crear nuevo item
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        db.add(cart_item)
        db.commit()

        return True, LucienVoice.store_cart_added(product.name)

    def remove_from_cart(self, user_id: int, cart_item_id: int) -> bool:
        """Elimina un item del carrito"""
        db = self._get_db()
        item = db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()

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
        item = db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()

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

            # Verificar stock
            if product.stock != -1 and product.stock < cart_item.quantity:
                return None, LucienVoice.store_stock_insufficient(product.name, product.stock)

            item_total = product.price * cart_item.quantity
            total_price += item_total
            total_items += cart_item.quantity

            order_items_data.append({
                'product': product,
                'quantity': cart_item.quantity,
                'unit_price': product.price,
                'total_price': item_total
            })

        # Verificar saldo del usuario
        balance = self.besito_service.get_balance(user_id)
        if balance < total_price:
            return None, LucienVoice.store_balance_insufficient(total_price, balance)

        # Crear la orden
        order = Order(
            user_id=user_id,
            total_items=total_items,
            total_price=total_price,
            status=OrderStatus.PENDING
        )
        db.add(order)
        db.flush()  # Para obtener el ID

        # Crear items de la orden
        for data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=data['product'].id,
                product_name=data['product'].name,
                quantity=data['quantity'],
                unit_price=data['unit_price'],
                total_price=data['total_price']
            )
            db.add(order_item)

        db.commit()
        db.refresh(order)

        logger.info(f"Orden creada: {order.id} para usuario {user_id}")
        return order, None

    async def complete_order(self, bot, order_id: int) -> tuple:
        """
        Completa una orden: cobra besitos, decrementa stock y entrega productos.
        Retorna (exito, mensaje)
        """
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return False, "Orden no encontrada"

        if order.status != OrderStatus.PENDING:
            return False, "La orden ya fue procesada"

        user_id = order.user_id

        # Verificar saldo nuevamente
        balance = self.besito_service.get_balance(user_id)
        if balance < order.total_price:
            return False, "Saldo insuficiente"

        # Cobrar besitos
        success = self.besito_service.debit_besitos(
            user_id=user_id,
            amount=order.total_price,
            source=TransactionSource.PURCHASE,
            description=f"Compra en tienda - Orden #{order.id}",
            reference_id=order.id
        )

        if not success:
            return False, "Error al procesar el pago"

        # Procesar cada item
        low_stock_products = []
        for order_item in order.items:
            product = db.query(StoreProduct).filter(
                StoreProduct.id == order_item.product_id
            ).with_for_update().first()

            if not product:
                continue

            # Decrementar stock
            if product.stock != -1:
                product.stock -= order_item.quantity

                # Check for low stock alert
                if product.stock <= product.low_stock_threshold:
                    low_stock_products.append(product.id)
                    logger.warning(
                        f"STOCK_ALERT: Product {product.id} ({product.name}) - "
                        f"Stock: {product.stock}, Threshold: {product.low_stock_threshold}"
                    )

            # Entregar paquete
            if product.package:
                await self.package_service.deliver_package_to_user(
                    bot=bot,
                    user_id=user_id,
                    package_id=product.package_id
                )

        # Actualizar orden
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        db.commit()

        # Notificar alertas de stock a admins
        for product_id in low_stock_products:
            await self.notify_stock_alert(bot, product_id)

        logger.info(f"Orden completada: {order.id}")
        return True, f"Compra completada! Se debitaron {order.total_price} besitos."

    def cancel_order(self, order_id: int) -> bool:
        """Cancela una orden pendiente"""
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status != OrderStatus.PENDING:
            return False

        order.status = OrderStatus.CANCELLED
        db.commit()
        return True

    def get_order(self, order_id: int) -> Optional[Order]:
        """Obtiene una orden por ID"""
        db = self._get_db()
        return db.query(Order).filter(Order.id == order_id).first()

    def get_user_orders(self, user_id: int, limit: int = 20) -> List[Order]:
        """Obtiene las ordenes de un usuario"""
        db = self._get_db()
        return db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(desc(Order.created_at)).limit(limit).all()

    # ==================== ALERTAS DE STOCK ====================

    def get_low_stock_products(self) -> List[StoreProduct]:
        """Obtiene productos con stock bajo"""
        db = self._get_db()
        return db.query(StoreProduct).filter(
            StoreProduct.is_active == True,
            StoreProduct.stock != -1,  # Not unlimited
            StoreProduct.stock <= StoreProduct.low_stock_threshold,
            StoreProduct.stock > 0  # Not out of stock
        ).order_by(StoreProduct.stock).all()

    def get_out_of_stock_products(self) -> List[StoreProduct]:
        """Obtiene productos agotados"""
        db = self._get_db()
        return db.query(StoreProduct).filter(
            StoreProduct.is_active == True,
            StoreProduct.stock == 0
        ).order_by(desc(StoreProduct.updated_at)).all()

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
            return {'alert': False, 'message': 'Producto no encontrado'}

        if product.stock == -1:
            return {'alert': False, 'status': 'unlimited'}

        if product.stock == 0:
            return {
                'alert': True,
                'status': 'out',
                'message': f"Producto '{product.name}' AGOTADO",
                'product': product
            }

        if product.stock <= product.low_stock_threshold:
            return {
                'alert': True,
                'status': 'low',
                'message': f"Producto '{product.name}' con stock bajo: {product.stock} unidades restantes",
                'product': product,
                'threshold': product.low_stock_threshold
            }

        return {'alert': False, 'status': 'available', 'stock': product.stock}

    async def notify_stock_alert(self, bot, product_id: int):
        """Envia notificacion de alerta de stock a admins"""
        from config.settings import bot_config
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        alert = self.check_stock_alert(product_id)
        if not alert.get('alert'):
            return

        product = alert.get('product')
        message = alert.get('message')

        alert_text = (
            f"🎩 <b>Lucien - Alerta de Inventario</b>\n\n"
            f"{message}\n\n"
            f"<i>Gestiona el stock desde el panel de administracion.</i>"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Gestionar stock",
                callback_data=f"restock_product_{product_id}"
            )]
        ])

        # Send to all admins
        for admin_id in bot_config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=alert_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error enviando alerta de stock a admin {admin_id}: {e}")

    # ==================== ESTADISTICAS ====================

    def get_store_stats(self) -> dict:
        """Obtiene estadisticas de la tienda"""
        db = self._get_db()
        total_products = db.query(StoreProduct).filter(StoreProduct.is_active == True).count()
        available_products = len(self.get_available_products())

        total_orders = db.query(Order).count()
        completed_orders = db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()

        # Total de besitos gastados
        completed = db.query(Order).filter(Order.status == OrderStatus.COMPLETED).all()
        total_besitos_spent = sum(o.total_price for o in completed)

        return {
            'total_products': total_products,
            'available_products': available_products,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_besitos_spent': total_besitos_spent
        }
