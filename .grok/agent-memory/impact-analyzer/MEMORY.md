# Impact Analyzer Memory Index

- [Broadcast Link Buttons ITEM 1](broadcast-link-buttons-item1.md) — Catalog model + service CRUD only; no handler/wizard/send changes; FK decision flagged; gold tests identified
- [Broadcast Link Buttons ITEM 2](broadcast-link-buttons-item2.md) — Wizard integration (after reactions), FSM states, create_broadcast_message signature, build_send_reaction_markup or new helper, preview, confirm_and_send, refresh_reaction_markup_counts; single choice UI; 173 LOC confirm_and_send flagged; admin UI gap; gold tests listed
- [VIP Forward Activation](item-vip-forward-activation.md) — Admin forward → forward_origin user ID → confirm → tariff → grant_vip_from_admin_forward (reuse grant_vip_from_tariff + DM + token fallback); FSM in vip_handlers; pure extract_forwarded_user_id; 1 pool item; channels-VIP critical; gold tests listed
- [Pool34 Item1 User Flows Reality](pool34-item1-user-flows-reality.md) — Story (crit#2 quiz/archetype/advance/achievements) + backpack fulfillment/VIP + mission claim/list; 28/15/11 get_service patches; golds listed; tight tests-only per pool33 precedent
