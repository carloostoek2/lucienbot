# Módulo de Gamificación - Lucien Bot

**Alcance:** Únicamente el módulo de gamificación (sistema de besitos, ingresos/gastos, interacciones actuales, broadcast con reacciones, regalo diario, y sus conexiones). Excluye detalles profundos de misiones/recompensas/store/narrativa/canales excepto las interacciones explícitas y flujos de economía. Misiones y Rewards se mencionan como fuentes de besitos y entregas cross-domain porque son el principal mecanismo de recompensas de gamificación.

**Dominio principal:** Gamificación (`BesitoService`, `DailyGiftService`, `BroadcastService` para reacciones). Economía de besitos (moneda virtual "💋"). Fuentes de ingreso (créditos), fuentes de gasto (débitos), atómica, historial inmutable, EventBus best-effort post-crédito.

**Arquitectura local:** `handlers/gamification_*` + `broadcast_handlers` (solo routing + UI + puros + 1 service call vía `get_service`) → servicios de dominio (`BesitoService` dueño de saldos/transacciones; `DailyGiftService` y `BroadcastService` delegan crédito local on-demand) → models (BesitoBalance, BesitoTransaction, TransactionSource, Reaction*, Broadcast*, DailyGift*). Cross-domain vía `deliver_reward` (local Besito) y `InternalEventBus` (post-commit "besitos_awarded").

**Entrypoint usuario:** Menú principal (balance, daily gift, reacciones vía callbacks de broadcast, historial). Admin: "admin_gamification" → config emojis/daily/manual grants + broadcast wizard.

---

## Módulos Principales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Handlers Usuario Gamif | `handlers/gamification_user_handlers.py` | Balance + stats (`get_service(BesitoService)`), historial transacciones, menú/claim regalo diario (`DailyGiftService`), handle reacciones (`BroadcastService.check_and_register_reaction` que hace crédito + missions best-effort). Puros: `calculate_emoji_counts_from_reactions`. |
| Handlers Admin Gamif | `handlers/gamification_admin_handlers.py` | Menú admin gamif, config besitos/emojis (BroadcastService), config daily gift amount/active (DailyGiftService), grants manual besitos (BesitoService), broadcast wizard entry. |
| Handlers Broadcast Wizard | `handlers/broadcast_handlers.py` | Wizard 8 pasos (canal vía ChannelService, texto, attachment, reacciones select, protected, confirm). Envío real vía bot.send_message (NO en service). Setup de BroadcastMessage + emojis. |
| BesitoService (core) | `services/besito_service.py` | Dueño de saldos y transacciones. `get_or_create_balance(lock=True)`, `get_balance`/`get_balance_with_stats`, `credit_besitos` (post-commit EventBus), `debit_besitos` (soporta `commit=False` para atomic callers), `has_sufficient_balance`, historial por usuario/fuente, top users, total circulación. |
| DailyGiftService | `services/daily_gift_service.py` | Config (amount, active, toggle), `can_claim` (24h cooldown), `claim_gift` (local BesitoService(db=...) **solo** dentro del crédito DAILY_GIFT + claim row atómico). Historial claims, stats hoy. |
| BroadcastService | `services/broadcast_service.py` | Emojis (CRUD + besito_value), registro BroadcastMessage (para stats), reacciones: `has_user_reacted`, `register_reaction` / `check_and_register_reaction` (lock + local Besito credit REACTION + commit + best-effort mission increment). NO envía broadcasts (eso es handler + TG API). |
| Integraciones cross (event + rewards) | `services/event_bus.py`, `services/reward_service.py`, `services/mission_service.py`, `services/story_service.py`, `services/store_service.py`, `services/game_service.py` | EventBus "besitos_awarded" (post credit), listeners observacionales (narrative, rewards, broadcast, game, store), deliver de rewards BESITOS (local credit MISSION), increment missions por tipo (REACTION_COUNT etc.), debits en store/story. |
| Modelos | `models/models.py` | `TransactionSource` (REACTION, DAILY_GIFT, MISSION, PURCHASE, ADMIN, ANONYMOUS_MESSAGE, GAME, TRIVIA, STREAK_PROTECTION), `TransactionType` (CREDIT/DEBIT), `BesitoBalance` (balance + total_earned/spent), `BesitoTransaction` (inmutable), ReactionEmoji/BroadcastMessage/BroadcastReaction, DailyGiftConfig/Claim. |

