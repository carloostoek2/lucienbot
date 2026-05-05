```markdown
# Sistema de Trivias y Promociones por Racha — Documento Técnico y Operativo Unificado

**Versión consolidada**  
Fusiona los dos reportes (`contexto1.txt` y `contexto2.txt`) en un único documento completo, sin contradicciones ni omisiones.

---

## 1. Resumen General

El sistema permite a los usuarios participar en **trivias diarias** y acumular **rachas** de respuestas correctas. Al alcanzar determinados umbrales (**tiers**), se generan códigos de descuento (`TRI-XXXXXX`) canjeables en la tienda.

```
Pregunta correcta → +1 racha → Tier alcanzado → Código generado
Pregunta incorrecta → Racha reiniciada → Código activo INVALIDADO (CANCELLED)
```

**Dos dimensiones orthogonales:**
1. **Trivias** — Preguntas diarias con límites configurables (globales).
2. **Promociones por Racha** — Configuraciones que vinculan rachas específicas con % de descuento.

---

## 2. Modelos Principales

### 2.1 `TriviaConfig` (Singleton global)
```python
class TriviaConfig(Base):
    daily_trivia_limit_free      # default: 7
    daily_trivia_limit_vip       # default: 15
    daily_trivia_vip_limit       # VIP exclusivo, default: 5
```

### 2.2 `QuestionSet`
```python
class QuestionSet(Base):
    name: str              # ej: "San Valentín 2026"
    file_path: str         # ruta al JSON de preguntas
    description: str
    is_active: bool
    is_override: bool      # True = reemplaza completamente los sets por defecto
```

### 2.3 `TriviaPromotionConfig` (Núcleo del sistema)
```python
class TriviaPromotionConfig(Base):
    name: str
    promotion_id: int | None          # FK → Promotion (nullable = promoción independiente)
    custom_description: str

    status: str                       # active | paused | expired | completed
    is_active: bool
    discount_percentage: int          # % base (single-tier)
    required_streak: int              # mínimo 3

    max_codes: int
    codes_claimed: int

    # Vigencia fija
    start_date: datetime
    end_date: datetime

    # Vigencia relativa
    duration_minutes: int | None
    started_at: datetime | None

    # Auto-reset
    auto_reset_enabled: bool
    reset_count: int
    max_reset_cycles: int | None

    question_set_id: int | None       # FK → QuestionSet (tema específico)
    discount_tiers: str | None        # JSON: [{"streak": 5, "discount": 50}, ...]
```

### 2.4 `DiscountCode`
```python
class DiscountCode(Base):
    config_id: int                    # FK → TriviaPromotionConfig
    code: str                         # TRI-XXXXXX (único)
    user_id: BigInteger
    username: str
    first_name: str
    promotion_id: int | None

    status: DiscountCodeStatus        # ACTIVE | USED | EXPIRED | CANCELLED
    generated_at: datetime
    used_at: datetime | None
    discount_percentage: int          # % real del tier alcanzado
