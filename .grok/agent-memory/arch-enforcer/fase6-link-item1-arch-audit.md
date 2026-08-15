# Arch Audit: Item 1 — Lucien emisor (Fase 6 link, Part A)

**Fecha:** 2026-08-15
**Repo:** /home/ubuntu/repos/lucienbot
**Commits auditados:** 0987068 (A1) → 2058cfd (A2) → f6e025f (A3) → 4afd702 (A4) → c499e08 (A5) → 1da4967 (docs)
**Diff acumulado:** `git diff 0987068~1..c499e08` (14 archivos, +384/-3)
**Verdict:** PASS WITH NOTES
**Critical violations:** 0

## Findings

### Critical (must fix before advance)
Ninguno.

### Medium
1. **`config/settings.py:21` — `LINK_CHAT_ID` crashea si la var existe pero vacía.**
   `LINK_CHAT_ID: int = int(os.getenv("LINK_CHAT_ID", "0"))`. Si el env var está presente con valor vacío — exactamente como lo documenta `.env.example` (`LINK_CHAT_ID=` vacío) — `int("")` lanza `ValueError` al importar `config.settings`. El bot NO arranca ni con `FEATURE_LINK_ENABLED=0`, violando el contrato "Flag OFF = idéntico" en el setup realista de copiar el example. Verificado con `LINK_CHAT_ID= python3 -c "import config.settings"` → ValueError.
   Fix concreto: `LINK_CHAT_ID: int = int(os.getenv("LINK_CHAT_ID") or "0")` (o parse defensivo try/except / solo cuando esté habilitado).

2. **Payload `vip_kicked` duplicado en 3 sitios emisores.**
   `bot.py:199-211`, `services/scheduler_service.py:238-250`, `services/vip_service.py:1065-1077` construyen el MISMO dict (mismas keys, mismo `int(datetime.now(UTC).timestamp())`). La regla non-negotiable "PROHIBIDO duplicación entre services" y el gold pattern de "pure helpers (verbo+contexto+resultado, stateless)" sugieren extraer un helper puro tipo `build_vip_kicked_payload(user_id, username, channel_id, channel_name, reason) -> dict`. Residual: no bloquea A1-A5 (el contrato del payload es idéntico en los 3), pero es el fix natural que también aliviaría el LOC de las 3 funciones.

