# Lucien Engagement Layer — Diseño Conceptual Consolidado

> **Estado:** Aprobado para implementación  
> **Origen:** Rediseño profundo de la expansión original (Fases 17-22) adaptado a la arquitectura actual de Lucien Bot  
> **Fecha de diseño:** 2026-04-15

---

## 1. Principios Rectores (non-negotiable)

1. **Una sola economía** → Besitos como única moneda. Sin "Atención", "Fantasía" ni monedas paralelas.
2. **Extensión, no reemplazo** → Todo vive dentro de `Services` existentes. No se crean nuevos services.
3. **Anonimato absoluto** → Sin interacción ni exposición entre usuarios.
4. **VIP vs Free como motor de negocio** → Cada mecánica responde: ¿qué gana un VIP?
5. **Complejidad progresiva** → Capas ligeras, no sistemas paralelos.
6. **Integración profunda** → Cada acción avanza `MissionService` y cada recompensa pasa por `RewardService.deliver_reward()`.

---

## 2. Arquitectura Base

| Mecánica | Service a extender |
|---|---|
| Ritmo Diario + Pasivo | `DailyGiftService` |
| Senderos Narrativos | `StoryService` |
| Susurros de Diana | `RewardService` |
| Misiones dinámicas | `MissionService` |
| Economía (besitos) | `BesitoService` (solo métodos transaccionales) |

**Regla de oro:** No se crean nuevos services. Solo extensiones controladas.

---

## 3. Núcleos del Sistema

### I. Ritmo Diario + Sistema Pasivo (Retención Base)

**Objetivo psicológico:** FOMO diario. El usuario siente que "está dejando besitos en la mesa" si no entra.

**Mecánicas:**
- Reclamo diario (base).
- Racha acumulativa (multiplicador).
- Generación pasiva offline (VIP).

**Funcionamiento:**
- El usuario entra y reclama en una sola acción (daily + pasivo acumulado).
- La racha multiplica TODO el reclamo.
- Si la racha se rompe (>48h), se resetea. VIP puede recuperarla 1 vez al mes.

**Diferenciación:**

| Feature | Free | VIP |
|---|---|---|
| Base | `base_amount` (ej. 10) | `base_amount × 2` (ej. 20) |
| Racha | +10% por día, tope +50% | +20% por día, tope +100% |
| Pasivo offline | 8h cap (ej. 8 besitos) | 24h cap (ej. 24 besitos) |
| Recuperación de racha | No | 1 vez/mes |

**Implementación:**
- `DailyGiftService` se extiende con `get_ritmo_status()` y `claim_ritmo()`.
- Calcula pasivo on-the-fly (`min(horas_offline, cap) × tasa`). No se persiste "besitos pendientes".
- Llama a `BesitoService.credit_besitos(source=TransactionSource.DAILY_GIFT)`.
- Dispara `MissionService.increment_progress_and_deliver()` para `DAILY_GIFT_TOTAL` y `DAILY_GIFT_STREAK`.

**Modelos:**
- `DailyGiftStreak` (nuevo): racha, última fecha de reclamo, recuperaciones usadas.

---

### II. Senderos Narrativos + Descubrimiento (Engagement Emocional)

**Objetivo psicológico:** Progresión emocional en el mundo de Diana sin construir un RPG complejo.

**Mecánicas:**
- Senderos curados de 3-5 nodos usando `StoryNode`/`StoryChoice` existentes.
- Decisiones ligeras que avanzan el sendero.
- Nodos de descubrimiento desbloqueables por racha o besitos acumulados.

**Funcionamiento:**
- Usuario entra a un sendero disponible.
- Avanza nodo por nodo usando `StoryService.advance_to_node()` internamente (arquetipos, costos y logros normales).
- Al completar el sendero, recibe recompensa vía `RewardService.deliver_reward()`.

**Diferenciación:**

| Feature | Free | VIP |
|---|---|---|
| Acceso | 1 "Sendero del Día" | Sendero del Día + exclusivos semanales |
| Intentos | 1 por sendero | Ilimitados |
| Recompensas | Estándar | 2x besitos + chance de paquete exclusivo |
| Descubrimientos | Básicos | Exclusivos |

**Nodos de descubrimiento:**
- Extensión de `StoryNode` con campos opcionales:
  - `unlock_required_streak` (nullable)
  - `unlock_required_besitos_total` (nullable)
