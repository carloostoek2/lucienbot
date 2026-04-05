---
title: Sistema de auditoría de economía con historial de movimientos
created: 2026-04-05
area: gamification
source: conversation
---

# Sistema de auditoría de economía con historial de movimientos

**Description:**
Sistema de auditoría de economía en el que se registre cada movimiento que tengan todos los usuarios de manera individual. Los usuarios pueden acceder a su historial de movimientos económicos y el administrador también puede acceder a toda esa información.

## Requirements

- [ ] Crear modelo `TransactionLog` o similar para registrar movimientos económicos
  - user_id, tipo_movimiento (ingreso/egreso), cantidad, concepto, fecha, balance_resultante
  - Índices por user_id y fecha para consultas eficientes
- [ ] Integrar logging en operaciones económicas:
  - `BesitoService`: reward_besitos, spend_besitos, transfer_besitos
  - `StoreService`: compras en tienda
  - `MissionService`: recompensas de misiones
  - `VIPService`: pagos de suscripciones
- [ ] Handler para usuarios: `/historial` o botón en menú
  - Mostrar últimos N movimientos con paginación
  - Filtros por tipo (ingresos/egresos/todos)
  - Resumen: total ingresos, total egresos, balance actual
- [ ] Handler para admin: auditoría global
  - Ver historial de cualquier usuario por ID/username
  - Exportar movimientos (CSV)
  - Filtros por fecha, tipo, rango de montos
  - Estadísticas: volumen total, usuarios más activos, etc.

## Related Areas

- gamification (BesitoService - core de economía)
- models (nuevo modelo TransactionLog)
- handlers/user (historial personal)
- handlers/admin (auditoría global)
- analytics (exportación CSV, estadísticas)

## Technical Notes

- Usar transacciones DB para garantizar atomicidad (movimiento + log)
- Considerar tabla separada o JSONB en PostgreSQL para metadata adicional
- Rate limiting en consultas de historial para evitar sobrecarga
- Retención: ¿archivar movimientos antiguos? ¿límite de tiempo?