### Minor
3. **Las 3 funciones editadas ya excedían 50 LOC (deuda pre-existente) y el ítem las creció.**
   - `bot.py:150-224` `check_expired_subscriptions_on_startup`: 63 → 75 LOC (pre-existente >50)
   - `services/scheduler_service.py:190-259` `_process_expired_subscriptions`: 58 → 70 LOC (pre-existente >50)
   - `services/vip_service.py:1010-1097` `admin_revoke_subscription`: 74 → 88 LOC (pre-existente >50)
   El ítem NO introdujo la violación (ya existían), pero el delta de ~13 líneas c/u las agranda. Se reporta como residual fuera del DoD (fix: extraer los bloques emit / #2 y/o el loop a helpers puros, siguiendo el gold de puros).

### Observations
4. **Posible emit duplicado por expiración** entre `check_expired_subscriptions_on_startup` (startup) y `_process_expired_subscriptions` (scheduler) si ambos procesan la misma suscripción. Es el mismo diseño dual pre-existente del ban/notificación; el emit paralelo es best-effort con `event_id` fresco → idempotente en efecto. No bloquea.
5. **Listener `on_vip_kicked` y router `business_connection` se registran SIEMPRE** (flag OFF = no-op). Consistente con la regla 6 (guard interno en handler, early-return en notifier, listener no-op). `_get_bot()` construye un `Bot(bot_config.TOKEN)` en la primera invocación incluso con flag OFF — inofensivo (no hace network, el early-return corta antes).

## Compliance Checklist

- [x] **Capas respetadas:** handlers → services → models. Handler llama exactamente 1 service (`LinkNotifier.upsert_business_connection`). Service accede a DB vía `models/database` (`SessionLocal`/`get_db_session` = capa correcta). 0 lógica de negocio en handlers.
- [x] **Handlers sin DB:** `rg SessionLocal|db.query|get_db handlers/` = 0 resultados.
- [x] **Funciones ≤50 en archivos nuevos:** `services/link_notifier.py` (todas ≤50: `_fetch_enabled_business_connection_id` 9, `upsert_business_connection` 22, `notify_vip_kicked` 41, `_get_bot` 7, `_get_link_notifier` 10, `on_vip_kicked` 9) y `handlers/business_connection_handlers.py` (8). Las 3 funciones pre-existentes >50 quedan como residual (#3).
- [x] **Naming verbo+contexto+resultado:** `upsert_business_connection`, `notify_vip_kicked`, `_fetch_enabled_business_connection_id`, `_get_link_notifier`, `on_vip_kicked`, `handle_business_connection`. Logging `link_notifier | upsert_business_connection | user_id=... | result=...` y `link_notifier | notify_vip_kicked | user_id=... | result=...` cumplen `módulo | acción | user_id | resultado`.
- [x] **3 sistemas sensibles intactos:** gamificación (besitos/reacciones/daily/misiones) no tocado; narrativa (progreso/arquetipos/FSM/quiz) no tocado; channels-VIP (pending/approve/expire/bans/subs + grant/revoke) — los 3 emits se agregaron POST-ban sin alterar la lógica de expulsión/ban/commit.
- [x] **Emits SOLO en branches de ban real + best-effort:** verificados los 3 sitios — `not_found`/`channel_inactive`/`deactivated_only` hacen return antes del emit; los emits corren tras `ban_chat_member` + commit, vía `schedule_emit` (nunca bloquea, nunca lanza).
- [x] **Atomicidad/EventBus/get_service protegidos:** emits post-commit (post-credit best effort); `EVENT_VIP_KICKED` nuevo sin mutar listeners; listener `on_vip_kicked` "MUST NOT mutate" (solo lee payload y envía best-effort). `get_service` no aplica (upsert es staticmethod sin sesión propia — sanción explícita del ítem).
- [x] **Flag OFF = idéntico:** guard interno en handler (`if not bot_config.FEATURE_LINK_ENABLED: return`), early-return en notifier (`if not self._enabled or self._chat_id is None: return`), listener no-op. EXCEPCIÓN: medium #1 (`LINK_CHAT_ID` vacío crashea al import).
- [x] **Contrato payload `[LINK]`:** `channel_name` desde `channel.channel_name` (Channel model lo tiene, NO `.name`); `username` con "@" agregado en UN solo punto (notifier: `f"@{raw_username}"`, los emisores pasan raw `user.username`); `ts` int unix (`int(datetime.now(UTC).timestamp())`).
- [x] **Sin voseo:** `.env.example` y logs nuevos en español neutro / formato módulo.
- [x] **Scope del PLAN respetado:** 14 archivos, todos A1-A5. Sin scope creep en los commits del ítem.
- [x] **Tests reflejan contratos:** `tests/unit/test_link_notifier.py` cubre flag OFF no envía, payload exacto `[LINK]`, `@` en username, swallow de errores, `event_id` fresco, fetch de bc id. 6 passed (verificado). `mock_bot` y `db_session` fixtures existen.

## Handoff
**test-guardian** — veredicto PASS WITH NOTES (0 critical). Las 2 medium y 1 minor son residuales (no bloquean A1-A5); el medium #1 (`LINK_CHAT_ID` vacío) tiene fix de 1 línea y sería bueno aplicarlo en el próximo ítem del pool o como follow-up antes de Part B.

## Residuales (fuera del DoD del ítem)
- `LINK_CHAT_ID` parse defensivo (`config/settings.py:21`) — fix 1 línea.
- Payload duplicado en 3 emisores → helper puro `build_vip_kicked_payload(...)` (también reduce LOC).
- 3 funciones pre-existentes >50 LOC crecidas por el ítem (deuda previa).
- Emit dual startup/scheduler (observación, diseño pre-existente).

## Fix Round Summary (gsd-executor, 2026-08-15)

Commit: `3fd7f02` fix(link): guard empty LINK_CHAT_ID and dedupe kick payload (6 archivos, +45/-26)

### Medium #1 — `LINK_CHAT_ID` crashea con var vacía → FIXED
`config/settings.py:21` → `LINK_CHAT_ID: int = int(os.getenv("LINK_CHAT_ID") or "0")`. Verificado: `LINK_CHAT_ID= python3 -c "import config.settings"` = OK (antes ValueError).

### Medium #2 — payload `vip_kicked` duplicado en 3 sitios → FIXED
Helper puro `build_vip_kicked_payload(user_id, username, channel_id, channel_name, reason) -> dict` en `services/link_notifier.py` (import `datetime`/`UTC`, convención del repo). Exportado en `services/__init__.py`. Reemplazados los 3 dicts inline manteniendo EXACTO el contrato:
- `services/vip_service.py` (branch kicked): `(subscription.user_id, user.username if user else None, channel.channel_id, channel.channel_name, "admin_revoke")`
- `services/scheduler_service.py` (branch expired): `(subscription.user_id, user.username if user else None, channel.channel_id, channel.channel_name, "expired")`
- `bot.py` (startup): `(user.telegram_id, user.username if user else None, channel.channel_id, channel.channel_name, "expired")`

`ts = int(datetime.now(UTC).timestamp())` ahora vive solo en el helper — misma expresión, mismo valor de contrato. No se tocaron branches `not_found`/`channel_inactive`/`deactivated_only`, ni la lógica de emisión (`schedule_emit` en la misma ubicación post-ban), ni sistemas sensibles.

### Verificación
- `LINK_CHAT_ID= python3 -c "import config.settings"` → OK; `python3 -c "import bot"` → OK; `services.build_vip_kicked_payload` importable.
- `rg -n "build_vip_kicked_payload" services/vip_service.py services/scheduler_service.py bot.py` → 3 usos + 3 imports.
- Directos: `tests/unit/test_link_notifier.py test_vip_service.py test_scheduler.py` → 95 passed, 3 xfailed.
- Smoke: `tests/unit/` → 746 passed, 10 xfailed (baseline idéntico, 0 regresiones).
- Ruff: 0 errores nuevos (5 pre-existentes en HEAD: 4x I001 + 1x SIM103).
