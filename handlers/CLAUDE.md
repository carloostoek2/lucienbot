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

1. **UN service** por handler
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos

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
