---
phase: 8
discuss_mode: auto
date: 2026-03-30
---

# Phase 8: Testing & Technical Debt — Context

## Phase Reference

- **Phase:** 8 — Testing & Technical Debt
- **Goal:** Tests automatizados, configuración de linting y refactor de deuda técnica
- **Requirements:** TEST-01, TEST-02, TEST-03, SCHED-02, SEC-03

## Success Criteria

1. Tests unitarios para VIPService, ChannelService, BesitoService, MissionService
2. Tests de integración para flujos VIP y canales
3. Configuración de ruff/black/isort integrada
4. Sesiones DB con context managers (eliminar `__del__`)
5. Startup check para suscripciones expiradas
6. SELECT FOR UPDATE en token redemption (resolver race condition)

## Key Decisions

### Testing Framework
- **Framework:** pytest con pytest-asyncio para tests async
- **Estructura:** Carpeta `tests/` con subcarpetas `unit/` y `integration/`
- **Database tests:** SQLite in-memory (`:memory:`) con rollback por test
- **Fixtures:** Base de datos recreada por test para aislamiento
- **Async pattern:** `@pytest.mark.asyncio` en tests async

### Test Coverage Strategy
- **Unit tests:** Services principales (VIPService, ChannelService, BesitoService, MissionService)
- **Integration tests:** Flujos completos (canje VIP, expiración, gamificación)
- **Mocking:** Bot de Telegram mockeado, APIs externas aisladas
- **Target coverage:** ≥70% en lógica de negocio (services/)

### Linting & Code Quality
- **Linter:** ruff (reemplaza flake8, pylint, black, isort en una herramienta)
- **Config:** `pyproject.toml` con reglas estrictas para imports y async
- **Pre-commit:** Opcional (evaluar si vale la pena el overhead)
- **Format:** ruff format en lugar de black

### Technical Debt Fixes

#### 1. Session Management (SCHED-02, SEC-03)
- **Problema:** `__del__` para cerrar sesiones DB es poco confiable
- **Solución:** Context managers (`async with session_scope():`)
- **Scope:** Reemplazar en todos los services que usan `__del__`
- **Patrón:**
  ```python
  @asynccontextmanager
  async def session_scope():
      session = Session()
      try:
          yield session
          await session.commit()
      except:
          await session.rollback()
          raise
      finally:
          await session.close()
  ```

#### 2. Race Condition en Token Redemption (SEC-03)
- **Problema:** Dos usuarios pueden canjear el mismo token simultáneamente
- **Solución:** `SELECT FOR UPDATE` en query del token
- **Scope:** `VIPService.redeem_token()`
- **DB Support:** SQLite (LIMIT 1), PostgreSQL (FOR UPDATE)

#### 3. Startup Check para Suscripciones Expiradas (SCHED-02)
- **Problema:** Suscripciones pueden expirar mientras el bot está offline
- **Solución:** Verificar expiraciones pendientes en `on_startup()`
- **Scope:** Handler de startup en `bot.py`
- **Lógica:** Query subscriptions WHERE expires_at < now AND status = 'active'

## Out of Scope

- Tests para handlers (muy acoplados a Telegram) — solo integration tests
- MemoryStorage → RedisStorage (deferred a Phase 9)
- Refactor de handlers grandes (>900 líneas) — riesgo alto, beneficios bajos
- Coverage 100% — target 70% en lógica de negocio es suficiente

## Architecture Constraints

- Tests deben seguir misma estructura de capas: test → service → model
- No modificar comportamiento durante refactor de sesiones
- SQLAlchemy 2.0 async API para tests
- Mantener compatibilidad SQLite/PostgreSQL en tests

## Dependencies to Add

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
ruff>=0.3.0
```

## Verification Plan

1. Todos los services principales tienen tests unitarios
2. `pytest --cov=services` reporta ≥70% coverage
3. `ruff check .` pasa sin errores
4. `ruff format --check .` pasa sin cambios pendientes
5. No quedan `__del__` en services (verificar con grep)
6. Token redemption usa SELECT FOR UPDATE
7. Startup handler verifica expiraciones pendientes

---
*Context created: 2026-03-30 via discuss-phase --auto*
