# Store Domain

Productos y compras en la tienda virtual.

## Services
- [store_service.py](../store_service.py) - Gestión de tienda
- [package_service.py](../package_service.py) - Paquetes de contenido

## Handlers
- [store_user_handlers.py](../../handlers/store_user_handlers.py) - Usuario
- [store_admin_handlers.py](../../handlers/store_admin_handlers.py) - Admin
- [package_handlers.py](../../handlers/package_handlers.py) - Paquetes

## Modelos
- `Package` - Paquetes de contenido
- `StoreProduct` - Productos en tienda
- `Order` - Órdenes de compra
- `OrderItem` - Ítems de orden

## Flujo de Compra
```
Usuario → Ver productos → Verificar saldo → Confirmar → Debitar besitos → Entregar contenido
```

## StoreService API
```python
- create_product(...)              # Crear producto
- get_available_products()         # Productos disponibles
- process_purchase(user_id, product_id)  # Procesar compra
- get_user_orders(user_id)          # Órdenes del usuario
```

## PackageService API
```python
- create_package(...)              # Crear paquete
- get_package_contents(package_id)  # Contenido del paquete
- deliver_package(user_id, package_id)  # Entregar
```

## Reglas de Negocio
- Verificar saldo **antes** de deduct
- Entregar contenido **después** de debit
- Notificar admins tras compra

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en store_service.py
4. No duplicar lógica con besito_service (usar para debit/credit)