**Notas de construcción (Hardener Items 1/5/6/10 + tirones relacionados):**
- **Locals on-demand BesitoService(db=self.db)** *solo* dentro de sitios de crédito/débito en otros servicios (broadcast reaction, daily claim, reward _deliver_besitos, store complete/purchase, game play_*, streak) — preserva atomicidad de la tx del composer + besito tx + log + best-effort post (missions, schedule_emit, listeners). 0 impacto en contratos de crédito.
- **EventBus observers** (narrative primero, luego rewards + broadcast + game + store): puramente best-effort, "MUST NOT credit/debit/mutate besitos", log "dominio | besitos_awarded_received | ...", ownership del dominio listener (no en gamif). Central reg explícito en bot.py on_startup.
- Handlers: `with get_service(XXXService) as svc:` (exact 1), puros para cálculos UI (ej. emoji counts), logging estándar, IdempotencyMiddleware global para reactions.
- `credit_besitos` extrae `_schedule_besitos_awarded_event` para mantenerse ≤50 LOC.
- Tests gold: `test_cross_service_atomicity.py` ("credit survives deliver False" + post-credit best effort), reaction full chains, daily atomic, game play, patch schedule_emit + TestSession + N806 + 777 + gather return_exceptions.
- 3 critical systems protegidos: gamif como fuente de créditos, missions/rewards atómicos vía locals, narrative como listener.

---

## Modelos Clave (extracto)

```python
class TransactionSource(enum.StrEnum):
    REACTION = "reaction"
    DAILY_GIFT = "daily_gift"
    MISSION = "mission"
    PURCHASE = "purchase"
    ADMIN = "admin"
    ANONYMOUS_MESSAGE = "anonymous_message"
    GAME = "GAME"
    TRIVIA = "TRIVIA"
    STREAK_PROTECTION = "streak_protection"

class TransactionType(enum.StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"

class BesitoBalance(Base):
    user_id (BigInteger unique), balance, total_earned, total_spent
    # relations: transactions

class BesitoTransaction(Base):
    user_id (FK), amount (pos para credit, neg para debit), type, source (Enum TransactionSource),
    description, reference_id, created_at
    # inmutable (nunca update/delete)

# Broadcast / Reactions
class ReactionEmoji: emoji, name, besito_value (configurable), is_active
class BroadcastMessage: message_id (TG), channel_id (TG FK), admin_id, text, has_reactions, is_protected, selected_emoji_ids
class BroadcastReaction: broadcast_id, user_id, reaction_emoji_id, besitos_awarded

# Daily
class DailyGiftConfig: besito_amount, is_active
class DailyGiftClaim: user_id, besitos_received, claimed_at
```

**Reglas negocio core:**
- Nunca saldos negativos (check en debit + rollback lock).
- Transacciones atómicas (lock FOR UPDATE, commit controlado).
- Historial inmutable (solo insert).
- Logging por acción: "módulo | acción | user_id | resultado" (incluye source.value).
- 1 reacción por usuario por broadcast message (has_user_reacted + unique constraint).

**Dualidad / IDs:** Broadcast usa channel_id (TG id) para mensajes; reacciones ref broadcast.id interno. Recompensas ref reward.id etc.

---

## BesitoService — API Principal (Dueño de la Economía)

