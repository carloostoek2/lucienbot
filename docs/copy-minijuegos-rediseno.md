# Copy Rediseñado - Sistema de Minijuegos
## Voz de Lucien: Elegante, Misterioso, en Tercera Persona

> **NOTA (junio 2026):** Este documento contiene el diseño poético anterior de los minijuegos.  
> Se reemplazó por lenguaje **directo y claro** (reglas explícitas, feedback simple, sin metáforas excesivas) para evitar confusiones en acciones.  
> Ver la sección actualizada en `docs/guia-estilo.md` ("Actualización de tono — Tienda y Minijuegos") y la implementación en `utils/lucien_voice.py` + `services/game_service.py` (MENU_TEMPLATES / DICE_TEMPLATES / TRIVIA_* simplificados).  
> Los ejemplos de abajo se conservan solo por referencia histórica.

**Versión actual recomendada (directa):**

```python
# Menú simplificado
"🎮 Minijuegos\n\nJuegue y gane besitos. Límite diario por juego.\n\n"
"<b>Dados:</b> gane 1 besito con pares o dobles.\n<i>restantes de límite</i>\n\n"
"<b>Trivia:</b> responda correctamente y gane besitos."

# Botones
"dice": "🎲 Dados",
"trivia": "❓ Trivia"

# Reglas dados (directas)
"Lance dos dados. Gane besitos si obtiene pares o dobles.\n"
"• Ambos pares: +1 besito\n• Iguales (dobles): +1 besito"

# Feedback
"¡Dobles! +1 besito."
"¡Pares! +1 besito."
"{dice1} y {dice2}. No ganó esta vez."

# Trivia
"Responda correctamente para ganar 1 besito."
"¡Correcto! +1 besito."
"Incorrecto. La respuesta era: XXX"
```

---

**Versión histórica (poética) a continuación para referencia.**

## 1. MENÚ PRINCIPAL DE JUEGOS

### Template Completo

```python
# Mensaje introductorio de Lucien
GAME_MENU_INTRO = """🎩 <b>El Salón de los Rituales</b>

Lucien tiene el honor de presentarle los pasatiempos que Diana ha diseñado para quienes buscan más que palabras..."""

# Líneas de juego con contador (formatear según estado)
def format_dice_line(remaining: int, limit: int, is_vip: bool) -> str:
    if is_vip:
        return f"🎲 Dados — {remaining} de {limit} rituales reservados por Diana"
    return f"🎲 Dados — {remaining} de {limit} oportunidades disponibles hoy"

def format_trivia_line(remaining: int, limit: int, is_vip: bool) -> str:
    if is_vip:
        return f"❓ Trivia — {remaining} de {limit} exámenes concedidos"
    return f"❓ Trivia — {remaining} de {limit} preguntas a su disposición"

# Mensaje completo del menú
def build_game_menu_message(dice_remaining: int, dice_limit: int,
                           trivia_remaining: int, trivia_limit: int,
                           is_vip: bool) -> str:
    vip_badge = "✨ VIP" if is_vip else "Visitante"
    dice_line = format_dice_line(dice_remaining, dice_limit, is_vip)
    trivia_line = format_trivia_line(trivia_remaining, trivia_limit, is_vip)

    return f"""🎩 <b>El Salón de los Rituales</b> — {vip_badge}

Lucien tiene el honor de presentarle los pasatiempos que Diana ha diseñado para quienes buscan más que palabras...

{dice_line}
{trivia_line}

¿Cuál ritual desea iniciar?"""

# Botones
GAME_MENU_BUTTONS = {
    "dice": "🎲 Lanzar los dados del destino",
    "trivia": "❓ El examen de Diana",
    "back": "🔙 Regresar al vestíbulo"
}
```

### Notas de Uso
- Mostrar cuando `callback.data == "game_menu"`
- Los contadores deben actualizarse en tiempo real
- El tono es invitatorio pero con aire de exclusividad

---

## 2. DADOS - PANTALLA DE ENTRADA

### Template Completo

```python
DICE_ENTRY_MESSAGE = """🎲 <b>El Ritual de los Dados</b>

Los dados no mienten... aunque a veces prefieren el silencio.

Lucien ha visto a Diana observar con particular interés cómo ciertos visitantes invocan la fortuna. Los números pares susurran secretos. Los dobles... bueno, los dobles tienen sus propios designios.

¿Se siente con la suficiente... audacia?"""

DICE_ENTRY_BUTTON = "🎲 Invocar el destino"
```

### Notas de Uso
- Mostrar antes del primer lanzamiento
- Incluir hint sutil sobre las reglas sin ser explícito
- El botón debe llevar a `callback.data == "dice_play"`

