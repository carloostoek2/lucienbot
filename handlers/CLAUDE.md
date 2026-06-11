# Handlers

Solo enrutan eventos desde Telegram. **SIN lógica de negocio, SIN acceso a DB.**

## Middleware

- `ThrottlingMiddleware` (middlewares/rate_limiter.py) — Rate limiting global (canonical)
  - 5 requests por ventana de 10 segundos por usuario (via aiolimiter.AsyncLimiter + per-user limiters)
  - **Custodios tienen bypass completo** (ADMIN_BYPASS=True from config, real bot_config.ADMIN_IDS)
  - Mensaje de throttle (Lucien voice): "Espera un momento... no tan rapido." (con show_alert)
  - Idle cleanup after 5min TTL, debug logging, robust answer on limit exceeded
  - Legacy shim at handlers/rate_limit_middleware.py (DEPRECATED, emits warning on import; gsd-mw-hardening phase 2)

- `IdempotencyMiddleware` (middlewares/idempotency.py) — Callback deduplication (gsd-mw-hardening phase 3)
  - Previene doble procesamiento de CallbackQuery por reintentos de Telegram
  - Usa IdempotencyCache global (TTL 60s)
  - En dupe: answer() + skip (no llama handler) + log
  - Solo para CBs; Messages y primer CB pasan
  - Robusto (try en answer), logging estándar
  - Reemplaza los guards manuales que existían en gamification_user_handlers.handle_reaction y reward_user_handlers (2 sitios) — removidos en phase 5

Orden de registro en bot.py (phase 4): Error outer → Idempotency (cb) → Throttling (cb); Throttling (messages).

## Estructura

```
handlers/
├── common_handlers.py           # /start, /help, profile, cancel
├── admin_handlers.py            # Panel admin [AdminStates]
├── channel_handlers.py          # Gestión canales [ChannelStates]
├── vip_handlers.py             # Admin: Tarifas y tokens [TariffStates, TokenStates]
├── vip_user_handlers.py        # Círculo VIP: mensajes anónimos [AnonymousMessageStates]
├── anonymous_message_admin_handlers.py  # Diana: gestión de susurros [AnonymousReplyStates]
├── free_channel_handlers.py    # ChatJoinRequest, ChatMemberUpdatedFilter
├── gamification_user_handlers.py
├── gamification_admin_handlers.py  # [EmojiConfigStates, DailyGiftConfigStates]
├── broadcast_handlers.py        # Wizard 8 pasos [BroadcastStates]
├── package_handlers.py          # [PackageWizardStates, SendPackageStates]
├── mission_user_handlers.py
├── mission_admin_handlers.py    # [MissionWizardStates]
├── reward_admin_handlers.py     # [RewardWizardStates, PackageFromRewardStates]
├── store_user_handlers.py
├── store_admin_handlers.py      # [ProductWizardStates]
├── promotion_user_handlers.py
├── promotion_admin_handlers.py  # [PromotionWizardStates, BlockUserStates]
├── story_user_handlers.py      # [ArchetypeQuizStates]
├── story_admin_handlers.py      # [Node/Choice/Archetype/AchievementWizardStates]
└── analytics_handlers.py       # /stats, /export
```

## Reglas de Handlers

1. **UN service** por handler (exactly 1 call, usual via `with get_service(XXXService) as svc:`)
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos (estándar "módulo | acción | user_id | resultado")

## Patrón Probado en Hardener (tirones 25-29 / Items 7-11)
Para handlers largos (wizards admin multi-step, lists, details, etc. >50 LOC común): 
- Consolidar a **exactly 1 service** por entrypoint (MissionService / StoreService / RewardService via get_service + thin delegates en service para cross-domain wizard steps si necesario, e.g. get_all_rewards_for_mission_wizard).
- Extraer **funciones puras** (verb+context+result naming; "Función pura (sin estado ni side-effects)."; stateless, importable, unit-testable; colocadas antes de clases o top-level; 1:1 de lógica previa inline) para builders de texto/keyboard/calcs (compute_*, build_*_text_and_keyboard, etc.) y llevar **todas las funciones <=50 LOC** (verificado vía inspect.getsourcelines post-edit).
- **Ports de tests**: @patch target "handlers.*.get_service" + mock.__enter__ / __exit__ asserts + setups en delegates del svc mock; mantener asserts exactos de UI/strings/cbs/estados/empty cases; docstrings "ported to 1-service pattern (XXXService only + delegate...) + pure UI helpers. Arch-enforcer note addressed. Precedent from item7/8/9".
- Nueva clase `Test*PureHelpers` al final del test file (5-11+ tests import-inside per conv; no @patch en los puros; cubren 1:1 strings/emojis/cbs/rows/edges/empty; usan MagicMock post-assign .name/.value para ejecución real de puros; assert edit_text/answer/params).
- UI render **1:1 idéntico** (textos, emojis, backs, truncation, cb packing, estados "Sin descripcion"/"Ninguna", Lucien, "Paso X de N", etc. pinned desde impact/PLAN).
- Logging estándar dentro de los withs post-success.
- 0 behavior / 0 delivery / 0 atomicity / 0 other handlers impact.
- Verificación: arch-enforcer (PASS WITH NOTES 0 critical; grep 0 bare otros svcs, N with get_service, N puros, LOC<=50, delegates, UI1:1, logging, 3 crit protected orthogonal); test-guardian ("suite protege adecuadamente"; re-runs handler + pure subset + broader cross + golds; coverage puros direct + ports + delegates); self-check PASSED + GSD pre every + pool phrase.
- Ejemplos: Item 9/27 mission_admin_handlers (10+ puros + delegates + 9 withs Mission + TestMissionAdminPureHelpers 11; 27-SUMMARY + impact9 + arch9 + test9 + gsd79+); Item 8/26 store_admin (6+ puros + 1svc Store + TestStoreAdminPureHelpers 9; 26-SUMMARY); Item 7/25 reward_user (2 puros + 1svc Mission; 25-SUMMARY). Precedentes en 25/26/27 SUMMARIES + HARDENING_ROADMAP + decisions Items 7/8/9 + documentador reports.
- Patrón se copia al pie de la letra de tirón previo (item8/26 para item9/27 etc.). Ver root CLAUDE "Hardener Workflow" section + .claude/agents/ + ROADMAP.

## Ejemplo Correcto

```python
async def handle_balance(callback: CallbackQuery):
    """Solo llama al service."""
    user_id = callback.from_user.id
    with get_session() as session:
        service = BesitoService(session)
        balance = service.get_balance(user_id)
    await callback.message.edit_text(f"Tu saldo: {balance}")
```

## Ejemplo Incorrecto (PROHIBIDO)

```python
async def handle_balance(callback: CallbackQuery):
    user = await session.get(User, callback.from_user.id)
    user.besitos += 10          # ❌ Lógica de negocio
    await session.commit()      # ❌ Acceso a DB
```