### Saldos
- `get_or_create_balance(user_id, lock: bool = False) -> BesitoBalance` (with_for_update si lock).
- `get_balance(user_id) -> int`
- `get_balance_with_stats(user_id) -> dict` (balance, total_earned, total_spent)
- `has_sufficient_balance(user_id, amount) -> bool`

### Crédito / Débito (core economy)
- `credit_besitos(user_id, amount (>0), source: TransactionSource, description=None, reference_id=None) -> bool`
  - Lock, += balance + total_earned, insert CREDIT tx, commit, **post-commit** `_schedule_besitos_awarded_event` (best effort via schedule_emit + bus.emit con gather return_exceptions; nunca afecta retorno ni causa rollback).
  - Payload: {"user_id", "amount", "source": .value, "reference_id", "description", "timestamp": ISO}.
- `debit_besitos(user_id, amount (>0), source, description=None, reference_id=None, commit: bool = True) -> bool`
  - Lock, check suficiente (warning + rollback si no), -= balance + total_spent, insert DEBIT tx (amount negativo), commit si flag, retorna bool.
  - `commit=False` permite atomicidad con caller (ej. story advance + progreso).

### Historial y Stats
- `get_transaction_history(user_id, limit=20)`
- `get_transactions_by_source(user_id, source, limit)`
- `get_top_users(limit=10)`
- `get_total_besitos_in_circulation()`

**Uso interno:** Siempre vía local on-demand en otros dominios para atomicity.

---

## Fuentes de Ingreso para el Usuario (Créditos de Besitos)

Todas usan `credit_besitos(..., source=..., reference_id=...)`. Listadas por TransactionSource + caller principal:

1. **DAILY_GIFT** (`daily_gift_service.claim_gift`):
   - Configurable (default 10, admin puede cambiar).
   - 24h cooldown por usuario (`can_claim` calcula timedelta).
   - Registra DailyGiftClaim + crédito atómico.
   - UI: "daily_gift" menu → claim.

2. **REACTION** (`broadcast_service.register_reaction` / `check_and_register_reaction`):
   - Por cada reacción a broadcast (1x por usuario por mensaje — enforced).
   - Valor = `ReactionEmoji.besito_value` (configurable por admin, default 1).
   - Descripción: "Reacción con {emoji}".
   - Además: incrementa misiones REACTION_COUNT (best effort post).
   - UI: callbacks ReactionCallback en mensajes broadcast (actualiza markup con counts vía puro `calculate_emoji_counts_from_reactions`).

3. **MISSION** (`reward_service._deliver_besitos` — llamado desde deliver_reward tras completar misión):
   - Recompensas de tipo BESITOS creadas por admin (tariff/reward_id asociada a misión).
   - `credit(..., source=MISSION, description="Recompensa: {name}", reference_id=reward.id)`.
   - Misiones se incrementan automáticamente por tipo (REACTION_COUNT desde broadcast, DAILY_GIFT_STREAK etc. desde daily, STORE_PURCHASE, VIP_ACTIVE, etc.).
   - Ver missions/CLAUDE para tipos y `increment_progress` / `increment_progress_and_deliver`.

4. **GAME** (`game_service` play_* wins + streak bonus):
   - Victorias en minijuegos (dados etc.).
   - Bonos por rachas.
   - Múltiples sitios de crédito GAME.

5. **TRIVIA** (`game_service` / trivia paths):
   - Respuestas correctas en trivias.
   - Múltiples TRIVIA credits.

6. **ADMIN** (manual grants en `gamification_admin_handlers` / config besitos):
   - Ajustes manuales por custodios (source=ADMIN).

7. **ANONYMOUS_MESSAGE**, **STREAK_PROTECTION**:
   - Presentes en enum. Usados para interacciones VIP anon (posiblemente costo/recompensa) y protección de rachas (puede ser gasto o award).

**Estadísticas:** Balance trackea total_earned (acumula todos los ingresos). Historial filtra por source. Top users por balance.

---