---

## 3. DADOS - RESULTADOS GANADOR

### Variante A - Dobles (dice1 == dice2)

```python
DICE_WIN_DOUBLES_TEMPLATES = [
    # Variante A1
    """✨ <b>Los números se alinean...</b>

🎲 {dice} — {dice}

*Lucien arquea una ceja con genuina sorpresa*

Dobles. Diana tiene una debilidad particular por quienes logran que el azar repita su canción. Es... inusual.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante A2
    """<b>El espejo se mira a sí mismo...</b>

🎲 {dice} — {dice}

*un momento de silencio respetuoso*

Dobles. Lucien ha visto a muchos intentarlo, pocos lograrlo. Diana ciertamente ha notado su... persistencia.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante A3
    """<b>La simetría del destino</b>

🎲 {dice} — {dice}

*Lucien inclina la cabeza con aprobación*

Cuando los dados coinciden, Diana dice que el universo está de acuerdo. Y el universo, al parecer, está de acuerdo con usted.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}"""
]
```

### Variante B - Pares (ambos pares, no dobles)

```python
DICE_WIN_PAIRS_TEMPLATES = [
    # Variante B1
    """<b>El equilibrio encuentra su forma...</b>

🎲 {dice1} — {dice2}

Dos pares. No el resultado más dramático, pero Lucien ha aprendido que Diana aprecia la consistencia. Hay elegancia en los números que se presentan en pareja sin ser idénticos.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante B2
    """<b>Los pares se reconocen</b>

🎲 {dice1} — {dice2}

*Lucien asiente lentamente*

Ambos pares. No es el destino gritando, pero es el destino susurrando. Diana escucha los susurros.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante B3
    """<b>Armonía en los números</b>

🎲 {dice1} — {dice2}

Lucien observa que ha logrado lo que algunos llaman 'el pasillo' — pares que conversan entre sí sin ser gemelos. Diana considera esto... prometedor.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}"""
]
```

### Variante C - Rara (~15% de victorias)

```python
DICE_WIN_RARE_TEMPLATES = [
    # Variante C1
    """<b>*guarda silencio un momento*</b>

🎲 {dice1} — {dice2}

...interesante.

Lucien no está seguro de haber visto esta combinación particular en... bueno, en bastante tiempo. El destino a veces elige ser generoso sin explicaciones. Diana prefiere así.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante C2
    """<b>*ajusta sus guantes con precisión inusual*</b>

🎲 {dice1} — {dice2}

Lucien debe confesar que esta combinación es... notable. No por las reglas establecidas, sino por algo que Diana llamaría 'el factor intrigante'.

Y a Diana le encanta lo intrigante.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}""",

    # Variante C3
    """<b>El azar tiene sus favoritos</b>

🎲 {dice1} — {dice2}

*Lucien sonríe con misterio*

No pregunte por qué. Algunas victorias no necesitan explicación lógica — solo la aprobación silenciosa de Diana. Y esa, créame, vale más que cualquier regla.

💋 <b>+{besitos} besito</b>
Total acumulado: {total_besitos}"""
]
```

### Lógica de Selección
```python
def select_win_message(dice1: int, dice2: int, besitos: int, total_besitos: int) -> str:
    import random

    if dice1 == dice2:
        # Dobles - Variante A
        template = random.choice(DICE_WIN_DOUBLES_TEMPLATES)
        return template.format(dice=dice1, besitos=besitos, total_besitos=total_besitos)
    elif dice1 % 2 == 0 and dice2 % 2 == 0:
        # Pares - Variante B
        template = random.choice(DICE_WIN_PAIRS_TEMPLATES)
        return template.format(dice1=dice1, dice2=dice2, besitos=besitos, total_besitos=total_besitos)
    else:
        # Rara - ~15% chance, random selection
        if random.random() < 0.15:
            template = random.choice(DICE_WIN_RARE_TEMPLATES)
            return template.format(dice1=dice1, dice2=dice2, besitos=besitos, total_besitos=total_besitos)
        else:
            # Fallback a pares si no califica para rara
            template = random.choice(DICE_WIN_PAIRS_TEMPLATES)
            return template.format(dice1=dice1, dice2=dice2, besitos=besitos, total_besitos=total_besitos)
```

---

## 4. DADOS - RESULTADOS PERDEDOR

### Variante Estándar

