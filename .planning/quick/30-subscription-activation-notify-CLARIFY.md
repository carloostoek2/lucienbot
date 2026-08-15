# SCOPE CLARIFICATION — Notificación de activación de suscripción

Fecha: 2026-08-15
Fuente: petición usuario (spec de desarrollo) + round de aclaración (`--clarify`)

## Objetivo
Notificar al administrador (Custodios) el estado de activación de tokens de suscripción,
diferenciando claramente éxito y fallo, vía mensaje directo de Telegram.

## Decisiones bloqueadas (respuestas del usuario — no re-abrir)
1. **Failure scope = TODOS los fallos** — notificar usado, expirado, inválido/inexistente,
   tarifa faltante y canal VIP no configurado. Sin filtrar por "ruido de usuario".
2. **Target = DM a cada Custodio** — loop sobre `bot_config.ADMIN_IDS` con try/except,
   copiando el patrón `_notify_admins_of_purchase` (`store_service.py:1411`).
3. **Identificación = id + username + nombre** — `user_id` + `@username` + `first_name`.
4. **Success scope = TODAS las activaciones VIP** — reutilizar el `EVENT_VIP_ACTIVATED`
   existente (sin evento nuevo de éxito). Notifica también grants internos (misiones,
   tienda, admin). Menos código, más visibilidad.

## Hechos de arquitectura (verificados)
- Éxito ya emite `EVENT_VIP_ACTIVATED` post-commit en `vip_service.py:294-299` (extensión)
  y `:341-345` (nueva suscripción); payload `{user_id, subscription_id}`.
- Fallo NO emite evento. `redeem_token` retorna `None` silenciosamente en:
  token inexistente (`:223`), USED (`:227`), EXPIRED (`:231`/`:235`), tarifa faltante (`:247`),
  canal VIP no configurado (`:317`).
- Duración = `Tariff.duration_days` (`models.py:130`); nombre legible = `Tariff.name`.
- EventBus: `services/event_bus.py` — `get_event_bus()`, `register()`, `emit()` (gather
  return_exceptions, nunca lanza), `schedule_emit()` para paths sync. Registro en `bot.py`
  `on_startup` (patrón `on_vip_activated` en `nurture_service.py:414`).

## Zonas grises delegadas al planner (no bloquean al usuario)
- Dónde vive el listener/helper de notificación (¿nuevo NotificationService, listener en
  `nurture_service`, o helper en VIP domain?).
- Punto(s) exacto(s) de emisión del evento de fallo (dentro de `redeem_token` en cada retorno
  `None` con razón; o desde el handler vía `validate_token`).
- Formato exacto del mensaje (voz de Lucien, diferenciación éxito/fallo clara).

## Invariantes a respetar
- Notificaciones best-effort: "MUST NOT mutate" (listeners del EventBus no tocan estado).
- 0 impacto en sistema crítico VIP (grant/revoke/activación) — solo observan y notifican.
- Handlers llaman exactamente 1 service; funciones ≤50 LOC; logging módulo|acción|user_id|resultado.
