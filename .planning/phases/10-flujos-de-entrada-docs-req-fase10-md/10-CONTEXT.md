# Phase 10: Flujos de entrada - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Source:** PRD Express Path (docs/req_fase10.md)

<domain>
## Phase Boundary

Rediseñar los flujos de entrada a ambos canales para convertirlos de procesos automáticos/fríos en experiencias narrativas/rituales que aumenten percepción de exclusividad y retención.

**Scope incluye:**
1. **Canal Free (Los Kinkys)** — Nuevo flujo de 3 mensajes con delay y botones de redes sociales
2. **Canal VIP (El Diván)** — Nuevo flujo ritualizado de 3 fases antes de entregar el enlace

**Scope NO incluye:**
- Cambios al sistema de tokens o tarifas VIP (solo el *momento* de entrega del enlace)
- Cambios a la lógica de expiración de suscripciones
- Nuevos canales adicionales

</domain>

<decisions>
## Implementation Decisions

### Canal Free — Decisiones Bloqueadas

- Al recibir `ChatJoinRequest`, el bot **NO debe enviar el mensaje inmediatamente**. Debe esperar **30 segundos exactos** antes de enviar el mensaje ritual.
- Se debe usar un **job del scheduler** (APScheduler) para el delay de 30s, no `asyncio.sleep` en el handler.
- Mensaje 1 (después de 30s): texto exacto del PRD, con botones inline a redes sociales:
  - Instagram: https://www.instagram.com/srta.kinky
  - TikTok: https://www.tiktok.com/@srtakinky
  - X: https://x.com/srtakinky
- Mensaje 2 (si vuelve a solicitar estando pending): texto exacto del PRD. No debe incluir botones.
- Mensaje 3 (al ser aceptado): texto exacto del PRD, seguido del enlace de invitación al canal. Reemplaza `LucienVoice.free_access_approved()`.
- El mensaje de aprobación actual (`free_access_approved`) queda **obsoleto** y se reemplaza por el mensaje de bienvenida ritual.

### Canal VIP — Decisiones Bloqueadas

- El canje del token (`/start <token>`) **NO debe entregar el enlace VIP de inmediato**.
- El token se canjea en el momento de `/start` (la suscripción se crea), pero el usuario entra en estado `pending_entry`.
- Se agregan **dos nuevos campos al modelo User**:
  - `vip_entry_status` — enum/string: `null` | `"pending_entry"` | `"active"`
  - `vip_entry_stage` — integer: `null` | `1` | `2` | `3`
- Flujo de 3 fases con botones inline:
  - **Fase 1** (`stage=1` o al entrar con `pending_entry`): mensaje ritual + botón "Continuar" → avanza a `stage=2`
  - **Fase 2** (`stage=2`): mensaje de alineación de expectativas + botón "Estoy listo" → avanza a `stage=3`
  - **Fase 3** (`stage=3`): genera el invite link dinámico de un solo uso, envía mensaje final con el link, marca `vip_entry_status="active"`, `vip_entry_stage=null`
- Si el usuario abandona el flujo y vuelve a `/start` (sin argumentos o con el mismo token), **debe retomar desde la etapa actual** leyendo los campos de User.
- Si la suscripción expira antes de completar el flujo: se cancela el proceso, no se genera el enlace, y se informa al usuario que su acceso ha expirado.
- El enlace VIP solo se genera en Fase 3, usando `bot.create_chat_invite_link(member_limit=1)` como se hace actualmente en `common_handlers.py`.

### Decisiones de Arquitectura — A discreción de implementación

- Para el delay de 30s del canal free: crear un método en `ChannelService` o `SchedulerService` que programe un job de APScheduler.
- Para el flujo VIP: usar nuevos handlers en `vip_handlers.py` o `common_handlers.py` para los callbacks de fase. La lógica de avance de etapa debe ir en `VIPService`.
- Los textos exactos del PRD deben ir en `LucienVoice` siguiendo la convención existente (`@staticmethod`, return `str`, parse_mode="HTML").

### Bug Crítico Descubierto

- El scheduler `_process_pending_requests` actualmente corre solo una vez al día a las 9:00 AM (`trigger="cron", hour=9, minute=0`). Esto significa que las aprobaciones automáticas del canal free no funcionan en tiempo real. **Debe cambiarse a un intervalo corto** (ej: cada 30 segundos o 1 minuto) para que el flujo de entrada tenga sentido.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Handlers Actuales
- `handlers/free_channel_handlers.py` — `handle_join_request()` es el punto de entrada del canal free
- `handlers/common_handlers.py` — `cmd_start()` maneja `/start` con token VIP (líneas 21-88)
- `handlers/vip_handlers.py` — handlers de administración VIP; los nuevos handlers de flujo ritual deben ir aquí o en common