## Fuentes de Gasto para el Usuario (Débitos de Besitos)

Usan `debit_besitos(..., source=..., commit=...)` (a menudo con check previo via has_sufficient).

1. **PURCHASE** (`store_service` complete_order, direct_purchase, create_order):
   - Compras en tienda (productos/paquetes).
   - Debit con source=PURCHASE, descripción "Compra en tienda - Orden #..", ref=order.id.
   - Pre-checks de saldo + recheck en complete (local Besito debit).
   - Observador store en besitos_awarded (best effort).

2. **Avances de narrativa** (`story_service.advance_to_node`):
   - Costo de besitos para progresar nodos (ej. 50 besitos en algunos).
   - Llama debit con `commit=False` para atomicidad con save de UserStoryProgress.
   - Tests verifican el flag commit=False.

3. **Mensajes anónimos VIP** (`vip_user_handlers`):
   - Costo para enviar susurros anónimos a Diana.
   - Debit besitos.

4. **Streak protection** (`streak_promotion_service`):
   - Compras de protección de racha (debits).

Otras posibles: fees internos o features futuras.

**Control:** Siempre verifica `has_sufficient_balance` antes; rollback en insuficiente. Balance nunca negativo.

---

## Broadcast y Reacciones (Interacción Principal de Gamificación)

**Flujo admin (broadcast_handlers.py — wizard 8 pasos):**
- Seleccionar canal (usa ChannelService.get_all_channels internamente).
- Texto, attachment (photo/video/doc), ¿reacciones? (selecciona emojis activos), ¿protegido? (no reenviar).
- Confirma → envía via bot.send_message (directo en handler) + registra BroadcastMessage en service.
- Mensaje con teclado de reacciones (si has_reactions).

**Flujo usuario (gamification_user + broadcast handlers callbacks):**
- Reacciona (ReactionCallback) → `BroadcastService.check_and_register_reaction` (atomic: insert reaction + local credit REACTION + commit).
- Si éxito: +besitos toast, actualiza markup con counts (puro calculate + get_reactions_by_broadcast + update_reaction_message).
- 1 reacción por msg (has + unique constraint).
- Además incrementa misiones REACTION_COUNT (en check_and_register: separate try para best effort deliver).

**Admin config (gamif_admin + broadcast service):**
- CRUD ReactionEmoji (emoji, besito_value, active).
- Ver broadcasts recientes, stats.

**BroadcastService NO hace el envío** — solo tracking + reacciones + emojis. (Ver broadcast/CLAUDE.md).

---

## Regalo Diario

- Config global (DailyGiftConfig: amount, is_active) editable por admin.
- Por usuario: DailyGiftClaim (último claim).
- `can_claim`: activo? + 24h desde last_claimed_at (aware UTC handling).
- `claim_gift`: si ok → insert claim + local Besito.credit DAILY_GIFT (dentro try, commit conjunto) → mensaje con nuevo saldo.
- UI en gamification_user: menú muestra available/remaining time.
- Stats admin: claims y besitos dados hoy.

---

## Cómo se Otorgan los Besitos (Flujo Técnico General)

1. Caller (daily claim, reaction handler, reward deliver, game win, etc.) decide fuente + amount + ref.
2. Obtiene o crea BesitoService local (db compartida) **solo** en el sitio de crédito.
3. `credit_besitos`:
   - Valida amount > 0.
   - Lock balance (FOR UPDATE).
   - Actualiza balance + total_earned.
   - Inserta tx CREDIT.
   - commit().
   - schedule_emit( bus.emit(EVENT_BESITOS_AWARDED, payload) ) — best effort, nunca falla crédito.
4. Retorna True/False. Caller continúa (ej. misiones best effort, UI update, log).
5. Para débitos: similar + check suficiente + amount negativo en tx + total_spent. Soporta commit=False.

