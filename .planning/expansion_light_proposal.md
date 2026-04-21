# Propuesta Light de Gamificación - Engagement Anónimo

## Visión

Extender el sistema de gamificación existente con **dinámicas ligeras** que:
-usen lo que ya existe (misiones, recompensas, narrativa)
-aumenten el engagement sin crear un "juego paralelo"
-sean 100% anónimas (sin interacción entre usuarios)

---

## Lo que YA existe y podemos robustecer

| Sistema | Estado | Cómo mejorarlo |
|---------|--------|--------------|
| Besitos | ✅ Completo | Generación pasiva + bonus por racha |
| Misiones | ✅ Completo | Más tipos, mejoradas por acciones idle |
| Recompensas | ✅ Completo | Entrega automática al completar misiones |
| Narrativa | ✅ Completo | Consecuencias en incursiones simples |
| Daily Gift | ✅ Completo | Racha de reclamos consecutivos |
| Canales | ✅ Completo | Acceso según tier VIP |

---

## Características Propuestas (Versión Light)

### 1. Generación Pasiva de Besitos (IDLE LIGHT)

**Concepto**: Los besitos se generan pasivamente mientras el usuario no esté activo.
- Máximo acumulable: 8 horas (respetando el daily gift)
- Usuario debe "reclamar" los besitos generados
- Cada reclaim suma a su racha de daily gift

**Integración con existente**:
- NO nueva moneda (usa Besitos)
- NO nueva tabla (extiende BesitoBalance)
- NO nuevo servicio (extiende BesitoService)

```python
# En BesitoBalance existente, agregar campos:
# - pending_besitos: besitos generados offline
# - last_claim_at: timestamp del último reclaim
# - auto_claim_on_login: booleano
```

### 2. Racha de Engagement (STREAKS MEJORADOS)

**Concepto**: Sistema de rachas que recompensa consistencia:
- Racha diaria: días consecutivos reclamando daily gift
- Racha de misiones: misiones diarias completadas
- Racha de visita: días consecutivos interactuando con el bot

**Recompensas por racha**:
- 7 días: +50 besitos bonus
- 14 días: +150 besitos bonus
- 30 días: +500 besitos + posibilidad de acceder a contenido exclusivo

**Integración**:
- Extend `DailyGiftClaim` con racha
- Nueva misión tipo: `DAILY_VISIT_STREAK`

### 3. Eventos Globales Anónimos (SIN INTERACCIÓN)

**Concepto**: Metas comunitarias que todos pueden contribuir anónimamente:
- "La comunidad ha enviado X besitos hoy"
- "Acumulamos X mensajes en el canal esta semana"
-Meta de besitos collective para desbloquear recompensas

**Anonimato**: Solo se muestra el total, nunca quién contribuyó qué.

**Integración**:
- Extender `GlobalEvent` (propuesto en expansión) o crear simple en `BroadcastService`
- No requiere новые таблицы, puede ser lógica en memoria/Redis

### 4. Statísticas Personales Anónimas

**Concepto**: Mostrar al usuario cómo se compara con "otros visitantes":
- "Tienes más besitos que el 65% de los visitantes"
- "Tu racha está en el top 20%"
- "Has completado más misiones que el promedio"

**Cómo**: Comparación por percentiles, no leaderboard.
- No muestra nombres
- No muestra ranking específico
- Solo percentiles

**Integración**: Nuevo método en `BesitoService` / `MissionService`

### 5. Incursiones Narrativas Simples (EXTENSIÓN DE STORY)

**Concepto**: Usar los StoryNode existentes para "mini-incursiones":
- Un nodo narrativo que tiene opciones con consecuencias
- Elegir "aventurarte" o "retirarte"
- Consequences persistidas en UserStoryProgress

**No es un juego separado**: Es la narrativa existente con decisiones binarias.

**Integración**:
- NO nuevos nodos de historia
- NO nuevo sistema de energía
- Solo usar `StoryNode` con opciones predefined

### 6. Misión "Conexión Diaria" (MISIÓN NUEVA PERO EXISTENTE)

**Concepto**: Misión automática diaria:
- Visitar el bot 1 vez al día
- Reclamar daily gift
- Leer un mensaje broadcast

**Recompensa**: Besitos extra por completar las 3 acciones。

**Integración**: Nueva misión tipo `DAILY_CONNECTION`

---

## Lo que NO incluimos (OVERKILL)

| Característica | Razón |
|--------------|-------|
| Sistema Gacha completo | Complejo, requiere nueva经济体, no se integra bien |
| Incursiones con nodos complejos | Sobra, narrativa existente alcanza |
| Battle Pass | Requiere Telegram Stars, no es necesario |
| Leaderboards | Expone ranking, viola anonimeo |
| Múltiples monedas | "Atención" vs Besitos = confusión |
| Tiendas paralelas | La tienda existente alcanza |

---

## Arquitectura Sugerida

```
services/
  besito_service.py    ← + generate_passive(), claim_pending(), get_percentile()
  mission_service.py ← + streak tracking, new mission types
  daily_gift_service.py  ← + streak bonuses
  event_service.py    ← NEW: eventos globales anónima (lógica simple)

models/models.py
  BesitoBalance   ← + pending_besitos, last_claim_at
  DailyGiftClaim ← + streak_days, last_streak_reset

handlers/
  existing handlers ← + claim_pending on /start
```

---

## Migraciones Necesarias (MÍNIMO)

1. Agregar `pending_besitos` a `BesitoBalance`
2. Agregar `streak_days`, `last_streak_reset` a `DailyGiftClaim`
3. (Opcional) Nueva tabla `global_event_contributions` si hay objetivos complejos

---

## Prioridades de Implementación

| Prioridad | Característica | Esfuerzo |
|----------|--------------|----------|
| P1 | Generación pasiva de besitos | Bajo |
| P1 | Racha de daily gift | Bajo |
| P2 | Estadísticas percentiles | Bajo |
| P2 | Misión conexión diaria | Medio |
| P3 | Eventos globales | Medio |
| P3 | Incursiones narrativas simples | Alto (solo usar existente) |

---

## Voz y Mensajería

Todo funciona con la voz de Lucien:
- "Lucien ha notado tu ausencia..."
- "Tu persistencia es admirable..."
- "La comunidad ansía tu atención..."
- "Diana ha recibido muchos susurros esta semana..."

---

## Consideraciones de Privacidad

- TODOS los datos son anónimos
- NO hay leaderboards con nombres
- NO hay interacción entre usuarios
- NO se comparten estadísticas individuales
- Solo percentiles y totales colectivos