```python
DICE_LOSE_STANDARD_TEMPLATES = [
    # Variante L1
    """<b>Hmm...</b>

🎲 {dice1} — {dice2}

*Lucien estudia los dados con expresión neutra*

El destino, al parecer, ha decidido ser discreto esta vez. Lucien podría mencionar que Diana ha visto a sus favoritos perder con más elegancia que a otros ganar... pero eso sería indiscreto.

{remaining} oportunidades aún disponibles hoy""",

    # Variante L2
    """<b>Los dados han hablado</b>

🎲 {dice1} — {dice2}

*Lucien recoge los dados con delicadeza*

No siempre el resultado que esperamos, pero siempre el resultado que merecemos... o eso dice Diana cuando pierde al ajedrez. Lucien no opina.

{remaining} oportunidades aún disponibles hoy""",

    # Variante L3
    """<b>Un resultado... interesante</b>

🎲 {dice1} — {dice2}

*Lucien mantiene compostura impecable*

No es victoria, pero tampoco es derrota definitiva. El destino simplemente ha pospuesto su decisión. Diana encuentra esto... poético.

{remaining} oportunidades aún disponibles hoy"""
]
```

### Variante Near-Miss (cuando resultados "casi" califican)

Near-miss: combinaciones como {1,2}, {2,3}, {3,4}, {4,5}, {5,6} — secuencias consecutivas

```python
DICE_LOSE_NEAR_MISS_TEMPLATES = [
    # Variante NM1
    """<b>*inhala lentamente*</b>

🎲 {dice1} — {dice2}

Tan cerca...

Lucien casi pudo ver cómo el destino dudó. Un número más, un giro diferente... pero no. Diana siempre dice que la paciencia es la virtud de quienes entienden el verdadero valor de las cosas.

{remaining} intentos esperan su decisión""",

    # Variante NM2
    """<b>*un suspiro apenas audible*</b>

🎲 {dice1} — {dice2}

Casi. Tan cerca que Lucien podría jurar que los dados vacilaron.

Diana mencionó una vez que las victorias que se demoran son las que más se saborean. Lucien no está seguro de si eso es consuelo o promesa.

{remaining} intentos esperan su decisión""",

    # Variante NM3
    """<b>El destino se detuvo a contemplar...</b>

🎲 {dice1} — {dice2}

*Lucien observa los dados con interés renovado*

Esta combinación estuvo a punto de ser... significativa. Diana tiene un nombre para estos momentos: 'el preludio'. Lo que sigue suele ser interesante.

{remaining} intentos esperan su decisión"""
]
```

### Lógica de Selección Near-Miss
```python
def is_near_miss(dice1: int, dice2: int) -> bool:
    """Detecta si es una secuencia consecutiva (casi victoria)"""
    return abs(dice1 - dice2) == 1

def select_lose_message(dice1: int, dice2: int, remaining: int) -> str:
    import random

    if is_near_miss(dice1, dice2):
        template = random.choice(DICE_LOSE_NEAR_MISS_TEMPLATES)
    else:
        template = random.choice(DICE_LOSE_STANDARD_TEMPLATES)

    return template.format(dice1=dice1, dice2=dice2, remaining=remaining)
```

---

## 5. DADOS - LÍMITE ALCANZADO

### Template Completo

```python
DICE_LIMIT_REACHED_FREE = """🎩 <b>Los rituales de hoy han concluido</b>

Lucien ha contabilizado cada lanzamiento, cada suspiro del destino, cada momento de anticipación. Y Lucien debe informarle — con genuina pena, créame — que su cuota de invocaciones ha sido completada.

La mesura, dice Diana, es la marca de quien sabe que la verdadera elegancia reside en saber cuándo retirarse... aunque solo sea hasta mañana.

El destino será invocado de nuevo cuando el sol renazca."""

DICE_LIMIT_REACHED_VIP = """🎩 <b>Los rituales reservados han concluido</b>

Lucien ha registrado cada uno de los {limit} rituales que Diana concedió para esta noche. Todos. Incluso Lucien se ha impresionado ligeramente.

Diana mencionó una vez que quienes agotan sus oportunidades demuestran o bien una fe inquebrantable en la fortuna, o una terquedad admirable. Diana aprecia ambas cualidades.

Los dados descansarán hasta mañana."""
```

### Notas de Uso
- `DICE_LIMIT_REACHED_FREE` para usuarios no-VIP
- `DICE_LIMIT_REACHED_VIP` para usuarios VIP (incluye el límite en el mensaje)
- Mostrar botón "🔙 Regresar al vestíbulo"

---

## 6. TRIVIA - PANTALLA DE ENTRADA + PREGUNTA

### Template Completo

