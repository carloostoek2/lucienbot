---
name: lucien-checklist
description: Pre-commit checklist for Lucien Bot. Trigger when: about to commit changes, before finalizing a PR, or when asking "is this ready?". This skill provides the validation checklist to ensure code quality before any code is committed or merged.
---

# Lucien Bot — Checklist de Desarrollo

**Obligatorio** antes de hacer commit o crear PR.

## Checklist

- [ ] **¿La función tiene máximo 50 líneas?**
- [ ] **¿El nombre sigue el patrón `verbo+contexto+resultado`?**
- [ ] **¿Se incluyó logging con formato `módulo/acción/user_id=resultado`?**
- [ ] **¿Los handlers solo llaman a services (sin lógica)?**
- [ ] **¿Se validó con `is_admin()` o `has_sufficient_balance()` donde aplica?**
- [ ] **¿Se usó transacción para operaciones atómicas?**
- [ ] **¿Se creó migración para nuevos valores de enum antes de usarlos?**
- [ ] **¿Se actualizó el CLAUDE.md del dominio si hay cambios?**
- [ ] **¿Se probó en SQLite local antes de subir?**

## Reglas Detalladas

### Límite de 50 Líneas
Si una función excede 50 líneas, debe dividirse en funciones más pequeñas con responsabilidad única.

### Naming
```python
# ❌ Incorrecto
def process()
def handle_data()

# ✅ Correcto
def credit_besitos()
def get_balance()
def validate_admin_permission()
```

### Logging
```python
# ❌ Incorrecto
logger.info(" credited besitos")

# ✅ Correcto
logger.info(f"besito_service/credit_besitos/{user_id}={amount}")
```

### Handlers
```python
# ❌ Incorrecto - Lógica en handler
async def handle(callback):
    user = await session.get(User, callback.from_user.id)
    user.besitos += 10
    await session.commit()

# ✅ Correcto - Solo llama service
async def handle(callback):
    service = BesitoService()
    service.credit_besitos(callback.from_user.id, 10)
```

### Migraciones
```python
# ❌ Incorrecto - Enum en la misma migración que lo usa
def upgrade():
    op.add_column('table', sa.Column('source', sa.Enum('NEW_VALUE')))

# ✅ Correcto - MIGRACIÓN DEDICADA para enum
# Primero: alembic revision -m "Add NEW_VALUE to source enum"
# Segundo: editar migración con IF NOT EXISTS
# Tercero: usar enum en código
```

### Transacciones
```python
# ❌ Incorrecto - Sin transacción
balance.besitos += amount
session.commit()

# ✅ Correcto - Con transacción
with session.begin():
    balance.besitos += amount
    # Si falla, rollback automático
```

## Voice Check

¿El código habla como Lucien?
- "¿El mensaje usa 'visitantes' en vez de 'usuarios'?"
- "¿Las variables están en snake_case?"
- "¿Los mensajes usan el tono elegante de Lucien?"

## Archivos que Cambiaron

Revisar que los archivos correctos fueron modificados:
- ¿handlers/ solo tiene routing?
- ¿services/ tiene la lógica de negocio?
- ¿models/ tiene los modelos?
- ¿alembic/versions/ tiene las migraciones necesarias?