- `StoryService.can_access_node()` los evalúa junto a `required_vip` y `cost_besitos`.

**Implementación:**
- `StoryService` se extiende con `list_available_paths()`, `start_path()`, `advance_path()`.
- Dispara `MissionService.increment_progress_and_deliver(MissionType.STORY_NODE_VISIT)`.

**Modelos:**
- `StoryPath` (nuevo): secuencia de IDs de `StoryNode`, recompensa, flags VIP, fechas válidas, límite de intentos.
- `UserStoryPathProgress` (nuevo): índice de nodo actual, intentos usados, estado completado.

---

### III. Misiones Dinámicas (Motor de Actividad)

**Objetivo psicológico:** Cada día hay 3+ misiones frescas que guían al usuario por el loop de engagement.

**Mecánicas:**
- 3 misiones diarias rotativas generadas automáticamente.
- 1 misión de conexión siempre presente (reclamar Ritmo).
- Tipos: volver al bot, reclamar reward, avanzar sendero, reclamar susurro.

**Diferenciación:**

| Feature | Free | VIP |
|---|---|---|
| Recompensas | Base | +50% |
| Misiones extras | No | 1 misión exclusiva ocasional |

**Implementación:**
- Nuevo modelo `MissionTemplate`: plantillas preconfiguradas por los Custodios con `mission_type`, `target_value`, `reward_id`, `weight`, `is_vip_exclusive`.
- Scheduler diario (`generate_daily_missions()`) selecciona templates aleatorios y crea `Mission` rows `RECURRING` con `cooldown_hours=24`.
- No se generan rewards dinámicamente desde código: cada template apunta a un `Reward` existente.

---

### IV. Susurros de Diana + Recompensas Misteriosas (Dopamina controlada)

**Objetivo psicológico:** Recompensa sorpresa diaria que mantiene la anticipación y la conversión.

**Mecánicas:**
- 1 (Free) o 2 (VIP) susurros gratis al día.
- Selección aleatoria ponderada desde pools de `Reward` existentes.
- Sin sistema de pity. Simple `random.choices()` por peso.

**Diferenciación:**

| Feature | Free | VIP |
|---|---|---|
| Susurros/día | 1 | 2 |
| Pool | `free_daily` | `vip_daily` |
| Drops típicos | 80% besitos, 15% paquete pequeño, 5% VIP temporal | Mejores montos, 35% paquetes exclusivos |

**Implementación:**
- `RewardService` se extiende con `can_claim_whisper()` y `claim_whisper()`.
- Entrega **obligatoriamente** por `RewardService.deliver_reward()`.
- Dispara `MissionService.increment_progress_and_deliver(MissionType.WHISPER_CLAIM)`.

**Modelos:**
- `WhisperRewardPool` (nuevo)
- `WhisperRewardItem` (nuevo): `reward_id` + `weight`
- `WhisperClaim` (nuevo): log diario por usuario

**Bolsas en tienda (futuro):**
- Producto `StoreProduct` especial que al comprar dispara `claim_whisper()`.
- **Fase 6 (post-MVP).** No entra en las primeras 5 fases.

---

### V. Estadísticas Anónimas (Psicología sin toxicidad)

**Objetivo psicológico:** Sentido de progreso relativo sin exponer identidades ni rankings exactos.

**Mecánicas:**
- Percentiles suaves: "Estás en el top 20% de visitantes esta semana".
- Comparativas en racha, besitos totales y misiones completadas.

**Reglas:**
- Sin leaderboard.
- Sin nombres.
- Sin ranking numérico exacto.

**Implementación:**
- `BesitoService.get_percentile(user_id)` — consulta simple contra `BesitoBalance`.
- `MissionService.get_percentile(user_id)` — consulta simple contra `UserMissionProgress`.

---

## 4. Loop Central del Usuario

```
1. Entra al bot
2. Reclama Ritmo Diario + pasivo
3. Ve progreso de racha + percentil
4. Realiza 1 sendero narrativo
5. Reclama 1 susurro
6. Consulta misiones diarias y las completa
7. Recibe recompensas acumuladas
8. Encuentra límite VIP → fricción controlada → nudge de conversión
```

---

## 5. Modelo de Datos (Mínimo Viable)

### Nuevas tablas (7)

