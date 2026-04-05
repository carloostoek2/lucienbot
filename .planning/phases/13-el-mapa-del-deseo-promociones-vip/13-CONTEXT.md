# Phase 13: El Mapa del Deseo - Promociones VIP Exclusivas

## Goal
Agregar sistema de promociones VIP exclusivas dentro de El Diván con 3 niveles: Premium, Círculo Íntimo y El Secreto.

## Context

### Current State
- El Diván (VIP area) solo tiene un botón: "💌 Enviar mensaje a Diana"
- Sistema de promociones existe (PromotionService, Promotion model, "Me Interesa")
- Promociones actuales están en "Gabinete de Oportunidades" para todos los usuarios

### Desired State
- Botón "🗺️ El Mapa del Deseo" dentro de El Diván
- 3 promociones exclusivas solo para VIPs:
  1. **✨ Premium ✨** - $600 MXN/mes
  2. **❤️‍🔥 Círculo Íntimo ❤️‍🔥** - $950 MXN/mes
  3. **🔒 El Secreto 🔒** - $1,500 MXN/mes
- Las promociones VIP usan el mismo flujo "Me Interesa" existente
- Campo `is_vip_exclusive` en modelo Promotion para filtrar

## Technical Approach (Option C)

1. **Modelo**: Agregar `is_vip_exclusive: bool = False` a `Promotion`
2. **Service**: Agregar `get_vip_exclusive_promotions()`
3. **Handlers VIP**: Agregar botón "El Mapa del Deseo" al menú
4. **Nuevo handler**: Mostrar las 3 promociones VIP con sus detalles
5. **Migration**: Alembic para el nuevo campo
6. **Seed**: Crear las 3 promociones VIP en la base de datos

## Files to Modify

- `models/models.py` - Campo `is_vip_exclusive` en Promotion
- `services/promotion_service.py` - Método `get_vip_exclusive_promotions()`
- `handlers/vip_user_handlers.py` - Botón y handler de El Mapa del Deseo
- `handlers/promotion_user_handlers.py` - Reutilizar flujo "Me Interesa"

## Files to Create

- Alembic migration para el nuevo campo

## Dependencies

- Phase 12 (Mejorar tienda) - debe estar completo
- Sistema de promociones existente (Fase 6)
- Sistema VIP existente (Fase 3)

## Success Criteria

1. Usuario VIP ve botón "🗺️ El Mapa del Deseo" en El Diván
2. Al entrar, ve las 3 promociones exclusivas: Premium, Círculo Íntimo, El Secreto
3. Cada promoción muestra: nombre, descripción, precio, botón "Me Interesa"
4. El flujo "Me Interesa" funciona igual que en el Gabinete general
5. Las promociones VIP no aparecen en el catálogo general
6. Solo usuarios VIP pueden ver y expresar interés en estas promociones
