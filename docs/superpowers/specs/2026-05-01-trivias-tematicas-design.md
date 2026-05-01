# Trivias Temáticas con Activación por Promoción

## Problema

Actualmente las trivias usan un solo archivo plano de preguntas (`preguntas.json`). No existe noción de sets temáticos de preguntas, ni forma de activar automáticamente un set cuando una promoción con fecha está activa.

## Solución

Sistema de **QuestionSets** que permite:

1. Admin define múltiples sets de preguntas (via JSON)
2. Admin activa manualmente un set para uso inmediato
3. Las promociones pueden asociarse a un set — cuando la promoción está activa por fecha, el set se activa automáticamente
4. Al terminar la promoción, se revierte al set general

---

## Diseño

### 1. Modelo de Datos

**Nuevo modelo `QuestionSet`** (en `models/models.py`):

```python
class QuestionSet(Base):
    __tablename__ = "question_sets"

    id: int (PK, auto)
    name: str (único, ej: "1 de Mayo")
    file_path: str (ruta al JSON, ej: "docs/question_sets/primero_de_mayo.json")
    description: str (nullable)
    is_active: bool (default False) — override manual del admin
    created_at: datetime

    # Relación: una promoción puede tener un question_set_id
    promotion_id: int (FK nullable → Promotion.id)
```

**Cambio en `Promotion`**:

```python
class Promotion(Base):
    # ... campos existentes ...
    question_set_id: int (FK nullable → QuestionSet.id)
    # Un campo activa_sistema:bool (para promotions tipo "Gabinete de Oportunidades")
```

### 2. Admin — Menú de QuestionSets

Nuevo handler: `question_set_admin_handlers.py`

FSM con pasos:
1. **Ver sets activos** — muestra cuál está activo ahora + override manual
2. **Crear set** — pide nombre + descripción + archivo JSON (upload o path)
3. **Activar set manualmente** — override manual, desactiva cualquier otro override
4. **Desactivar override manual** — regresa a modo "controlado por promoción"
5. **Ver/editar set** — cambiar description, cambiar file_path

### 3. Admin — Asociación en Promoción

Al crear/editar `Promotion` (en `promotion_admin_handlers.py`):

- Nuevo paso en el wizard: seleccionar `QuestionSet` (opcional)
- Si se selecciona, la promoción al estar activa activa ese set
- Si no se selecciona, la promoción no afecta la trivia

### 4. Scheduler — Activación automática por fecha

**Job cada 1 minuto** (`SchedulerService` o job dedicado):

```
Para cada Promotion con question_set_id y fecha_actual entre start_date y end_date:
  → marcar QuestionSet.is_active = True (para esa promo)

Para cada QuestionSet que NO tiene promoción activa:
  → si estaba activo por promoción (no por override manual), marcar is_active = False
```

**Lógica de precedence**:
1. Si existe algún QuestionSet con `is_active=True` por **override manual** → ese se usa
2. Si hay QuestionSets activos por **promoción** → se usa el de la promoción más reciente
3. Si ninguno de los anteriores → se usa `preguntas.json` (set general)

El campo `is_active_by_promotion` en `QuestionSet` distingue el origen del activo.

### 5. Trivia — Carga de preguntas

`GameService.get_random_question()`:

```python
def get_random_question(self) -> dict:
    # 1. Si hay override manual → cargar de ese file_path
    # 2. Si hay promoción activa con set → cargar de ese file_path
    # 3. Si no → cargar de docs/preguntas.json (comportamiento actual)
```

同样的 para `load_trivia_questions()` y `load_trivia_vip_questions()`.

### 6. Flujo completo

**Escenario 1 — Activación manual:**
1. Admin entra al menú QuestionSet
2. Crea set "1 de Mayo" asociando `docs/question_sets/primero_de_mayo.json`
3. Activa manualmente el set
4. → Trivia usa ese set immediately

**Escenario 2 — Activación por promoción:**
1. Admin crea promoción "1 de Mayo" (1-5 mayo)
2. En el wizard asocia el QuestionSet "1 de Mayo"
3. Scheduler detecta que la promo está activa por fecha
4. → QuestionSet se activa automáticamente
5. 6 de mayo: scheduler detecta promo vencida → revierte a set general

**Escenario 3 — Override manual > promoción:**
1. Promo "1 de Mayo" activa usando set "1 de Mayo"
2. Admin manualmente activa set "San Valentín" (override)
3. → Trivia usa "San Valentín" aunque la promo de Mayo esté activa
4. Admin desactiva override manual → promo de Mayo retoma el control

---

## Archivos a modificar/crear

| Archivo | Cambio |
|---------|--------|
| `models/models.py` | Agregar `QuestionSet`, agregar `question_set_id` a `Promotion` |
| `services/game_service.py` | `get_random_question()` y `load_questions()` respected el active set |
| `handlers/question_set_admin_handlers.py` | **NUEVO** — FSM admin para managear sets |
| `services/scheduler_service.py` | Job cada 1 min para sync promoción → question set |
| `handlers/promotion_admin_handlers.py` | Agregar paso wizard para asociar QuestionSet |
| `docs/question_sets/primero_de_mayo.json` | **NUEVO** — archivo JSON de preguntas temáticas |

---

## Notas de implementación

- Los archivos JSON de sets se almacenan en `docs/question_sets/` (nuevo directorio)
- Admin sube/asocia el archivo vía path — no se almacena el contenido en BD
- El scheduler job se puede agregar como job inline en `SchedulerService` usando `add_job` dinámico
- No se modifica el flujo de usuario final — solo cambia de qué JSON se sacan las preguntas
- Mantener backwards compatible: si no existe ningún QuestionSet, behave como hoy (carga `preguntas.json`)