**Atomicity gold:** La tx del composer (reaction row + credit commit + mission best effort) sobrevive fallos parciales en listeners/post. "credit survives deliver False".

---

## Mapa de Gamificación (Diagrama de Economía e Interacciones)

```
Usuario
  │
  ├── INGRESOS (créditos BesitoService)
  │   ├── DailyGiftService.claim → DAILY_GIFT (24h, config amount)
  │   ├── Broadcast reactions → REACTION (1x/msg, emoji value configurable)
  │   │     + increment REACTION_COUNT missions
  │   ├── Missions completadas → RewardService.deliver → BESITOS (MISSION source)
  │   │     (o PACKAGE o VIP_ACCESS)
  │   ├── Games/Trivia → GAME / TRIVIA (wins + streaks)
  │   └── Admin manual → ADMIN
  │
  ├── GASTOS (débitos BesitoService)
  │   ├── Store purchases → PURCHASE (atomic en complete_order)
  │   ├── Story advances → debit (commit=False + progreso narrativo)
  │   ├── VIP anon messages
  │   └── Streak protection
  │
  ├── ESTADÍSTICAS
  │   └── BesitoBalance (balance + total_earned/spent), historial inmutable por source
  │
  └── CROSS-DOMAIN
      ├── EventBus (post-credit best-effort)
      │   └── "besitos_awarded" → listeners observacionales:
      │       narrative (log + futuro hints/progreso; MUST NOT mutate besitos)
      │       rewards (observational)
      │       broadcast/game/store (observational, no re-entrancy)
      │
      ├── Misiones (conectan todo)
      │   increment por tipo (reaction/daily etc.) → complete → deliver_reward (besitos/VIP/package)
      │
      ├── Canales (administración)
      │   Gamif (VIP rewards) → VIPService.redeem → Subscription a Channel VIP
      │   (canales registrados vía channel admin; broadcasts se envían a ellos)
      │
      └── Narrativa
          ├── VIP gates en nodos (is_vip de subs que gamif puede otorgar vía rewards)
          ├── Debita besitos para avanzar nodos (atomic con progreso)
          └── Recibe evento besitos_awarded (best effort) + puede credit por logros
```

**Loops:** Earn (daily/reaction/mission) → Spend (store/story) → Progress missions → More rewards (incl. VIP → channels access + narrative content) → Más earns vía EventBus triggers.

**Separación:** Gamif (Besito core) no llama directamente a ChannelService ni StoryService. Conexiones son a través de Rewards (VIP) y EventBus (observational) + débitos/credits explícitos controlados en story.

---

## Conexión con Administración de Canales

- **Indirecta principal:** Recompensas de misiones de tipo VIP_ACCESS (creadas en reward_admin, entregadas vía gamif missions) → `VIPService.redeem_token` → busca Channel VIP activo (registrado y configurado en el módulo de canales) → crea Subscription (channel_id = DB PK del canal).
- Efecto: ganar misiones gamificadas da acceso a canales VIP (círculo de Diana).
- Broadcasts (parte de gamif) se envían a canales registrados (broadcast wizard usa ChannelService para listar targets free/vip).
- Free channels son independientes (no requieren besitos); VIP channels gated por subs que la gamif puede proveer vía rewards.
- 0 llamadas directas Besito/Broadcast/Daily → ChannelService. Salud de canales (pending counts) en analytics admin usa ChannelService por separado.
- Health observa canales pero sin mutar besitos.

---

## Conexión con Narrativa

- **EventBus (dirección gamif → narrative):** Todo `credit_besitos` exitoso emite "besitos_awarded" (payload completo + source). Listener `on_besitos_awarded_from_gamification` en story_service (ownership narrative): loguea recepción ("narrative | besitos_awarded_received | ..."), best-effort, **MUST NOT** llamar credit/debit besitos (evita loops — _grant_achievement ya hace créditos de logros). Registrado central en bot.py. Errores tragados por bus.
- **Dirección narrativa → gamif:** `StoryService` mantiene ref a besito_service (injected). 
  - `advance_to_node`: debita besitos (con `commit=False` para atomicidad con UserStoryProgress), source=PURCHASE? (en algunos paths) o interno.
  - Posibles créditos por logros/achievements.