```

### 2.5 `GameRecord`
Registra cada partida de trivia:
- `game_type`: `'trivia'` | `'trivia_vip'` | `'dice'`
- `discount_code_id`: FK nullable (vincula con código generado al alcanzar tier)

**Límites diarios**: Se cuentan registros de `GameRecord` por usuario + `game_type` + día UTC.

### 2.6 `Promotion`
Puede estar vinculada a `TriviaPromotionConfig` y/o a un `QuestionSet`.

---

## 3. Flujo Completo del Usuario

1. **Entrada** → `game_trivia` → `GameService.get_trivia_entry_data()`
   - Muestra racha actual, próximo umbral, tiempo restante de promoción, intentos diarios restantes.

2. **Respuesta** → `trivia_answer` → `GameService.play_trivia()`
   - Preguntas cargadas desde JSON (`docs/preguntas.json` por defecto o `QuestionSet` activo).

3. **Lógica de racha**:
   - **Correcta** → `streak += 1`
     - Si alcanza tier intermedio → modo `streak_continue` (teclado: “Continuar” / “Salir”)
     - Si alcanza tier final → código generado automáticamente con el descuento máximo del tier.
   - **Incorrecta** → `streak = 0` + `invalidate_streak_code()` (código activo → CANCELLED).

4. **Besitos ganados**:

| Tipo              | Besitos por respuesta correcta |
|-------------------|--------------------------------|
| Trivia FREE       | 1                              |
| Trivia VIP        | 5                              |

**Límites diarios**:
- Free: 7
- VIP: 15 + 5 (VIP exclusivo)

---

## 4. Wizard de Creación de Promoción por Racha (Admin)

**Archivo:** `handlers/trivia_discount_admin_handlers.py`  
**FSM:** `TriviaDiscountStates` (17 estados)

| Paso | Estado FSM                      | Acción |
|------|---------------------------------|--------|
| 1    | waiting_promotion_type          | Promo existente o independiente |
| 2    | waiting_promotion / waiting_custom_description | Selección o descripción |
| 3    | waiting_discount_percentage     | % de descuento (0-100) |
| 4    | waiting_required_streak         | Racha mínima (≥3) |
| 5    | waiting_tier_mode               | Single-tier o Multi-tier |
| 6    | waiting_discount_tiers          | JSON de tiers (el último tier es el descuento máximo) |
| 7    | waiting_max_codes               | Cantidad máxima de códigos |
| 8    | waiting_duration                | Fechas fijas o duración relativa |
| 9-10 | waiting_start_date / end_date   | Fechas |
| 11   | waiting_auto_reset              | ¿Auto-reset? |
| 12   | waiting_reset_cycles            | Número de ciclos |
| 13   | waiting_question_set            | Selección de tema |
| 14   | waiting_confirmation            | Resumen completo + Confirmar |

**Pantalla de confirmación** muestra: nombre, tiers, vigencia, auto-reset, preguntas y códigos máximos.

---

## 5. Servicios Principales

| Servicio                    | Responsabilidad principal |
|-----------------------------|---------------------------|
| `TriviaConfigService`       | Gestiona singleton de límites diarios |
| `QuestionSetService`        | CRUD de sets temáticos + activación |
| `TriviaDiscountService`     | Crear configs, generar códigos (`generate_tiered_discount_code`), auto-reset, tiempo restante, extensión |
| `GameService`               | `get_trivia_entry_data()`, `play_trivia()`, lógica de streak, invalidación, reset diario |

---

## 6. Reglas de Negocio Clave

1. **Límites diarios** — Basados en conteo de `GameRecord` (UTC).
2. **Racha** — Solo incrementa con respuestas correctas consecutivas.
3. **Reset diario de racha** — Scheduler diario; **no afecta** códigos ya generados.
4. **Invalidación** — Error rompe racha y cancela código activo (`invalidate_streak_code`).
5. **Multi-tier** — JSON donde el último tier contiene el descuento máximo (no necesariamente 100%).
6. **Duración relativa + auto-reset** — Al expirar: 25% de duración original por ciclo (si habilitado).
7. **Question Sets** — `is_override=True` reemplaza todo; sino se usa por promoción.
8. **Códigos únicos** — Solo un código `ACTIVE` por usuario por `TriviaPromotionConfig`.

---

## 7. Migraciones Relevantes (orden cronológico aproximado)

| Archivo | Propósito |
|---------|-----------|
| `trivia_discount_system.py` | Crea tablas `trivia_promotion_configs` + `discount_codes` |
| `20250408_make_trivia_promotion_nullable.py` | Hace `promotion_id` nullable |
| `20250418_trivia_duration.py` | Agrega `duration_minutes` + `started_at` |
| `20250418_trivia_auto_reset.py` | Agrega auto-reset (`reset_count`, `max_reset_cycles`) |
| `c3d6143dc098_add_status_to_trivia_promotion_config.py` | Columna `status` |
| `205ae3e4b36a_add_question_sets_table.py` | Tabla `question_sets` |
| `20250603_add_question_set_id_to_trivia_promotion_config.py` | FK `question_set_id` |
| `20250604_add_discount_tiers_to_trivia_promotion_config.py` | Columna JSON `discount_tiers` |
| `add_trivia_config_table.py` + `merge_trivia_config_to_main.py` | Singleton `TriviaConfig` |
| Otras | `GameRecord`, enum `TransactionSource:TRIVIA`, etc. |

---

## 8. Archivos Afectados (Mapa Consolidado)

### Handlers
- `handlers/trivia_admin_handlers.py` — Límites diarios
- `handlers/trivia_discount_admin_handlers.py` — Wizard completo
- `handlers/game_user_handlers.py` — Gameplay + streak (FSM `TriviaStreakStates`)
- `handlers/question_set_admin_handlers.py` — CRUD de QuestionSet

### Services
- `services/trivia_config_service.py`
- `services/trivia_discount_service.py`
- `services/question_set_service.py`
- `services/game_service.py`

### Models (`models/models.py`)
- `QuestionSet`
- `TriviaPromotionConfig`
- `DiscountCode`
- `TriviaConfig`
- `GameRecord`
- `DiscountCodeStatus` (enum)

### Datos
- `docs/preguntas.json` (default)
- `docs/preguntas_vip.json`
- `docs/preguntas_mayo.json`, `preguntas_test.json`, etc.

### Keyboards (`keyboards/inline_keyboards.py`)
- `streak_choice_keyboard` — Continuar / Retirarse / Salir (solo al alcanzar un tier)
- `streak_continue_keyboard` — Continuar / Salir (entre niveles)
- `streak_final_keyboard` — Teclado final con descuento máximo
- `discount_claim_keyboard` — Copiar código de descuento

---

## 9. Resumen de Estados FSM

| Tipo              | Estados principales |
|-------------------|---------------------|
| **Usuario (Gameplay)** | `TriviaStreakStates`: `waiting_streak_choice`, `streak_continue` |
| **Admin Wizard**  | `TriviaDiscountStates` (17 estados) |
| **Question Sets** | `QuestionSetStates` |
| **Trivia Config** | `TriviaConfigStates` |

---

