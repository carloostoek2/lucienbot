# Store Domain — Fulfillment Catalog

## Services

- `StoreService` — catálogo, carrito, `complete_order` (atómico)
- `FulfillmentService` — post-commit fulfillment (NUNCA dentro de `complete_order` tx)

## Contrato atómico

`complete_order`: debit + stock FOR UPDATE + COMPLETED en un commit.
Fulfillment: `create_fulfillments_for_order` + `process_order_fulfillments` solo post-commit.

## Fulfillment kinds

PACKAGE, VIP_GRANT, STORY_UNLOCK, PRIVILEGE_*, WAITLIST_ENTRY, MANUAL queue kinds.

## Deferred v1.1

`notify_early_access_holders(drop_id)` — stub/log only; integración Promotions pendiente.