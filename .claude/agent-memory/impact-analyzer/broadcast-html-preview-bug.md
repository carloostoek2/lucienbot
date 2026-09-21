---
name: broadcast-html-preview-bug
description: Impact map for the broadcast HTML normalization + preview truncation bug (prod incident 2026-09-21, unclosed tag kills wizard step 6/7)
metadata:
  type: project
---

# Bug de HTML/preview en broadcast (incidente prod 2026-09-21, user_id=8788842027)

Dos defectos en la ruta de envío de broadcast:

1. `handlers/broadcast_handlers.py:211` (`build_broadcast_preview_text`) truncaba a ciegas
   `preview_text[:500] + "..."`. Si el corte cae dentro de una etiqueta, Telegram responde
   `can't parse entities: Unsupported start tag` y el wizard muere en el paso 6 de 7 (Preview);
   el broadcast nunca se envía.
2. `services/broadcast/text_format.py:38` (`resolve_broadcast_text_to_html`): si el cuerpo
   contiene AL MENOS una etiqueta de la whitelist, devuelve `body` entero sin escapar, así que
   `<3`, `5 < 10`, `<br>` crudos llegan a Telegram con `parse_mode="HTML"`.

**Why:** es el entry point del loop reacción→besitos (reacciones que pagan besitos dependen de que
el mensaje exista en el canal) y de la entrega de contenido a canales. Bug de dominio money-adjacent.

**How to apply:** al analizar/tocar esta ruta, recordar: (a) `BroadcastMessage.text` se escribe pero
NADA lo lee (verificado: 0 lecturas de `broadcast.text` en el repo), así que cambiar la normalización
no requiere migración ni rompe lectores; (b) `tests/unit/test_broadcast_text_format.py::test_manual_html_preserved`
pinea el comportamiento actual de pass-through y DEBE actualizarse junto con el fix; (c) no existen
tests para `build_broadcast_preview_text`, `show_broadcast_preview` ni `process_broadcast_text`.

Ver [[broadcast-link-buttons-item1]] (mismo dominio, wizard/paso de preview).
