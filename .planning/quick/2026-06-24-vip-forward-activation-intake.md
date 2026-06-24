# SCOPE INTAKE — VIP Forward Activation (hardener-agile --effort 5)

**Date:** 2026-06-24
**Orchestrator:** hardener-agile

## Objetivo
Implementar activación de VIP (nuevo suscriptor o renovación) vía reenvío de mensaje:
- Administrador reenvía al bot un mensaje proveniente de un usuario candidato a VIP.
- Bot identifica el ID del usuario original (usando forward_from / forward_origin).
- Solicita confirmación al admin (incluyendo selección de tarifa para duración).
- Si aprueba, activa VIP automáticamente usando el flujo interno de Token + redeem (siguiendo regla "siempre vía token").
- Envía directamente al usuario (bot.send_message) el mensaje de bienvenida + enlace de invitación nativa de Telegram (1-uso, member_limit=1) al canal VIP.
- Elimina necesidad de que el usuario active manualmente un deep link /start=token.
- Mantiene flujo manual (tokens + deep link) completamente intacto como fallback.
- Si el envío directo falla (usuario bloqueó el bot u otro error Telegram), notifica al administrador para que genere/proporcione el enlace manual.

## Fuente
Petición explícita del usuario en /hardener-agile --effort 5 + descripción detallada.

## Ítems del pool (≤4)
- **1 ítem**: VIP forward activation flow (feature cohesiva, medium scope)
  - Incluye: detección de forwarded user msg por admin, confirm+tariff, grant, direct send + fallback notify.
  - No se parte porque el flujo es atómico desde identificación hasta notificación.

## Restricciones (non-negotiable)
- 0 impacto en atomicidad de redeem_token / cross service contracts / EventBus (MUST NOT mutate en observers).
- Seguir arquitectura: handlers/ SOLO routing + exactamente 1 llamada a service (usar get_service si aplica, o patrón existente).
- Funcs <=50 LOC, naming "verbo + contexto + resultado".
- Logging: f"{__name__} | accion | user_id=... | resultado=..."
- Voz de Lucien: 3ra persona, elegante.
- Proteger 3 sistemas críticos: gamificación, narrativa, canales-VIP (este item toca fuertemente canales-VIP).
- Mantener flujo token/deep-link existente 100% funcional.
- Usar preferentemente grant_vip_from_tariff + create_vip_invite_link existentes.
- Effort=5: review loop estricto con múltiples reviewers (general + specialists) hasta **0 issues** (bug/suggestion/nit) en ronda completa.
- No hardcodear IDs, secrets, etc.
- Usar transacciones donde ya hay (redeem ya usa).

## Sistemas sensibles
- canales-VIP (Subscription, redeem, invite links, ban/unban via scheduler indirecto)
- VIPService.redeem_token (FOR UPDATE, extensión de subs, emisión EVENT_VIP_ACTIVATED post-commit best effort)
- create_chat_invite_link + manejo de fallos (allow_fallback en otros sitios)
- Envío de mensajes directos a usuarios + detección de "bot was blocked by the user"
- Admin authorization (is_admin)
- FSM para wizard de confirmación si se usa

## Artefactos esperados
- .planning/quick/.../PLAN.md + *-SUMMARY.md
- Cambios en: handlers/vip_handlers.py (nuevo handler mensaje forward + callbacks de confirm), posiblemente utils/lucien_voice.py (nuevos strings), keyboards si nuevo confirm UI, servicios/vip_service.py solo si extensión mínima (prefer NO, reuse)
- Tests: actualizar/añadir unit para grant paths, integration para forward flow, re-correr golds vip_* , cross atomicity si aplica
- Documentación mínima en decisions o CLAUDE si necesario
- Review reports en agent-memory/
- 0 violaciones arch críticas, tests "suite protege adecuadamente", review final 0 issues

## Notas para pipeline
- Intake limpio, feature nueva (no hardening puro).
- Usar effort 5 para review final.
- Slug sugerido: vip-forward-activation
- Al final del pool lanzar documentador (no --hardening así que no forzar ROADMAP phrase, pero reportar en agent-memory)
- Cualquier ambigüedad de "selección de tarifa" debe resolverse por planner/executor usando precedentes (tariffs_keyboard existente).

## Pool status inicial
POOL: VIP-Forward-Activation
ITEM 1/1: VIP forward activation — [pending]
Paso actual: intake (complete) → 1-impact
Review round: 0
Effort: 5