```python
TRIVIA_ENTRY_TEMPLATE = """❓ <b>El Examen de Diana</b>

Las preguntas que verá a continuación no son triviales... bueno, técnicamente sí lo son, pero Diana las ha diseñado con un propósito particular: conocerle a usted.

Cada respuesta correcta revela algo. No solo a Lucien, no solo a Diana, sino a usted mismo. Las preguntas son espejos disfrazados de acertijos.

Pregunta {current} disponible hoy."""

TRIVIA_QUESTION_TEMPLATE = """❓ <b>El Examen de Diana</b>

📜 <i>{question}</i>

*Lucien observa con interés profesional*

Las respuestas apresuradas suelen ser las más honestas... o las más reveladoras. Diana prefiere que usted tome su tiempo.

¿Cuál es su respuesta?"""

# Botones de respuesta (A, B, C)
TRIVIA_ANSWER_BUTTONS = {
    "A": "📜 A) {text}",
    "B": "📜 B) {text}",
    "C": "📜 C) {text}"
}
```

### Notas de Uso
- Mostrar `TRIVIA_ENTRY_TEMPLATE` primero si es la primera pregunta del día
- Luego `TRIVIA_QUESTION_TEMPLATE` con la pregunta actual
- `{current}` debe calcularse como: `played + 1`

---

## 7. TRIVIA - RESPUESTA CORRECTA

### Variante A (Normal)

```python
TRIVIA_CORRECT_NORMAL_TEMPLATES = [
    # Variante A1
    """<b>...impresionante.</b>

✅ Correcto

*Lucien asiente con aprobación genuina*

Diana siempre dice que quienes prestan atención a los detalles son quienes merecen atención a su vez. Usted, al parecer, presta atención.

💋 <b>+{besitos} besitos</b>
Total acumulado: {total_besitos}""",

    # Variante A2
    """<b>La respuesta precisa</b>

✅ Correcto

*Lucien anota algo en su libreta mental*

Correcto. No por suerte, Lucien presume, sino por... ¿conocimiento? ¿intuición? Diana encontraría ambas explicaciones igualmente interesantes.

💋 <b>+{besitos} besitos</b>
Total acumulado: {total_besitos}""",

    # Variante A3
    """<b>El conocimiento reconocido</b>

✅ Correcto

*Lucien sonríe sutilmente*

Diana apostaba a que sabría la respuesta. Diana suele ganar sus apuestas.

💋 <b>+{besitos} besitos</b>
Total acumulado: {total_besitos}"""
]
```

### Variante B (Racha 2+ correctas)

```python
TRIVIA_CORRECT_STREAK_TEMPLATES = [
    # Variante B1
    """<b>De nuevo correcto.</b>

✅ Correcto — {streak} consecutivas

*Lucien estudia al visitante con renovado interés*

Diana ha comenzado a notar un patrón. Su forma de pensar... no pasa desapercibida. Diana encuentra eso intrigante. Y a Diana le encanta lo intrigante.

💋 <b>+{besitos} besitos</b>
{total_besitos} besitos — y contando""",

    # Variante B2
    """<b>La racha continúa</b>

✅ Correcto — {streak} consecutivas

*Lucien ajusta sus guantes con deliberación*

Dos correctas seguidas podrían ser suerte. Tres, coincidencia. Pero Diana dice que cuatro revelan carácter. Lucien está empezando a entender qué ve ella.

💋 <b>+{besitos} besitos</b>
{total_besitos} besitos — y contando""",

    # Variante B3
    """<b>Consistencia notable</b>

✅ Correcto — {streak} consecutivas

*Lucien inclina la cabeza en gesto de respeto*

Hay visitantes que aciertan por casualidad, y visitantes que aciertan por... otra cosa. Diana ha comenzado a especular sobre usted. Eso es, créame, un honor.

💋 <b>+{besitos} besitos</b>
{total_besitos} besitos — y contando"""
]
```

### Lógica de Selección
```python
def select_trivia_correct_message(besitos: int, total_besitos: int, streak: int = 1) -> str:
    import random

    if streak >= 2:
        template = random.choice(TRIVIA_CORRECT_STREAK_TEMPLATES)
        return template.format(besitos=besitos, total_besitos=total_besitos, streak=streak)
    else:
        template = random.choice(TRIVIA_CORRECT_NORMAL_TEMPLATES)
        return template.format(besitos=besitos, total_besitos=total_besitos)
```

---

## 8. TRIVIA - RESPUESTA INCORRECTA

### Template Completo

