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
import logging

logger = logging.getLogger(__name__)


class StoreService:
    """Servicio para gestion de tienda"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self.package_service = PackageService(self.db)
    
    # ==================== PRODUCTOS ====================
    
    def create_product(self, name: str, description: str, package_id: int,
                       price: int, stock: int = -1, created_by: int = None) -> StoreProduct:
        """Crea un nuevo producto en la tienda"""
        product = StoreProduct(
            name=name,
            description=description,
            package_id=package_id,
            price=price,
            stock=stock,
            created_by=created_by,
            is_active=True
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        logger.info(f"Producto creado: {name} (ID: {product.id})")
        return product
    
    def get_product(self, product_id: int) -> Optional[StoreProduct]:
        """Obtiene un producto por ID"""
        return self.db.query(StoreProduct).filter(StoreProduct.id == product_id).first()
    
    def get_all_products(self, active_only: bool = True) -> List[StoreProduct]:
        """Obtiene todos los productos"""
        query = self.db.query(StoreProduct)
        if active_only:
            query = query.filter(StoreProduct.is_active == True)
        return query.order_by(desc(StoreProduct.created_at)).all()
    
    def get_available_products(self) -> List[StoreProduct]:
        """Obtiene productos disponibles para compra"""
        return self.db.query(StoreProduct).filter(
            StoreProduct.is_active == True,
            (StoreProduct.stock == -1) | (StoreProduct.stock > 0)
        ).order_by(desc(StoreProduct.created_at)).all()
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """Actualiza un producto"""
        product = self.get_product(product_id)
        if not product:
            return False
        
        allowed_fields = ['name', 'description', 'price', 'stock', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(product, field):
                setattr(product, field, value)
        
        self.db.commit()
        logger.info(f"Producto {product_id} actualizado")
        return True
    
    def delete_product(self, product_id: int) -> bool:
        """Elimina (desactiva) un producto"""
        return self.update_product(product_id, is_active=False)
    
    # ==================== CARRITO ====================
    
    def get_cart_items(self, user_id: int) -> List[CartItem]:
        """Obtiene los items del carrito de un usuario"""
        return self.db.query(CartItem).filter(
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
        return self.db.query(CartItem).filter(CartItem.user_id == user_id).count()
    
    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> tuple:
        """
        Agrega un producto al carrito.
        Retorna (exito, mensaje)
        """
        product = self.get_product(product_id)
        if not product:
            return False, "Producto no encontrado"
        
        if not product.is_available:
            return False, "Producto no disponible"
        
        # Verificar si ya esta en el carrito
        existing = self.db.query(CartItem).filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id
        ).first()
        
        if existing:
            existing.quantity += quantity
            self.db.commit()
            return True, f"Cantidad actualizada: {existing.quantity} x {product.name}"
        
        # Crear nuevo item
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        self.db.add(cart_item)
        self.db.commit()
        
        return True, f"Agregado al carrito: {product.name}"
    
    def remove_from_cart(self, user_id: int, cart_item_id: int) -> bool:
        """Elimina un item del carrito"""
        item = self.db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()
        
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False
    
    def update_cart_quantity(self, user_id: int, cart_item_id: int, quantity: int) -> bool:
        """Actualiza la cantidad de un item en el carrito"""
        if quantity < 1:
            return self.remove_from_cart(user_id, cart_item_id)
        
        item = self.db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()
        
        if item:
            item.quantity = quantity
            self.db.commit()
            return True
        return False
    
    def clear_cart(self, user_id: int) -> bool:
        """Vacia el carrito del usuario"""
        items = self.db.query(CartItem).filter(CartItem.user_id == user_id).all()
        for item in items:
            self.db.delete(item)
        self.db.commit()
        return True
    
    # ==================== ORDENES/COMPRAS ====================
    
    def create_order(self, user_id: int) -> tuple:
        """
        Crea una orden desde el carrito.
        Retorna (orden, mensaje_error)
        """
        cart_items = self.get_cart_items(user_id)
        
        if not cart_items:
            return None, "El carrito esta vacio"
        
        # Verificar disponibilidad y calcular total
        total_price = 0
        total_items = 0
        order_items_data = []
        
        for cart_item in cart_items:
            product = cart_item.product
            
            if not product or not product.is_available:
                return None, f"Producto no disponible: {product.name if product else 'Desconocido'}"
            
            # Verificar stock
            if product.stock != -1 and product.stock < cart_item.quantity:
                return None, f"Stock insuficiente para: {product.name} (disponible: {product.stock})"
            
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
            return None, f"Saldo insuficiente. Necesitas: {total_price} besitos. Tienes: {balance}"
        
        # Crear la orden
        order = Order(
            user_id=user_id,
            total_items=total_items,
            total_price=total_price,
            status=OrderStatus.PENDING
        )
        self.db.add(order)
        self.db.flush()  # Para obtener el ID
        
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
            self.db.add(order_item)
        
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Orden creada: {order.id} para usuario {user_id}")
        return order, None
    
    async def complete_order(self, bot, order_id: int) -> tuple:
        """
        Completa una orden: cobra besitos, decrementa stock y entrega productos.
        Retorna (exito, mensaje)
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
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
        for order_item in order.items:
            product = order_item.product
            
            # Decrementar stock
            if product.stock != -1:
                product.stock -= order_item.quantity
            
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
        self.db.commit()
        
        logger.info(f"Orden completada: {order.id}")
        return True, f"Compra completada! Se debitaron {order.total_price} besitos."
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancela una orden pendiente"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status != OrderStatus.PENDING:
            return False
        
        order.status = OrderStatus.CANCELLED
        self.db.commit()
        return True
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Obtiene una orden por ID"""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_user_orders(self, user_id: int, limit: int = 20) -> List[Order]:
        """Obtiene las ordenes de un usuario"""
        return self.db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(desc(Order.created_at)).limit(limit).all()
    
    # ==================== ESTADISTICAS ====================
    
    def get_store_stats(self) -> dict:
        """Obtiene estadisticas de la tienda"""
        total_products = self.db.query(StoreProduct).filter(StoreProduct.is_active == True).count()
        available_products = len(self.get_available_products())
        
        total_orders = self.db.query(Order).count()
        completed_orders = self.db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()
        
        # Total de besitos gastados
        completed = self.db.query(Order).filter(Order.status == OrderStatus.COMPLETED).all()
        total_besitos_spent = sum(o.total_price for o in completed)
        
        return {
            'total_products': total_products,
            'available_products': available_products,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_besitos_spent': total_besitos_spent
        }
    
    def __del__(self):
        """Cierra la sesion de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
