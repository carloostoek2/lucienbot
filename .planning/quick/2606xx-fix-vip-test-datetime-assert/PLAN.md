# Plan: Fix broken test_complete_vip_flow (datetime tz + dead param)

**Created:** 2026 (current session)  
**Task (pequeño / ad-hoc):** Arreglar `tests/integration/test_vip_flow.py::TestVIPFlow::test_complete_vip_flow` que falla consistentemente con `TypeError: can't subtract offset-naive and offset-aware datetimes`. Limpiar fixture muerto. Seguir patrones existentes del proyecto para manejo de datetimes en tests VIP. Mantener scope mínimo.

**Contexto del problema (de review + exploración):**
- SQLite + SQLAlchemy `DateTime(timezone=True)` devuelve datetimes **naive** al cargar (aunque se guardan aware). Ver `_ensure_aware` en `services/vip_service.py:19-28` y comentarios en `models/CLAUDE.md`, `fases_refactor_testing.md`.
- El test calcula `expected_end = datetime.now(UTC) + timedelta(days=30)` (aware) **después** del redeem y hace `abs((subscription.end_date - expected_end)...)` sin normalizar.
- `subscription.end_date` post-`db.refresh()` es naive → TypeError siempre.
- Patrones rotos/fragiles similares existen en otros lugares, pero este es el que falla ya.
- Fixture `sample_admin` se pasa pero nunca se usa (línea 24).
- Este test duplica setup happy-path de `test_vip_complete_cycle.py` (mismo channel TG magic `-100999888777`, create via ChannelService + tariff + redeem + asserts básicos), pero para "pequeño" no se toca la duplicación.

**Exploración realizada (plan mode + subagent explore):**
- Usos de `_ensure_aware`, `now(UTC)`, end_date asserts en `vip_service.py`, todos los `tests/integration/test_vip*.py`, unit VIP, conftest.
- Patrones que **funcionan** (de `test_vip_flows.py`, `test_vip_complete_cycle.py`, `test_vip_subscription_lifecycle.py`, units):
  - Inline normalize: `end = sub.end_date; if end.tzinfo is None: end = end.replace(tzinfo=UTC)`
  - Capturar `now` **antes** de la acción que genera el end_date (redeem), luego delta con tolerancia pequeña (<5s).
  - Relative: `assert _ensure_aware(end) > captured - td` o `end > original_end` (para extensiones).
  - Duplicar helper `_ensure_aware` + `_now()` solo en tests complejos de flujos (test_vip_flows.py).
- El test actual usa import `from datetime import UTC, datetime, timedelta` (consistente dentro del archivo).
- Ningún uso de freezegun/time_machine en tests VIP (solo en reqs-dev).
- Queries en service a veces usan `.replace(tzinfo=None)` intencionalmente para compat SQLite en filtros.

**Opciones consideradas y trade-offs (para pequeño):**
1. **Mínimo + robusto (recomendado):** Solo editar el método del test. Capturar `now_before` justo antes de `redeem_token`. Normalizar `subscription.end_date` inline (patrón de complete_cycle y subscription_lifecycle). Usar delta con tolerancia <5s + mensaje claro. Quitar `sample_admin` del signature.  
   - Pros: 1 archivo, ~5-8 líneas cambiadas, sigue exactamente patrones existentes, desbloquea el test inmediatamente, sin nuevos helpers ni exposición de _ensure_aware privado.  
   - Cons: Repite 3 líneas de normalize (como hacen otros tests).  
2. Duplicar `_ensure_aware` + helpers en este archivo de test (como hace test_vip_flows.py).  
   - Pros: Reutilizable dentro del archivo para otros tests.  
   - Cons: Más código para un fix pequeño; este archivo tiene tests más simples.  
3. Hacer `_ensure_aware` público en VIPService o mover a utils/test helpers en conftest.  
   - Pros: DRY a largo plazo.  
   - Cons: Cambios en service (no "pequeño"), scope creep, requiere discusión de API. Fuera de alcance aquí.  
4. Usar solo `assert (end - before).days == 30` o > checks relativos (sin abs delta exacto).  
   - Pros: Más simple.  
   - Cons: Pierde la intención original del test (verificar que se aplicaron los ~30 días de la tarifa). Mejor mantener delta con tolerancia.

**Decisión:** Opción 1 (mínimo). Captura + normalize inline + delta estricto (<5s, como en test_vip_flows renewal). Esto hace que el assert valide el efecto real (duración aplicada) de forma que no puede fallar por tz.

