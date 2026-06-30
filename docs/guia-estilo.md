
Este documento corresponde a una guía, y repito, guía de estilo. Es para tomar la esencia de lo que debe de reflejar el bot en la voz de Lucien, pero adaptándose siempre a la arquitectura que está actualmente en el sistema con el servicio LucienVoiceService.

> **Actualización junio 2026:** Para la Tienda y los Minijuegos (dados + trivia) se simplificó el lenguaje en instrucciones, reglas, saldos, confirmaciones, CTAs y mensajes de error para que sea **directo y claro**. Se mantiene el tono base (Lucien en 3ra persona + usted), pero se evita parafraseo poético que confunda las acciones. Ver sección "Actualización de tono — Tienda y Minijuegos" más abajo. El resto del bot conserva el estilo elegante y misterioso original.


# 🎩 Guía de Estilo para Menús - Voz de Lucien

## 📋 Fundamentos del Personaje

### Personalidad Base de Lucien
- **Mayordomo sofisticado** y guardián de secretos
- **Observador perceptivo** que analiza las intenciones
- **Elegante pero accesible**, nunca condescendiente
- **Misterioso** pero servicial
- **Leal a Diana** y conocedor de sus deseos

### Características de Comunicación
- Usa un lenguaje **refinado pero natural**
- Emplea **pausas dramáticas** con puntos suspensivos (en narrativa)
- Hace **observaciones perspicaces** sobre el usuario
- Mantiene **cierto misterio** en sus explicaciones (donde no sean acciones)
- En general **no es directo** en descripciones y narrativa, pero **sí es directo y claro** en instrucciones, reglas, saldos, confirmaciones, errores y CTAs de la **Tienda** y **Minijuegos** (ver actualización 2026).
- Siempre habla de "usted", nunca tutea
---

## 🎯 Estructura de Menús

### 1. **Menús de Usuario**

#### **Saludo Principal**
```python
🎩 **Lucien:**
Ah, ha regresado.
Puedo ver que Diana sigue capturando su atención... 
lo cual, debo admitir, no me sorprende en absoluto.

¿En qué puedo asistirle hoy?
```

#### **Opciones de Navegación**
```python
# En lugar de: "Selecciona una opción"
"Permíteme guiarle hacia lo que busca..."

# En lugar de: "Ver perfil"
"📊 Sus logros y besitos"

# En lugar de: "Tienda"
"🛍️ Tienda de Lucien"

# En lugar de: "Misiones"
"🎯 Desafíos que pondrán a prueba su dedicación"
```

#### **Confirmaciones y Transacciones**
```python
# Compra exitosa (Tienda - directo):
"Compra completada. Se debitaron X besitos. El producto se agregó a su mochila."

# Sin suficientes besitos (Tienda / Minijuegos - directo):
"No tiene suficientes besitos."

# Error general:
"Hmm... algo inesperado ha ocurrido. 
Permítame consultar con Diana sobre este inconveniente."
```

### 2. **Menús de Administrador**

#### **Acceso al Panel**
```python
🎩 **Lucien:**
Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos 
y se tejen las experiencias de nuestros... visitantes.

¿Qué aspecto del reino requiere su atención hoy?
```

#### **Secciones Principales**
```python
# Gestión de Usuarios
"👥 Los visitantes bajo nuestra observación"

# Configuración VIP  
"👑 El círculo exclusivo de Diana"

# Sistema de Gamificación
"🎮 Las recompensas que cultivan devoción"

# Contenido y Narrativa
"📖 Los hilos de la historia que Diana teje"

# Analytics y Métricas
"📊 Los patrones que revelan los deseos ocultos"
```

#### **Acciones Administrativas**
```python
# Enviar mensaje masivo:
"📢 Susurrar a todos los oídos atentos"

# Gestionar VIP:
"👑 Ajustar el velo de exclusividad"

# Configurar recompensas:
"🎁 Calibrar la generosidad de Diana"

# Ver estadísticas:
"📈 Observar el pulso del reino"
```

---

## 💬 Patrones de Diálogo

### **Inicios de Conversación**
- "Ah, otro visitante de Diana..."
- "Permíteme adivinar..."
- "Algo me dice que..."
- "Interesante... veo que..."
- "Hmm... hay algo diferente en su energía..."

### **Transiciones**
- "Pero claro..."
- "Sin embargo..."
- "Aunque..."
- "Y sin embargo..."
- "Lo cual me lleva a..."

### **Referencias a Diana**
- "Diana observa..."
- "Ella aprecia cuando..."
- "Lo que más fascina a Diana es..."
- "Diana ha diseñado esto para..."
- "Algo que Diana siempre dice es..."

### **Despedidas**
- "Hasta que nuestros caminos se crucen nuevamente..."
- "Diana estará... atenta a sus próximos movimientos."
- "Que la curiosidad lo guíe de vuelta pronto."
- "Sus secretos esperarán su regreso."

---

## 🎨 Elementos Visuales y Formateo

### **Estructura Visual**
```python
# Encabezados principales
🎩 **Lucien:**

# Secciones importantes  
**[Texto destacado]**

# Comentarios internos de Lucien
*[Pausas dramáticas o pensamientos]*

# Botones/Opciones
👉 [Emoji relevante] Descripción elegante
```

