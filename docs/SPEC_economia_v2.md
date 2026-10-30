# Economía v2: topes, VIP corto, nurture y premio de racha (PR #12)

Origen: [PR #12](https://github.com/carloostoek2/lucienbot/pull/12), mergeado el 2026-10-29 (ítems 4, 3, 1 y 2 del informe de economía). Va encima de la migración de misiones del [PR #11](https://github.com/carloostoek2/lucienbot/pull/11).

## 1. Topes para valores editables por admin

`config/economy_limits.py` es la única fuente de los rangos permitidos.

- **Al guardar** se valida: si el valor está fuera de rango, no se guarda nada y el admin ve el rango permitido.
- **Al leer** se recorta: si en la BD ya hay un valor fuera de rango (por SQL manual o un script), se acredita el tope y el mensaje al usuario muestra el monto real acreditado.

| Campo | Valor en prod (2026-10-29) | Rango permitido |
|---|---|---|
| Regalo diario | 10 | 1–30 |
| Dados Free / VIP (jugadas por día) | 5 / 10 | 0–30 |
| Trivia Free / VIP, trivia simple Free / VIP, trivia VIP | 5 / 8, 5 / 8, 5 | 0–25 |
| Besitos de trivia por día Free / VIP | 10 / 15 | 0–50 |
| Besitos de trivia por semana Free / VIP | 50 / 70 | 0–250 |
| Valor de reacción (🥵 = 5) | 2 / 5 | 1–15 |
| Recompensa de misión (besitos) | 5 / 30 previstos | 1–100 |
| Racha: retiro / completa (nuevo) | 15 / 30 | 1–50 / 1–100 |

`MAX_ADMIN_BESITO_GRANT = 10000` no cambia. Se aplica en `DailyGiftService`, `BroadcastService` (emojis y crédito de reacción), `RewardService` (recompensas y entrega de besitos) y `TriviaConfigService`. Los handlers de admin muestran el rango en el prompt y en el rechazo.

## 2. Nurture solo para grants VIP de 7 días o más

- Los cinco sitios que emiten `EVENT_VIP_ACTIVATED` usan `vip_activated_payload(...)`: `{user_id, subscription_id, tariff_id, granted_days, is_extension}`.
- `nurture_service.on_vip_activated` no enrola si `granted_days < 7` (log `skipped_short_grant`). Si el payload no trae `granted_days`, toma la duración de la tarifa; si no se conoce, enrola como antes.
- La regla es por grant: 1 + 3 + 3 días no suman 7.

## 3. VIP corto (1 y 3 días)

Tarifas 15 y 12; productos 38 y 37.

- **Enlace de invitación:** `member_limit=1` y vence en `min(ahora + 7 días, fin del acceso)`. Si al acceso le quedan menos de 5 minutos, no se crea enlace. En accesos cortos no se usa el enlace permanente del canal.
- **Unban antes del enlace**, también en el grant interno, cuando el usuario no era VIP. Todos los unban usan `only_if_banned=True`; sin eso Telegram expulsa a un miembro actual.
- **Vencimiento:** el sweep de suscripciones vencidas (`expire_subscriptions`) pasa de cada 6 h a cada 10 minutos. Como máximo queda ~10 minutos de acceso extra.
- **Recordatorio de 24 h:** se omite en VIP de 1 día. El de 3 días lo conserva, y un VIP de 30 días que suma 1 día también.
- **Copy según duración** (`LucienVoice.vip_direct_access`): si el enlace vence con el acceso dice "(vence junto con su acceso)"; en VIP corto (≤3 días, no extensión) cierra con la línea "Entre hoy…".

## 4. El modo arriesgo de racha paga besitos

- **Oferta** al alcanzar un nivel: retirarse ahora con los besitos de retiro o seguir por los de completar. Botones "Continuar" y "Retirarse con {n} 💋".
- **Retirarse** paga el monto de retiro (15 por defecto). **Completar** paga el de completa (30 por defecto). Fallar en modo arriesgo no paga.
- **Completar** significa que, en modo arriesgo, la racha llega al umbral del último nivel de la promoción (`max(consecutive_required)`), haya o no códigos en ese nivel. Si el usuario deja de jugar sin fallar ni completar, no cobra.
- **Un solo pago por sesión** (retiro o completa), con `SELECT … FOR UPDATE` sobre `streak_sessions`. El crédito y las columnas `payout_*` se confirman en el mismo commit.
- El callback lleva `session_id`: un botón de otra sesión, de una sesión cerrada o un "Retirarse" después de "Continuar" no paga y muestra un alert. Los botones viejos sin `session_id` dejan de responder.
- Se corrigió que "Retirarse" no hacía commit. Las sesiones pagadas ya no se tratan como timeout, así que no se cancelan sus códigos conservados.
- Los premios usan la fuente nueva `TransactionSource.STREAK_REWARD` y no cuentan contra los topes diario y semanal de trivia. Los montos se editan en Configuración de trivia.

## Migración `20261029_streak_besitos`

- Agrega `STREAK_REWARD` al enum `transactionsource`.
- `streak_sessions` += `retired_at`, `completed_at`, `payout_besitos`, `payout_paid_at` (nullable).
- `trivia_config` += `streak_retire_besitos` (default 15) y `streak_complete_besitos` (default 30).
- Idempotente. El downgrade borra las columnas; el valor del enum queda.

## Rollout

1. Desplegar después del PR #11. El deploy corre `alembic upgrade head`.
2. Activar los productos VIP de 1 día (38) y 3 días (37) solo después del deploy.
3. Textos provisionales pendientes del Copywriter (en `utils/lucien_voice.py`): la línea "Entre hoy…" (`VIP_SHORT_DELIVERY_LINE`), el cierre de 2 semanas y del mes (`VIP_LONG_DELIVERY_LINE`), el alert del botón de racha ya no válido y los botones "Continuar" / "Retirarse con {n} 💋".