**Cambios requeridos (solo este archivo):**

### tests/integration/test_vip_flow.py

1. **Signature del test (línea 24):** Quitar parámetro muerto.
   ```python
   def test_complete_vip_flow(self, db_session, sample_user):  # sin sample_admin
   ```

2. **Sección de verificación de fecha (reemplazar ~82-84):** Usar patrón defensivo.
   ```python
   # 9. Verificar fecha de expiración (30 días desde el now del redeem)
   now_before_redeem = datetime.now(UTC)
   # ... (el redeem ya está arriba)
   user_subscription = ...
   # ...
   end_date = subscription.end_date
   if end_date.tzinfo is None:
       end_date = end_date.replace(tzinfo=UTC)
   expected_end = now_before_redeem + timedelta(days=30)
   delta = abs((end_date - expected_end).total_seconds())
   assert delta < 5, f"end_date drift too high: {delta}s (expected ~30d from redeem time)"
   ```

   (Mantener el resto del test idéntico: creates de channel/tariff/token/validate/redeem, asserts de IDs por contrato, USED, is_vip, get_sub, etc.)

**Actualizar docstring de clase si ayuda (opcional, menor):** El "DESIRED CONTRACT" ya menciona datetimes aware explícitamente en otros fixtures — se puede dejar.

**Testing / verificación post-fix:**
- `python -m pytest tests/integration/test_vip_flow.py::TestVIPFlow::test_complete_vip_flow -q --tb=short -o "addopts="`
- El módulo completo del archivo.
- (Opcional smoke) `-k "vip and (flow or complete or redeem)"` para no romper otros.
- Confirmar que no hay más TypeError y que el delta pasa (verifica duración).
- Si pytest emite warning por unused fixture, se resuelve.
- (En GSD) ruff check + cualquier gate de quick task.

**Ejecución vía GSD (después de aprobación de este plan):**
Dado que es fix pequeño/ad-hoc de test (sin ambigüedad de arquitectura, sin prod logic):
- Invocar `/gsd-quick --validate "fix broken datetime tz assert + remove dead sample_admin in tests/integration/test_vip_flow.py::TestVIPFlow::test_complete_vip_flow"`
  (o equivalente con gsd-sdk / terminal según setup).
- Esto creará `.planning/quick/YYYYMMDD-.../PLAN.md` (o usará contexto), ejecutará, actualizará STATE.md "Quick Tasks Completed", commit atómico.
- Si se quiere más calidad: agregar `--discuss` o `--full` (pero para pequeño no necesario).
- No usar edits directos fuera de GSD.

**Criterios de éxito:**
- Test pasa limpio (sin TypeError, delta <5s).
- Fixture muerto eliminado (sin warnings innecesarios).
- Assert sigue protegiendo el contrato de duración + IDs (puede fallar si se rompe la lógica de redeem).
- Cambios <10 líneas netas.
- Cero impacto en prod / otros tests.
- Cumple reglas del proyecto (tests usan patrones ya establecidos en VIP domain, logging no aplica aquí, handlers/services no tocados).

**Fuera de scope (para mantener "pequeño"):**
- Refactor/dedup de los múltiples tests VIP (test_vip_complete_cycle, test_vip_flows, etc.).
- Hacer helper compartido de tiempo.
- Agregar más asserts (ej. pre-set vip_entry y verificar clear — ya cubierto en units).
- Tocar service (el _ensure_aware sigue privado).
- Actualizar otros tests con patrones similares (se pueden hacer en quick tasks separados si se descubre breakage).

**Referencias clave (exploradas):**
- services/vip_service.py:173 (redeem, now/end_date), 19 (_ensure_aware)
- tests/integration/test_vip_flow.py (el test)
- tests/integration/test_vip_complete_cycle.py:82 (patrón normalize)
- tests/integration/test_vip_flows.py:29 (helpers + delta en renewal:424)
- models/CLAUDE.md (dualidad IDs + datetimes)
- .planning/quick/* ejemplos de PLAN.md estilo

Este plan es auto-contenido para ejecución vía GSD quick. Aprobación vía exit_plan_mode.

---
**Notas para executor:** Mantener voz/estilo de Lucien irrelevante (es test). Usar search_replace preciso. Verificar con run pytest antes de commit. Actualizar SUMMARY.md al final.
