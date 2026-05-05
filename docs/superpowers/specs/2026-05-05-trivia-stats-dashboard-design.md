# Trivia Stats Dashboard — Diseño Técnico

**Fecha:** 2026-05-05
**Tipo:** Dashboard analítico (lectura only)

---

## 1. Resumen

Extraer métricas del sistema de trivias y descuentos por racha existente para construir un dashboard de estadísticas dirigido a Custodios. No modifica lógica ni modelos existentes — solo consume datos ya registrados.

**Tres segmentos de métricas:**

| Segmento | Descripción |
|----------|-------------|
| **Promociones** | Estado de cada配置 de promoción por racha (códigos generados, reclamados, usados, cancelados, expirados) |
| **Usuarios** | Tasa de aciertos, rachas, besitos ganados, códigos obtenidos/usados por usuario |
| **Ranking** | Top usuarios por respuestas correctas, racha máxima, códigos reclamados |

---

## 2. Modelos Consumidos (solo lectura)

| Modelo | Uso |
|--------|-----|
| `TriviaPromotionConfig` | Configuraciones de promoción (nome, status, tiers, limites) |
| `DiscountCode` | Códigos generados + status + discount_percentage |
| `DiscountCodeStatus` | Enum: ACTIVE / USED / EXPIRED / CANCELLED |
| `GameRecord` | Todas las partidas de trivia (`game_type IN ('trivia', 'trivia_vip')`) |
| `QuestionSet` | Tema(s) activo(s) |

---

## 3. Métricas a Extraer

### 3.1 Por Promoción

Para cada `TriviaPromotionConfig` activa o inactiva:

| Métrica | Cómo se calcula |
|---------|-----------------|
| `total_codes` | Count total de `DiscountCode` con ese `config_id` |
| `codes_by_status` | Count agrupado por `DiscountCode.status` |
| `claimed` | `config.codes_claimed` |
| `available` | `config.max_codes - config.codes_claimed` |
| `used_percentage` | `(USED / max_codes) * 100` |
| `tiers_summary` | Lista de tiers con streak y discount |
| `duration_remaining` | `get_time_remaining_formatted(config.id)` si es duration-based |
| `question_set` | `question_set.name` si existe |

### 3.2 Por Usuario

Agregación por `user_id` + `game_type`:

| Métrica | Cómo se calcula |
|---------|-----------------|
| `total_plays` | Count de `GameRecord` donde `game_type` matchea |
| `correct_answers` | Count donde `payout > 0` |
| `incorrect_answers` | Count donde `payout == 0` |
| `correctness_rate` | `correct / total * 100` |
| `current_streak` | Conteo secuencial desde el último registro del día (payout > 0 unbroken) |
| `max_streak_session` | Mayor racha observada en una sola sesión (secuencia ininterrumpida de payout > 0) |
| `besitos_earned` | Sum de `payout` para ese game_type |
| `codes_earned` | Count de `DiscountCode` con ese `user_id` y status ACTIVE |
| `codes_used` | Count de `DiscountCode` con ese `user_id` y status USED |

### 3.3 Ranking

Tres rankings independientes (limit 10 o 20 configurable):

| Ranking | Order by | Top |
|---------|----------|-----|
| `top_scorers` | `correct_answers` DESC | trivia + trivia_vip combinados |
| `top_streaks` | `max_streak_session` DESC | trivia + trivia_vip combinados |
| `top_codes` | `codes_used` DESC | códigos usados (USADO) |

Cada entrada incluye: `rank`, `user_id`, `username`, `first_name`, `value`

---

## 4. Servicio: TriviaStatsService

**Archivo:** `services/trivia_stats_service.py`

```python
class TriviaStatsService:
    # === PROMO STATS ===
    def get_promotion_stats(self, config_id: int) -> dict
    def get_all_promotions_stats(self) -> list[dict]

    # === USER STATS ===
    def get_user_trivia_stats(self, user_id: int) -> dict

    # === RANKINGS ===
    def get_top_scorers(self, limit: int = 10) -> list[dict]
    def get_top_streaks(self, limit: int = 10) -> list[dict]
    def get_top_codes_redeemed(self, limit: int = 10) -> list[dict]

    # === EXPORTS ===
    def export_promotions_csv(self) -> str | None
    def export_users_stats_csv(self) -> str | None
    def export_rankings_csv(self) -> str | None

    # === DASHBOARD ===
    def get_full_dashboard(self) -> dict  # todo junto
```