### Services
- `services/channel_service.py` — `create_pending_request()`, `get_pending_request()`, `approve_request()`
- `services/vip_service.py` — `redeem_token()`, `is_user_vip()`, `get_vip_channel()`
- `services/scheduler_service.py` — `_process_pending_requests()` y `SchedulerService.start()` para jobs de aprobación y delay

### Models
- `models/models.py` — `User`, `Channel`, `PendingRequest`, `Subscription`, `Token` (debe leerse para conocer columnas actuales)

### Voz y UI
- `utils/lucien_voice.py` — métodos existentes como `free_request_received()`, `free_access_approved()`, `vip_activated()`
- `keyboards/inline_keyboards.py` — convenciones de botones inline

### Arquitectura y Reglas
- `@architecture.md` — capas handlers/services/models, prohibiciones
- `@rules.md` — límite 50 líneas, naming, logging
- `handlers/CLAUDE.md` — reglas de handlers
- `services/CLAUDE.md` — reglas de services

</canonical_refs>

<specifics>
## Specific Ideas

### Mensajes Canal Free (textos exactos)

**Mensaje 1 (tras 30s de solicitud):**
```
🎩 Lucien:
Ah… alguien ha llamado a la puerta.
Su solicitud para entrar a <b>Los Kinkys</b> ha sido registrada.
Diana siempre nota cuando alguien decide cruzar hacia su mundo… 
Mientras su acceso se prepara, hay algo que puede hacer.
Las redes de Diana no son simples perfiles.
Obsérvela.
Escuche el tono.
Empiece a entender el juego.
💡 No necesita quedarse aquí esperando.
Cuando todo esté listo, yo mismo vendré a buscarle.
Mientras tanto… aquí puede seguir su rastro 👇
(botones de redes)
```

**Mensaje 2 (solicitud repetida estando pending):**
```
🎩 Lucien:
Veo que el deseo de entrar no ha disminuido…
Su acceso a Los Kinkys ya está en movimiento.
Puede cerrar este chat con tranquilidad.
Cuando llegue el momento, no tendrá que buscar la puerta.
La puerta se abrirá.
```

**Mensaje 3 (bienvenida al aprobar):**
```
🎩 Lucien:
Listo.
Diana ha permitido su entrada.
Bienvenido a Los Kinkys.
Este no es el lugar donde ella se entrega.
Es el lugar donde comienza a insinuarse…
y donde algunos descubren que ya no quieren quedarse solo aquí.
El enlace está abajo.
Tiene 24 horas para cruzar antes de que se cierre de nuevo.
Entre con intención.
👇
(link de invitación)
```

### Mensajes Canal VIP (textos exactos)

**Fase 1:**
```
🎩 Lucien:
Veo que ha dado el paso que muchos contemplan… y pocos toman.
Su acceso al Diván de Diana está siendo preparado.
Este no es un espacio público.
No es un canal más.
Y definitivamente no es para quien solo siente curiosidad.
Antes de entregarle la entrada, hay algo que debe saber…
```
Botón: `[ Continuar ]`

**Fase 2:**
```
🎩 Lucien:
El Diván no es un lugar donde se mira y se olvida.
Es un espacio íntimo, sin filtros, sin máscaras.
Aquí Diana se muestra sin la distancia de las redes,
y eso exige discreción, respeto y presencia real.
Si ha llegado hasta aquí solo para observar de paso…
este es el momento de detenerse.
Si entiende lo que significa entrar… entonces sí.
```
Botón: `[ Estoy listo ]`

**Fase 3:**
```
🎩 Lucien:
Entonces no le haré esperar más.
Diana le abre la puerta al Diván.
Este acceso es personal.
No se comparte.
No se replica.
Y se cierra cuando el vínculo termina.
Tiene 24 horas para usar el enlace.
Entre con intención.
👇
```
Seguido del enlace de invitación.

</specifics>

<deferred>
## Deferred Ideas

None — PRD covers phase scope.

</deferred>

---

*Phase: 10-flujos-de-entrada-docs-req-fase10-md*
*Context gathered: 2026-03-31 via PRD Express Path*