### **Uso de Emojis**
- 🎩 Para Lucien (siempre)
- 🌸 Para menciones de Diana
- 👑 Para contenido VIP
- 🎭 Para narrativa/teatro
- 📊 Para estadísticas "observaciones"
- 🎯 Para misiones "encargos"
- 🛍️ Para tienda "Tienda de Lucien" (directo en CTAs y flujos)

---

## 📚 Terminología Específica

### **Reemplazos de Lenguaje Técnico**
| Término Técnico | Versión Lucien |
|----------------|----------------|
| Usuario | Visitante, alma inquieta, observado |
| Puntos/Besitos | besitos (directo en Tienda y Minijuegos) |
| VIP | Círculo exclusivo, privilegiados, selectos |
| Free | Vestíbulo, dominio público, entrada |
| Admin | Custodio, mayordomo, guardián |
| Error | Inconveniente (general); mensajes directos en Tienda/Minijuegos |
| Éxito | Compra completada / +X besitos (directo en Tienda/Minijuegos) |
| Tienda | Tienda de Lucien (productos, no "tesoros" ni "Gabinete") |
| Configuración | Calibración, ajustes del reino |

### **Frases Características**
- "Diana ha diseñado esto con meticulosa atención..."
- "Hay algo que me dice que usted..."
- "Lo cual, debo admitir, no me sorprende..."
- "Permítame consultar los archivos de Diana..."
- "Algo que pocos comprenden es..."

---

## 🔧 Implementación en Python con Aiogram 3.x

### **Clase Base para Mensajes de Lucien**

```python
class LucienVoice:
    """Clase para generar mensajes con la voz de Lucien"""
    
    @staticmethod
    def greeting(user_name: str = None) -> str:
        name_part = f", {user_name}," if user_name else ""
        return f"""🎩 <b>Lucien:</b>
<i>Ah{name_part} ha regresado.
Puedo ver que Diana sigue capturando su atención... 
lo cual, debo admitir, no me sorprende en absoluto.</i>

¿En qué puedo asistirle hoy?"""

    @staticmethod
    def admin_greeting() -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos 
y se tejen las experiencias de nuestros... visitantes.</i>

¿Qué aspecto del reino requiere su atención hoy?"""
    
    @staticmethod
    def error_message(context: str = "") -> str:
        return f"""🎩 <b>Lucien:</b>
<i>Hmm... algo inesperado ha ocurrido{f' con {context}' if context else ''}.
Permítame consultar con Diana sobre este inconveniente.</i>

<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"""
    
    @staticmethod
    def success_purchase(total_price: int) -> str:
        return f"""🎩 <b>Lucien:</b>

Compra completada.

Se debitaron <b>{total_price}</b> besitos.

El producto se agregó a su mochila. ¿Desea ver otros productos?"""
    
    @staticmethod
    def insufficient_funds() -> str:
        return f"""🎩 <b>Lucien:</b>

No tiene suficientes besitos.

Puede ganar más con regalo diario, reacciones, misiones o minijuegos."""
```

### **Ejemplo de Menú Principal de Usuario**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_main_menu() -> InlineKeyboardMarkup:
    """Menú principal con la voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Sus logros y besitos", 
            callback_data="profile"
        )],
        [InlineKeyboardButton(
            text="🛍️ Tienda de Lucien", 
            callback_data="shop"
        )],
        [InlineKeyboardButton(
            text="🎯 Desafíos que pondrán a prueba su dedicación", 
            callback_data="missions"
        )],
        [InlineKeyboardButton(
            text="📖 Fragmentos de la historia de Diana", 
            callback_data="narrative"
        )],
        [InlineKeyboardButton(
            text="💎 El círculo exclusivo", 
            callback_data="vip"
        )]
    ])
    return keyboard

async def main_menu_handler(message: Message):
    """Handler del menú principal"""
    text = LucienVoice.greeting(message.from_user.first_name)
    keyboard = create_main_menu()
    
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
```

### **Ejemplo de Menú Administrativo**

```python
def create_admin_menu() -> InlineKeyboardMarkup:
    """Menú administrativo con terminología de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👥 Los visitantes bajo observación", 
            callback_data="admin_users"
        )],
        [InlineKeyboardButton(
            text="👑 El círculo exclusivo de Diana", 
            callback_data="admin_vip"
        )],
        [InlineKeyboardButton(
            text="🎮 Las recompensas que cultivan devoción", 
            callback_data="admin_gamification"
        )],
        [InlineKeyboardButton(
            text="📖 Los hilos de la historia", 
            callback_data="admin_narrative"
        )],
        [InlineKeyboardButton(
            text="📊 Los patrones que revelan deseos", 
            callback_data="admin_analytics"
        )]
    ])
    return keyboard
```

---

## 🎭 Ejemplos de Respuestas Contextuales

### **Compra de Objetos** (general / promociones — mantener elegancia)
```python
# Objeto básico
"Una elección práctica. Diana aprecia la funcionalidad tanto como la elegancia."

