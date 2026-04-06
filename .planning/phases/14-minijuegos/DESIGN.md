# Minijuegos - Fase 14

## Descripción

Sistema de minijuegos (Dados y Trivia) integrado en Lucien Bot para generar ingresos de besitos. Los usuarios pueden ganar besitos participando en juegos y respondiendo trivias.

---

## Requisitos

### Dados
- **Reglas de victoria**:
  - **Pares**: los dos números son pares (2, 4, 6) aunque sean diferentes entre ellos
  - **Dobles**: los dos números son iguales (1-1, 2-2, etc.)
- **Recompensa**: 1 besito por cada victoria
- **Interactividad**: animación visual de dados al jugar

### Trivia
- **Fuente de preguntas**: `docs/preguntas.json`
- **Selección**: aleatoria para cada usuario
- **Recompensa**: besitos por respuesta correcta (configurable)

### Mensajes de celebración
- Usar emojis y mensajes dopaminérgicos al ganar besitos

---

## Análisis de Viabilidad

### Arquitectura existente
- Handlers: `/handlers/` → solo routing
- Servicios: `/services/` → lógica de negocio
- Modelos: `/models/` → entidades SQLAlchemy
- Teclados: `/keyboards/inline_keyboards.py`

### Sistema de besitos
- **BesitoService** (`services/besito_service.py`):
  - `get_balance(user_id)` - consultar saldo
  - `credit_besitos(user_id, amount, source)` - acreditar besitos
  - `debit_besitos(user_id, amount, source)` - debitar besitos
  - `has_sufficient_balance(user_id, amount)` - verificar saldo
- **Fuente de transacciones**: agregar `GAME` y `TRIVIA` al enum `TransactionSource`

### Estados FSM
- Proyecto usa aiogram FSM con StatesGroup
- Juegos simples no requieren FSM (solo callbacks)

---

## Diseño del Sistema

### 1. Modelos de Datos

```python
# models/models.py - agregar

class GameRecord(Base):
    __tablename__ = "game_records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    game_type = Column(String(20), nullable=False)  # 'dice', 'trivia'
    bet_amount = Column(Integer, default=0)
    result = Column(String(50), nullable=False)
    payout = Column(Integer, default=0)
    played_at = Column(DateTime, default=datetime.utcnow)

class TriviaSession(Base):
    __tablename__ = "trivia_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    question_id = Column(Integer, nullable=False)
    correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Servicios

#### GameService (`services/game_service.py`)
- `roll_dice()` - lanzar dos dados (1-6)
- `check_win(dice1, dice2)` - verificar victoria (pares o dobles)
- `credit_win(user_id)` - acreditar besitos por victoria
- `get_random_trivia()` - obtener pregunta aleatoria de preguntas.json

#### TriviaService (`services/trivia_service.py`)
- `get_question()` - obtener pregunta aleatoria
- `check_answer(question_idx, user_answer)` - verificar respuesta
- `award_besitos(user_id)` - otorgar besitos por acierto

### 3. Handlers

#### Game User Handlers (`handlers/game_user_handlers.py`)
- `game_menu` - mostrar menú de minijuegos
- `dice_play` - lanzar dados
- `trivia_start` - iniciar trivia
- `trivia_answer` - procesar respuesta

#### Game Admin Handlers (`handlers/game_admin_handlers.py`)
- `game_admin_menu` - configuración de juegos
- `set_dice_reward` - configurar recompensa de dados
- `set_trivia_reward` - configurar recompensa de trivia

### 4. Keyboards

```python
# keyboards/inline_keyboards.py - agregar

def game_menu_keyboard():
    # Botones: 🎲 Dados, ❓ Trivia, Volver

def dice_game_keyboard():
    # Botón: 🎲 Jugar Dados

def trivia_keyboard(options):
    # Opciones de respuesta A, B, C, D
```

### 5. Integración con menú principal

```python
# keyboards/inline_keyboards.py - modificar main_menu_keyboard

def main_menu_keyboard(is_vip, besitos_balance=None):
    # Agregar botón: 🎮 Minijuegos
```

---

## Flujos de Usuario

### Dados
1. Usuario toca "🎮 Minijuegos" en menú principal
2. Ve opciones: "🎲 Dados" o "❓ Trivia"
3. Toca "🎲 Dados"
4. Lucien muestra animación de dados rodando 🎲🎲
5. Dados caen: resultadoaleatorio
6. Si victoria (pares/dobles): mensaje de celebración + besito
7. Si derrota: mensaje de ánimo

### Trivia
1. Usuario toca "❓ Trivia" en menú de juegos
2. Lucien muestra pregunta aleatoria con 4 opciones
3. Usuario selecciona respuesta
4. Si correcta: celebración + besitos
5. Si incorrecta: mostrar respuesta correcta

---

## Mensajes de Celebración

### Victoria en dados
```
🎉 ¡VICTORIA! 🎉
Los dados cayeron: [2] [4]
¡Son pares! Has ganado 1 besito 💋

¡Tu suerte te sonríe, Visitante!
```

### Respuesta correcta en trivia
```
🌟 ¡CORRECTO! 🌟
Has respondido bien y ganado X besitos 💋

¡Brillas como el sol, Visitante!
```

---

## Configuración (Admin)

- Recompensa por victoria en dados: 1 besito (default)
- Recompensa por trivia correcta: configurable
- Límite de juegos por día: sin límite

---

## Archivos a Crear/Modificar

### Nuevos
- `.planning/phases/14-minijuegos/DESIGN.md` (este archivo)
- `services/game_service.py`
- `handlers/game_user_handlers.py`

### Modificar
- `models/models.py` - agregar GameRecord, TriviaSession
- `keyboards/inline_keyboards.py` - agregar keyboards de juegos
- `bot.py` - registrar nuevos handlers

---

## Estado

- [ ] Análisis de viabilidad: ✓ Completado
- [ ] Diseño del sistema: ✓ Completado
- [ ] Modelos de datos: ⏳ Pendiente
- [ ] Servicios: ⏳ Pendiente
- [ ] Handlers: ⏳ Pendiente
- [ ] Keyboards: ⏳ Pendiente
- [ ] Integración menú: ⏳ Pendiente
- [ ] Verificación: ⏳ Pendiente
