# Store Domain — Fulfillment Catalog

## Services

- `StoreService` — catálogo, carrito, `complete_order` (atómico)
- `FulfillmentService` — post-commit fulfillment (NUNCA dentro de `complete_order` tx)

## User-facing copy (tienda)
Mensajes al visitante en tienda (handlers/store_user_handlers + LucienVoice) usan lenguaje **directo** desde la actualización de tono junio 2026:
- "Tienda de Lucien" (no "Gabinete de Tesoros")
- "productos" / "besitos" (no "tesoros" / "moneda especial")
- Instrucciones y CTAs claras: precio explícito, "Comprar", confirmaciones directas, "No tiene suficientes besitos", etc.
Ver `docs/guia-estilo.md` y `utils/lucien_voice.py` (store_* methods).

## Contrato atómico

`complete_order`: debit + stock FOR UPDATE + COMPLETED en un commit.
Fulfillment: `create_fulfillments_for_order` + `process_order_fulfillments` solo post-commit.

## Fulfillment kinds

PACKAGE, VIP_GRANT, STORY_UNLOCK, PRIVILEGE_*, WAITLIST_ENTRY, MANUAL queue kinds.

## Deferred v1.1

`notify_early_access_holders(drop_id)` — stub/log only; integración Promotions pendiente.