### Detalle de `get_full_dashboard()`

```python
{
    "generated_at": "2026-05-05T...",
    "promotions": [...],      # lista de stats por promo
    "users_summary": {
        "total_trivia_users": int,
        "total_vip_trivia_users": int,
        "avg_correctness_rate": float,
        "avg_streak": float,
    },
    "rankings": {
        "top_scorers": [...],
        "top_streaks": [...],
        "top_codes": [...]
    }
}
```

---

## 5. Handler: Dashboard de Admin

**Archivo a crear:** `handlers/trivia_stats_admin_handlers.py`

Nuevo handler para custodios que acciona el dashboard.

| Callback data | Acción |
|---------------|--------|
| `trivia_stats_dashboard` | Muestra resumen general con métricas agregadas |
| `trivia_stats_promotions` | Lista cada promoción con sus métricas |
| `trivia_stats_users` | Top 10 usuarios por correctas + besitos + códigos |
| `trivia_stats_export` | Genera y envía CSVs por separados (promos, usuarios, rankings) |

Keyboard: Inline keyboard con botones por sección + botón de exportar todo.

**Mensajes de respuesta** — formato texto/tabulado simple (no HTML rico). Máximo 4096 chars por mensaje; si ranking > 10 usar múltiples mensajes.

---

## 6. Flujo de Datos

```
Custodio ejecuta /trivia_stats
  → trivia_stats_admin_handlers.py
      → TriviaStatsService.get_full_dashboard()
          → queries: TriviaPromotionConfig, DiscountCode, GameRecord
          → calcula métricas
          → retorna dict
      → formatea mensaje
      → envía a Telegram
```

Queries son todas de solo lectura. Sin transacciones de escritura.

---

## 7. Exportación CSV

Tres archivos separados:

| Archivo | Contenido |
|---------|-----------|
| `trivia_promotions_YYYYMMDD.csv` | Una fila por promoción: id, nome, status, total_codes, active, used, cancelled, expired, claimed, available |
| `trivia_users_YYYYMMDD.csv` | Una fila por usuario: telegram_id, username, game_type, total_plays, correct, incorrect, rate, max_streak, besitos |
| `trivia_rankings_YYYYMMDD.csv` | Tres bloques: top_scorers, top_streaks, top_codes |

---

## 8. Reglas de Implementación

1. **Sin писания** en modelos — solo lectura
2. **Sin modificación** de lógica de trivia ni generación de códigos
3. **Sin nuevos modelos** — reutilizar los 5 existentes
4. Logs: cada método de stats loguea su nombre, parametro de entrada (config_id/user_id), y count del resultado
5. Límites de ranking: default 10, configurable hasta 50
6. Rankings se calculan sobre **todo el histórico** (no filtrado por fecha) — sin límite temporal
7. CSVs van a `/tmp/` con tempfile.NamedTemporaryFile y seBorren después de enviar

---

## 9. Verificaciones Previas a Implementación

- [ ] `GameRecord.game_type` permite 'trivia' y 'trivia_vip' como valores
- [ ] `DiscountCode.status` es un Enum con los 4 valores esperados
- [ ] `TriviaPromotionConfig.discount_tiers` es JSON string o None
- [ ] `QuestionSet` tiene relación con `TriviaPromotionConfig` vía `question_set_id`

---

## 10. Dependencias

Usa los models existentes — no requiere nuevas migraciones.

Services existentes consumidos:
- `TriviaDiscountService.get_discount_stats()` — referencia, no reutilización directa (el método actual es por config_id)
- `TriviaDiscountService.parse_discount_tiers()` — para mostrar tiers en stats de promo

No consume handlers existentes. Se crea handler nuevo.