- **Gates VIP:** Nodos con `required_vip=True` requieren membresía (is_vip chequeado en can_access_node). Membresías VIP se otorgan vía gamif (recompensas misiones VIP → channels).
- **Achievements / progreso:** Narrativa puede disparar rewards (besitos) de vuelta al ecosistema gamif.
- 0 mutación de besitos en listeners del bus. 0 acoplamiento directo handlers/story con Besito core excepto los sitios controlados en story_service.
- Narrativa también usa besitos para "fragmentos" pagos.

---

## Interacciones Actuales y Flujos Clave

- **Reacción → besitos + misión:** Usuario reacciona → BroadcastService (local credit REACTION) → mission increment REACTION_COUNT → posible deliver_reward (más besitos o VIP).
- **Misión completa → recompensa:** User ve misiones (mission_user_handlers) → claim → RewardService.deliver → si BESITOS: local credit MISSION.
- **Daily → besitos:** Claim → credit DAILY_GIFT + claim row.
- **Broadcast admin wizard:** 8 pasos + envío TG + registro + setup reacciones.
- **Admin grants/config:** Emojis values (afecta ingresos por reacción), daily amount, manual besitos (ADMIN source), toggle daily.
- **Store spend:** Seleccionar → verificar saldo (Besito) → debit PURCHASE atómico.
- **Story progress:** Avanzar nodo → debit (atomic) + progreso + posible event.
- **Event post-earn:** Cualquier crédito → narrative/rewards/etc. observan (log + potential future logic sin mutar).

**UI/UX voz Lucien:** "fragmentos de atención", "besitos", "Diana aprecia...", toasts "+X besitos! 💋".

---

## Reglas, Patrones y Gotchas

- **Handlers:** Exactly 1 service por entry (Besito/Daily/Broadcast vía get_service). Puros para UI (counts, formatting). IdempotencyMiddleware para reactions. Logging completo.
- **Locals only inside credit/debit sites:** Patrón hardener probado (Items 5/6/10). Preserva atomicity + "credit survives" + post best-effort.
- **EventBus contract:** Post-commit only, schedule_emit para sync callers, gather return_exceptions, no exceptions al emisor, listeners "MUST NOT mutate besitos", ownership en dominio listener.
- **Fuentes siempre via Enum:** Nunca strings mágicos. Usar TransactionSource.XXX.
- **Cooldowns y guards:** Daily 24h, 1 reacción/msg, saldo suficiente antes de debit.
- **Historial inmutable + stats:** Totales en Balance para reportes (circulación, top earners/spenders).
- **Tests:** Golds protegen atomicity cross (reaction→credit→mission, daily, store debit, game, story debit commit=False, event emit). Re-runs post any change a besito paths.
- **No duplicación:** BesitoService es el único lugar para mutar saldos/tx. Otros dominios solo llaman localmente para sus flujos.
- **Antes de tocar:** Leer services/gamification/CLAUDE.md, broadcast/CLAUDE.md, missions/CLAUDE.md, services/CLAUDE.md (EventBus + Item details), handlers/CLAUDE.md (patrón puros + 1svc), event_bus.py, y tests atómicos/cross.

**Fin del documento — solo módulo de gamificación.**

Construido con: BesitoService como única fuente de verdad económica, locals on-demand para atomicity, EventBus observacional para desacoplamiento (narrative/rewards/etc.), missions como "pegamento" que convierte acciones gamificadas en rewards (besitos + VIP para canales + progreso narrativo), puros + get_service en handlers, logging y guards estrictos. Fuentes de ingreso/gasto completamente mapeadas vía TransactionSource + callers reales.