```python
TRIVIA_INCORRECT_TEMPLATES = [
    # Variante I1
    """<b>Ah...</b>

❌ No exactamente

La respuesta era: <b>{correct_answer}</b>

*Lucien guarda un momento de silencio*

Diana siempre dice que equivocarse es simplemente el primer paso hacia la próxima pregunta. Ella se equivoca raramente, pero cuando lo hace, lo hace con estilo.

¿Otra pregunta?""",

    # Variante I2
    """<b>Interesante elección...</b>

❌ No exactamente

La respuesta era: <b>{correct_answer}</b>

*Lucien anota algo mentalmente*

No es la respuesta que Diana esperaba, pero Diana encuentra valor en las respuestas inesperadas. A veces revelan más que las correctas.

¿Otra pregunta?""",

    # Variante I3
    """<b>El destino del conocimiento</b>

❌ No exactamente

La respuesta era: <b>{correct_answer}</b>

*Lucien sonríe con misterio*

Incorrecto, sí, pero ¿sabe qué? Diana ha mencionado que sus errores favoritos son los que vienen de quienes al menos lo intentaron con convicción.

¿Otra pregunta?"""
]

# Botón para continuar
TRIVIA_CONTINUE_BUTTON = "❓ Continuar el examen"
TRIVIA_BACK_BUTTON = "🔙 Regresar al salón"
```

### Notas de Uso
- Mostrar botón "Continuar el examen" si quedan preguntas disponibles
- Mostrar botón "Regresar al salón" si es la última o no quedan más

---

## 9. TRIVIA - LÍMITE ALCANZADO

### Template Completo

```python
TRIVIA_LIMIT_REACHED_FREE = """🎩 <b>La cuota de exámenes completada</b>

Lucien ha registrado cada respuesta, cada reflexión, cada momento de duda. Y Lucien debe informarle que ha alcanzado el límite de preguntas para hoy.

Diana diseñó estos exámenes para ser saboreados, no devorados. La anticipación, dice ella, es el ingrediente secreto de todo conocimiento valioso.

Las preguntas regresarán mañana. Diana lo garantiza."""

TRIVIA_LIMIT_REACHED_VIP = """🎩 <b>Los exámenes reservados han concluido</b>

Lucien ha supervisado cada una de las {limit} preguntas que Diana concedió para esta sesión. Todas han sido respondidas — algunas con acierto, otras con... aprendizaje.

Diana mencionó que los VIP que agotan sus exámenes demuestran una sed de conocimiento que ella encuentra... estimulante.

El examen continuará mañana. Hasta entonces, reflexione sobre lo aprendido."""
```

---

## 10. DIFERENCIACIÓN VIP vs FREE

### Mensajes de Límite (en flujo normal)

```python
# En el menú principal
LIMIT_DISPLAY = {
    "free": "{remaining} oportunidades disponibles hoy",
    "vip": "Usted tiene {remaining} rituales reservados por Diana esta noche."
}

# En mensajes de límite alcanzado (upsell sutil)
LIMIT_UPSELL_FREE = """

¿Le gustaría más? Los miembros del círculo íntimo disponen de el doble de oportunidades. Diana siempre tiene espacio para quienes demuestran... dedicación."""

LIMIT_UPSELL_VIP = """

Lucien observa que ha sido particularmente... persistente hoy. Diana aprecia esa cualidad."""
```

### Notas de Implementación
- VIP: Usar lenguaje de exclusividad ("reservados", "concedidos", "círculo íntimo")
- Free: Lenguaje de disponibilidad ("disponibles", "oportunidades", "hoy")
- El upsell solo aparece en mensajes de límite para usuarios free

---

## RESUMEN DE VARIABLES REQUERIDAS

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `{dice1}`, `{dice2}` | Valores de los dados | 4, 6 |
| `{dice}` | Valor único (para dobles) | 5 |
| `{besitos}` | Besitos ganados en esta ronda | 1, 2 |
| `{total_besitos}` | Balance total del usuario | 42 |
| `{remaining}` | Oportunidades restantes | 3 |
| `{limit}` | Límite total diario | 10, 20 |
| `{current}` | Número de pregunta actual | 2 |
| `{question}` | Texto de la pregunta | "¿Cuál es...?" |
| `{correct_answer}` | Letra de respuesta correcta | "B" |
| `{streak}` | Racha de respuestas correctas | 3 |
| `{is_vip}` | Booleano para lógica condicional | True/False |

---

## EMOJIS PERMITIDOS

- 🎩 Lucien / elegancia
- 💋 Besitos
- 🎲 Dados
- ❓ Preguntas / Trivia
- ✅ Correcto
- ❌ Incorrecto
- 📜 Pregunta / Sabiduría
- ✨ Especial / VIP
- 🔙 Regresar

**Prohibido**: Emojis excesivos, caritas, animales, comida, u otros que rompan el tono elegante.
