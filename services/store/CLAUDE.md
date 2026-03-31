# Store Domain

Tienda virtual: catálogo, carrito, checkout y entrega de paquetes de contenido.

## Services
- `store_service.py` — Catálogo, carrito, órdenes, checkout
- `package_service.py` — Paquetes de archivos, stock, entrega

## Handlers
- `store_user_handlers.py` — Usuario: catálogo, carrito, checkout, historial
- `store_admin_handlers.py` — Admin: crear productos
- `package_handlers.py` — Admin: crear paquetes, enviar paquete a usuario

## Modelos clave
- `Package` — Contenido (archivos). Stock: store_stock (para venta), reward_stock (para recompensas)
- `PackageFile` — Archivo dentro de un paquete (file_id de Telegram)
- `StoreProduct` — Producto en tienda: name, description, package_id, price (besitos), stock
- `CartItem` — Ítem en carrito
- `Order` / `OrderItem` — Órden completada

## Stock de Paquetes — Convenciones

| Valor | Significado |
|-------|-------------|
| `-1` | Ilimitado |
| `-2` | No disponible / no vendible |
| `0` | Agotado |
| `> 0` | Disponible |

## Flujo de Compra

```
Usuario → /shop → Ver catálogo
    → add_to_cart() → se guarda en CartItem
    → view_cart / remove_from_cart / update_quantity
    → checkout
    → StoreService.complete_order()
        → Verificar has_sufficient_balance (BesitoService)
        → Debitar besitos (BesitoService.debit_besitos())
        → Marcar orden como COMPLETED
        → Decrementar store_stock del Package
        → Entregar: PackageService.deliver_package_to_user()
            → Enviar archivos via bot.send_media_group()
```

## StoreService API
```python
# Productos
create_product(name, description, package_id, price, stock) -> StoreProduct
get_product(product_id) -> StoreProduct
get_all_products(active_only=True) -> list[StoreProduct]
get_available_products() -> list[StoreProduct]
update_product(product_id, **kwargs) -> bool
delete_product(product_id) -> bool

# Carrito
get_cart_items(user_id) -> list[CartItem]
get_cart_total(user_id) -> int
get_cart_items_count(user_id) -> int
add_to_cart(user_id, product_id, quantity=1) -> tuple  # (success, error)
remove_from_cart(user_id, cart_item_id) -> bool
update_cart_quantity(user_id, cart_item_id, quantity) -> bool
clear_cart(user_id) -> bool

# Órdenes
create_order(user_id) -> tuple  # (order, error) — crea orden PENDING
complete_order(user_id) -> tuple  # (order_id, error) — debit + deliver
cancel_order(order_id) -> bool
get_order(order_id) -> Order
get_user_orders(user_id, limit=20) -> list[Order]
get_store_stats() -> dict
```

## PackageService API
```python
# Paquetes
create_package(name, description, store_stock, reward_stock) -> Package
add_file_to_package(package_id, file_id, file_type, file_name, file_size) -> PackageFile
get_package(package_id) -> Package
get_all_packages(active_only=True) -> list[Package]
get_available_packages_for_store() -> list[Package]
get_available_packages_for_rewards() -> list[Package]
get_package_files(package_id) -> list[PackageFile]  # NO "get_package_contents"
update_package(package_id, **kwargs) -> bool
delete_package(package_id) -> bool
remove_file_from_package(file_id) -> bool

# Stock
decrement_store_stock(package_id) -> bool
decrement_reward_stock(package_id) -> bool
add_store_stock(package_id, amount) -> bool
add_reward_stock(package_id, amount) -> bool

# Entrega
deliver_package_to_user(user_id, package_id) -> bool  # NO "deliver_package"

get_package_stats(package_id) -> dict
```

## Reglas de Negocio
- Verificar `has_sufficient_balance` ANTES de complete_order
- Stock se decrementa SOLO en complete_order (no en create_order)
- Entrega ocurre DENTRO de complete_order después del debit exitoso
- No существует "process_purchase" — el flujo completo está en complete_order

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Métodos correctos: `deliver_package_to_user()`, `get_package_files()`
4. Si necesitas stock de reward: `decrement_reward_stock()` no `decrement_store_stock()`