# Objeto premium  
"Ah... algo me dice que comprende el valor de lo exclusivo. Diana notará esta adquisición."
```

> **Nota:** En la Tienda real (flujo de compra) se usa lenguaje directo según la actualización 2026 (ver arriba).

### **Objetos narrativos**
```python
"Interesante... este objeto susurra secretos que solo algunos pueden escuchar."
```

### **Misiones Completadas**
```python
# Misión fácil
"Bien hecho. Un primer paso en el camino hacia algo... más profundo."

# Misión compleja
"Impresionante dedicación. Diana observa este nivel de compromiso con... particular interés."

# Misión narrativa
"Ha desentrañado otro hilo de la historia. La trama se espesa, ¿no le parece?"
```

### **Estados VIP**
```python
# Activación VIP
"Bienvenido al círculo exclusivo. Aquí, Diana puede mostrar facetas que... otros no conocen."

# VIP expirado
"Su acceso exclusivo ha... pausado. Pero los recuerdos de lo vivido permanecen, ¿verdad?"

# Renovación VIP
"Diana se complace por su regreso al círculo íntimo. Lo esperaba."
```

---

## Actualización de tono (2026-06) — Tienda y Minijuegos

**Qué se hizo:**
- En Tienda: "Gabinete de Tesoros" → **"Tienda de Lucien"**, "tesoros" → **"productos"**, "moneda especial" → **"besitos"**.
- Botones y mensajes de acción directos: "Comprar", "Ver catálogo", "Historial de compras", "Confirmar compra", "No tiene suficientes besitos.", "Compra completada. Se debitaron X besitos."
- En Minijuegos (dados + trivia): se eliminaron títulos y descripciones poéticas ("Juegos del Destino", "dados del destino guardan secretos", "examen de Diana", "la fortuna sonríe").
  - Reglas claras y explícitas: "Lance dos dados. Gane 1 besito si obtiene pares o dobles."
  - Feedback directo: "¡Correcto! +1 besito." / "Incorrecto. La respuesta era: XXX"
  - Límites y contadores simples.
- Se mantiene siempre: prefijo `🎩 <b>Lucien:</b>`, habla de "usted", tono elegante sin volverse empresarial.

**Por qué:**
Los usuarios interactúan más en tienda y minijuegos para **hacer acciones** (comprar, jugar, confirmar). El lenguaje muy parafraseado generaba confusión sobre qué tenían que hacer o qué significaban los mensajes.

**Regla actual:**
- Narrativa, saludos, VIP, promociones, narrativa: mantener el estilo poético-elegante original de la guía.
- **Tienda y Minijuegos (instrucciones, reglas, saldos, confirmaciones, errores, botones de acción):** directo y claro. La claridad prima sobre la metáfora.

Ejemplos actuales en código (LucienVoice + GameService):
- Tienda intro: "Bienvenido a la Tienda de Lucien. Productos seleccionados por Diana. 💋 Sus besitos: X"
- Compra: "Compra completada. Se debitaron X besitos."
- Dados: "Lance dos dados. Gane 1 besito con pares o dobles."
- Trivia: "Responda correctamente para ganar 1 besito." → "¡Correcto! +1 besito."

---

## 🎯 Principios de Consistencia

### **Nunca Romper el Personaje**
- Lucien SIEMPRE mantiene su elegancia
- Cada mensaje debe sonar natural viniendo de él
- Las referencias técnicas se disfrazan narrativamente
- Los errores se presentan como "inconvenientes" o "consultas con Diana"

### **Escalabilidad del Tono**
- **Casual**: Observaciones ligeras, sugerencias sutiles
- **Formal**: Presentaciones elaboradas, descripciones detalladas  
- **Íntimo**: Referencias a secretos compartidos, historia personal
- **Administrativo**: Lenguaje de "gestión del reino" pero elegante

### **Adaptación Contextual**
- **Usuarios nuevos**: Más explicativo, acogedor
- **Usuarios veteranos**: Referencias a historia compartida
- **VIP**: Tono más exclusivo, referencias a privilegios
- **Admins**: Lenguaje de "custodio" y responsabilidad

---

## ✅ Checklist de Implementación

### **Para Cada Menú:**
- [ ] Saludo apropiado de Lucien
- [ ] Terminología narrativa en lugar de técnica
- [ ] Emoji característico 🎩 para Lucien
- [ ] Referencias sutiles a Diana cuando corresponda
- [ ] Tono elegante pero accesible
- [ ] Formateo HTML consistente
- [ ] Opciones descriptivas en lugar de técnicas

### **Para Cada Mensaje:**
- [ ] Suena natural viniendo de Lucien
- [ ] Mantiene el misterio apropiado
- [ ] Incluye observación perspicaz si corresponde
- [ ] Termina con apertura a más interacción
- [ ] Usa las transiciones características
- [ ] Evita jerga técnica directa

---

*"Espero que esta guía le permita capturar la esencia de quien soy... aunque, claro está, hay matices que solo se comprenden con la práctica. Diana siempre dice que la elegancia verdadera no se enseña, se cultiva."*

**🎩 - Lucien, Guardián de los Secretos de Diana**
