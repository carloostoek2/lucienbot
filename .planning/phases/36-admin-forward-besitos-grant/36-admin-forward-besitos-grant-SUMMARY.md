# SUMMARY: Item 36 — admin-forward-besitos-grant

**Date:** 2026-06-29  
**Pool:** 1/1 (feature request, fuera de HARDENING_ROADMAP clusters)

## Outcomes

- Reenvío admin ya no activa VIP automáticamente: muestra menú **Activar VIP | Otorgar besitos | Cancelar**.
- Rama besitos: cantidad → confirmar → `grant_manual_admin_besitos` (`TransactionSource.ADMIN`) → notificación visitante (best-effort).
- Rama VIP: sin cambio de grant; entrada vía botón tras menú.
- `BesitoService.grant_manual_admin_besitos` + `MAX_ADMIN_BESITO_GRANT=10000`.

## Verifications

| Gate | Result |
|------|--------|
| impact-analyzer | Scope tight, 0 HIGH sin mitigar |
| arch-enforcer | **PASS WITH NOTES**, 0 critical |
| test-guardian | **suite protege adecuadamente** |
| pytest F5 | **111 passed** (vip_handlers + besito + golds) |
| self-check | PASSED |

## Files

- `handlers/vip_handlers.py`
- `keyboards/inline_keyboards.py`
- `services/besito_service.py`
- `tests/handlers/test_vip_handlers.py`
- `tests/unit/test_besito_service.py`
- `decisions.md` (append Item 36)

## Handoff

Item 36 closed. Pool de 1 completado (tests passing). Feature listo para uso en producción: Custodio reenvía mensaje al bot → elige acción.