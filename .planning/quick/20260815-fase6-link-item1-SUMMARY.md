# Item 1 — Lucien emisor (Fase 6 link, Part A) — SUMMARY

phase: quick | plan: 20260815-fase6-link | item: Item 1 | mode: standard
Repo: /home/ubuntu/repos/lucienbot
Fecha: 2026-08-15

## Tareas completadas + commits

| Task | Descripción | Commit | Estado |
|------|-------------|--------|--------|
| A1 | Tabla `business_connections` + modelo + export + config `FEATURE_LINK_ENABLED`/`LINK_CHAT_ID` | `0987068` feat(link): business_connections table, model and link flag config | DONE |
| A2 | `LinkNotifier` (upsert + notify `[LINK]`) + handler `business_connection` + `EVENT_VIP_KICKED` + exports | `2058cfd` feat(link): LinkNotifier upsert/notify service + business_connection handler | DONE |
| A3 | Wiring en bot.py: registro del listener ANTES del startup check (R1) + include_router | `f6e025f` feat(link): register EVENT_VIP_KICKED listener at startup | DONE |
| A4 | 3 emisiones post-ban (admin_revoke, scheduler expired, startup expired) + `.env.example` | `4afd702` feat(link): emit VIP_KICKED on all 3 kick points + env docs | DONE |
| A5 | Tests unitarios `tests/unit/test_link_notifier.py` | `c499e08` test(link): LinkNotifier unit tests | DONE |

## Verificaciones corridas

- A1: `import models.models, models, config.settings` OK; `alembic upgrade head` aplicado; `alembic heads` = 1 solo head (`20260815_business_connections`); `tests/integration/test_alembic_heads.py` = 4 passed.
- A2: imports OK (`services.EVENT_VIP_KICKED = "vip_kicked"`); `rg SessionLocal|db.query|get_db handlers/` = 0; funciones de `link_notifier.py` ≤50 LOC.
- A3: `import bot` OK; registro `EVENT_VIP_KICKED` (L223) antes de `check_expired_subscriptions_on_startup` (L226).
- A4: grep `EVENT_VIP_KICKED` = 3 emisiones (vip_service L1067, scheduler_service L240, bot L201) + imports; `test_vip_service.py + test_scheduler.py` = 89 passed, 3 xfailed.
- A5: `test_link_notifier.py` = 6 passed.
- Smoke: `pytest tests/unit/` = 746 passed, 10 xfailed (0 regresiones).
- Integración VIP: `test_vip_flows.py + test_vip_subscription_lifecycle.py` = 41 passed, 4 xfailed.

## Desviaciones y cómo se resolvieron

1. **Colocación de la clase `BusinessConnection`** en `models/models.py`: el PLAN no especificaba ubicación; la inserté tras la clase `Channel` (contrato de tabla/modelo/export intacto). Residual `in-scope-followup`.
2. **Test 5 de A5 dividido en 2 tests** (una fila → id; sin filas → None) en vez de 1 test con 2 aserciones, para aislar el fixture `db_session` (teardown con rollback por test). Conteo final = 6 tests, no 5. Residual `in-scope-followup`.

## Self-Check

```
## Self-Check: PASSED
- [x] Todas las tasks A1-A5 completadas
- [x] Tests del PLAN corridos
- [x] 0 regresiones atribuibles
- [x] Convenciones del proyecto respetadas
```

## Residuales

- **Colocación de `BusinessConnection`** (models/models.py) — `in-scope-followup` — ubicación no especificada en el PLAN; contrato intacto.
- **Test 5 dividido** (tests/unit/test_link_notifier.py) — `in-scope-followup` — 2 tests en vez de 1; comportamiento idéntico.
- **pytest.ini no existe** — `out-of-scope` — `asyncio_mode="auto"` vive en `pyproject.toml [tool.pytest.ini_options]`; solo contexto del entorno.

## Archivos tocados (14)

- `config/settings.py`, `models/models.py`, `models/__init__.py`, `alembic/versions/20260815_business_connections.py`
- `services/link_notifier.py` (nuevo), `services/event_bus.py`, `services/__init__.py`
- `handlers/business_connection_handlers.py` (nuevo), `handlers/__init__.py`
- `bot.py`, `services/vip_service.py`, `services/scheduler_service.py`
- `.env.example`, `tests/unit/test_link_notifier.py` (nuevo)
