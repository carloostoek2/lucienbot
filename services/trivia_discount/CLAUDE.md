# Trivia Discount Service

Servicio para gestionar el sistema de promociones por racha de trivia.

## Dominio

Gestiona la configuración de promociones vinculadas a rachas de trivia y la generación de códigos de descuento cuando los usuarios alcanzan rachas configurables de respuestas correctas.

## Archivos

- `services/trivia_discount_service.py` - Servicio principal
- `models/models.py` - Modelos TriviaPromotionConfig, DiscountCode, DiscountCodeStatus

## Dependencias

- **models.py**: TriviaPromotionConfig, DiscountCode, DiscountCodeStatus, Promotion
- **database.py**: SessionLocal
- **promotion_service.py**: Acceso a promociones comerciales

## Modelos

| Modelo | Descripción |
|--------|------------|
| `DiscountCodeStatus` | Estados: ACTIVE, USED, EXPIRED, CANCELLED |
| `TriviaPromotionConfig` | Configuración de promoción por racha |
| `DiscountCode` | Códigos de descuento generados por usuarios |

## Métodos Principales

### Configuración
- `create_trivia_promotion_config()` - Crea configuración de promoción
- `get_trivia_promotion_config()` - Obtiene por ID
- `get_active_trivia_promotion_configs()` - Lista activas
- `update_trivia_promotion_config()` - Actualiza
- `delete_trivia_promotion_config()` - Elimina
- `pause_trivia_promotion_config()` - Pausa

### Códigos
- `generate_discount_code()` - Genera TRI-XXXXXX
- `get_user_discount_code()` - Código activo de usuario
- `get_codes_by_config()` - Lista de códigos
- `use_discount_code()` - Marca como USADO + incrementa codes_claimed
- `cancel_discount_code()` - Cancela

### Verificación
- `get_config_by_promotion()` - Por ID de promoción
- `is_promotion_configured()` - Boolean
- `get_available_codes_count()` - max_codes - codes_claimed

### Estadísticas
- `get_discount_stats()` - Stats completas

## Validaciones en generate_discount_code

1. Configuración existe y está activa
2. start_date <= now <= end_date (si definido)
3. available > 0 (max_codes - codes_claimed)
4. Usuario no tiene código activo para esta config

## Formato de Código

TRI-XXXXXX donde X es alfanumérico (sin O, I, 0, 1 para evitar confusión)

## Logging

Formato: `trivia_discount_service - {método} - {user_id} - {resultado}`

## Notas

- El contador de códigos disponibles muestra `max_codes - codes_claimed` (reclamados, no emitidos)
- codes_claimed solo se incrementa cuando admin marca código como usado
- Un usuario solo puede tener un código activo por configuración