1. `DailyGiftStreak`
2. `MissionTemplate`
3. `StoryPath`
4. `UserStoryPathProgress`
5. `WhisperRewardPool`
6. `WhisperRewardItem`
7. `WhisperClaim`

### Extensiones a tablas existentes

- `StoryNode`: `unlock_required_streak`, `unlock_required_besitos_total`

### Enums a extender (migraciones enum-first obligatorias)

**`TransactionSource`:**
- `STORY_PATH`
- `WHISPER`

**`MissionType`:**
- `STORY_NODE_VISIT`
- `WHISPER_CLAIM`
- `STREAK_RECOVER`

---

## 6. Handlers (Puros, 1 Service Call)

### Nuevo archivo: `handlers/engagement_user_handlers.py`

| Handler | Callback | Service Call |
|---|---|---|
| `ritmo_menu` | `ritmo_diario` | `DailyGiftService.get_ritmo_status()` |
| `ritmo_claim` | `claim_ritmo` | `DailyGiftService.claim_ritmo()` |
| `senderos_menu` | `senderos_espejo` | `StoryService.list_available_paths()` |
| `senderos_start` | `start_path_{id}` | `StoryService.start_path()` |
| `senderos_advance` | `advance_path_{choice_id}` | `StoryService.advance_path()` |
| `susurros_menu` | `susurros_diana` | `RewardService.can_claim_whisper()` |
| `susurros_claim` | `claim_whisper` | `RewardService.claim_whisper()` |
| `percentil_menu` | `mi_percentil` | `BesitoService.get_percentile()` / `MissionService.get_percentile()` |

### Nuevo archivo: `handlers/engagement_admin_handlers.py`

- Configuración de Ritmo (base, multiplicadores, caps).
- CRUD de `MissionTemplate`.
- CRUD de `StoryPath` (selección de nodos existentes).
- CRUD de `WhisperRewardPool` y pesos.

**Regla:** Cero lógica de negocio en handlers.

---

## 7. Roadmap de Implementación (GSD)

### Fase X — Ritmo Diario + Pasivo + Rachas
> Impacto inmediato en retención.
- Migraciones enum + tablas.
- `DailyGiftStreak`.
- Extensión `DailyGiftService`.
- Handler de Ritmo.
- Percentil básico de racha.

### Fase 18 — Misiones Dinámicas Diarias
> Aumenta actividad diaria guiada.
- `MissionTemplate`.
- Scheduler job `generate_daily_missions()`.
- Integración con flujo de misiones existente.

### Fase 19 — Senderos Narrativos + Descubrimiento
> Engagement emocional profundo.
- `StoryPath`, `UserStoryPathProgress`.
- Extensión `StoryService`.
- Nodos desbloqueables por racha/besitos.
- Admin y user handlers.

### Fase 20 — Susurros de Diana
> Dopamina controlada y conversión VIP.
- `WhisperRewardPool`, `WhisperRewardItem`, `WhisperClaim`.
- Extensión `RewardService`.
- Nudges de conversión VIP en cada límite.

### Fase 21 — Percentiles Anónimos + Pulido
> Retención psicológica sin toxicidad.
- Percentiles en besitos y misiones.
- Recuperación de racha VIP.
- Tests, optimización de queries, ajustes de balance.

### Fase 22 (Futuro) — Bolsas en Tienda
- Mystery boxes como `StoreProduct` especial.
- No entra en el MVP inicial.

---

## 8. Archivos a Modificar / Crear

### Modificar
- `models/models.py`
- `services/daily_gift_service.py`
- `services/mission_service.py`
- `services/story_service.py`
- `services/reward_service.py`
- `services/besito_service.py`
- `services/scheduler_service.py`
- `keyboards/inline_keyboards.py`
- `handlers/gamification_user_handlers.py`
- `handlers/gamification_admin_handlers.py`
- `bot.py`

### Crear
- `handlers/engagement_user_handlers.py`
- `handlers/engagement_admin_handlers.py`
- Alembic migrations (enum-first, luego tablas)

---

## 9. Resultado Esperado

- Sistema cohesivo (no Frankenstein).
- Retención diaria medible.
- Motivación constante sin saturar al usuario.
- Conversión VIP orgánica mediante fricciones claras.
- Escalable sin romper la arquitectura establecida.

---

*Diseñado por Lucien para Diana. 🎩*
