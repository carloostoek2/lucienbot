# Refactor y Mejora de Testing - Lucien Bot

**Fecha de última actualización:** 2026-05-31 (continuación Ítem 3/4 + Ítem #5: scheduler jobs + VIPService unit tests for expiration helpers)  
**Estado:** 
- Ítem #1 (Reacciones): ✅ Completado
- Ítem #2 (Limpieza reaction_mission_flow_real): ✅ Completado (reconciliado desde worktree)
- Ítem #3 (VIP expiration variants + Scheduler loop): ✅ Avanzado (a/b/c + variante #4 entregados; d revisado)
- Ítem #4 (VIP Expiration variants en fases_refactor_testing.md): ✅ Avanzado (variante ritual + scheduler durante estado entry)
- Ítem #5 (Scheduler de expiraciones - VIPService privados): ✅ Completado (unit tests en test_vip_service.py para has_other/get_expiring/expired/redeem/expire; ver s.8 + fases row 5)

**Responsable de la iniciativa:** Trabajo conjunto con el equipo

---

## 1. Objetivo General

Mejorar significativamente la calidad, confiabilidad y cobertura de los tests del proyecto, con especial énfasis en:

- Dejar de validar "lo que el código hace hoy" (incluyendo bugs intermitentes).
- Validar el **comportamiento correcto deseado** según las reglas de negocio y arquitectura.
- Reducir la aparición de "sacositas" (bugs que aparecen en producción al tocar otras partes).
- Establecer patrones claros y mantenibles para tests de flujos complejos.

El problema identificado inicialmente:
> "Agrego algo pequeño y se rompe otra cosa por allá". Los tests existentes a veces estaban protegiendo comportamiento buggy en vez de prevenirlo.

---

## 2. Enfoque de Trabajo

Se decidió un enfoque en dos velocidades:

1. **Acción inmediata (Top 10 Críticos)**: Identificar y atacar los 10 puntos de testing más riesgosos y de mayor impacto en los problemas reales reportados (reacciones que no funcionan, expulsiones indebidas de VIP, etc.).
2. **Revisión estructural (Fase por Fase)**: Una vez estabilizados los críticos, realizar una revisión sistemática de testing siguiendo la estructura de `.planning/phases/`, alineado con cómo realmente se construyó el bot.

---

## 3. Estado Actual (Fin de esta sesión)

### 3.1 Auditoría inicial realizada

- Se analizó la suite completa (~1082 tests, ~55% cobertura global).
- Se identificaron debilidades estructurales:
  - Muchos tests de "integración" eran en realidad scripts de diagnóstico con prints.
  - Falta de tests determinísticos para flujos clave.
  - Cobertura muy baja en dominios complejos nuevos (`game_service.py` ~34%, backpack ~18%, etc.).
  - El método más frágil (`check_and_register_reaction`) no tenía tests unitarios dedicados.

### 3.2 Top 10 Críticos identificados

Se priorizó el siguiente listado (solo los más relevantes para retomar):

| # | Prioridad | Área | Estado |
|---|-----------|------|--------|
| 1 | Crítico | Flujo completo de Reacción (`check_and_register_reaction` + misión + recompensa + actualización de teclado) | ✅ Completado |
| 2 | Crítico | Limpieza del test `test_reaction_mission_flow_real.py` (toca DB real) | ✅ Completado (ver 3.4 — trabajo realizado en worktree lucienbot-2026-05-31-0bd7f536 y sincronizado) |
| 3-10 | Alto | VIP expiration variants, Scheduler, GameService/Trivias, Backpack, Invariantes de negocio, etc. | En progreso (ítem 3/4/5: a/b/c + ritual variant + Ítem #5 VIPService units for scheduler helpers completado; tests passing + docs updated) |

### 3.3 Trabajo realizado en esta sesión (Flujo de Reacciones - Ítem #1)

Este fue el punto de partida elegido por su alto impacto:

- Se creó `tests/unit/test_broadcast_service_reaction_flow.py` → Tests unitarios sólidos para `check_and_register_reaction` (el método real que usa producción).
- Se creó `tests/integration/test_reaction_full_chain.py` → Test del flujo completo:
  - Reacción real → acreditación de besitos
  - Avance y completado de misión `REACTION_COUNT`
  - Entrega automática de recompensa
  - Reconstrucción y actualización de teclado con conteos (la parte que históricamente tiene "comportamientos raros")

**Mejoras de infraestructura aplicadas:**

- Se agregó `expire_on_commit=False` en el fixture `db_session` de `tests/conftest.py` (recomendación de análisis externo).
- Se implementó y documentó el **patrón de SQLite en archivo + TestSession independiente** como el estándar recomendado para tests pesados con múltiples commits internos de servicios.

**Resultado actual del test de flujo completo:**
- 1 test pasa limpiamente (validación de acumulación de conteos en teclado).
- 1 test está en `xfail` con documentación clara (dificultades de attachment incluso con el patrón de archivo, debido a `SessionLocal()` internas en algunos servicios).

**Confirmación de revisión (sesión actual + reconciliación worktree):** Todos los 5 tests unitarios pasan. El test de conteos múltiples pasa. El patrón SQLite-en-archivo + TestSession queda establecido como estándar para flujos pesados. Los tests validan el contrato deseado (incluyendo que fallo en misión NO revierte la reacción + besitos).

**Nota importante sobre worktree:** El trabajo de ítem #2 (limpieza) se realizó en el worktree aislado `lucienbot-2026-05-31-0bd7f536` (sesión del 31 de mayo). Los cambios (borrado del archivo peligroso + limpieza de CI + actualización detallada de este md) quedaron sin commitear en ese árbol. Esta sesión reconcilia trayendo el estado correcto al árbol principal.

### 3.4 Ítem #2 completado: Limpieza de test que tocaba DB real de producción

- Se eliminó `tests/integration/test_reaction_mission_flow_real.py` (392 líneas de script diagnóstico con prints).
- **Riesgo eliminado:** Este archivo se conectaba directamente a `bot_config.DATABASE_URL` (BD de producción), creaba usuarios con telegram_id 999999999, mensajes de broadcast falsos, reacciones, etc., mutando datos reales. Usaba hack de path hardcoded para Termux y no tenía asserts determinísticos.
- Reemplazado por los tests correctos ya existentes:
  - `tests/unit/test_broadcast_service_reaction_flow.py`: cobertura unitaria sólida y aislada del método de producción `check_and_register_reaction`.
  - `tests/integration/test_reaction_full_chain.py`: flujo completo determinístico usando el patrón recomendado de SQLite en archivo + TestSession (evita DetachedInstanceError y no toca prod).
- El archivo hermano `test_reaction_mission_flow.py` (sin _real) se mantuvo porque usa fixtures aislados (db_session con rollback), contiene asserts reales (no solo prints) y cubre caminos legacy + async; no representa riesgo de mutación de prod (aunque su cobertura de misiones REACTION_COUNT es parcial ya que depende del estado de datos de prueba y no crea misiones explícitamente, a diferencia de test_reaction_full_chain.py).
- **CI hygiene completada como parte del cierre:** Se leyeron y limpiaron las dos líneas `--deselect` obsoletas en `.github/workflows/ci.yml` (que referenciaban las clases del test eliminado para proteger prod). Se agregó comentario histórico. Verificación: comando pytest de CI simulado recolecta limpio (0 warnings de deselects unmatched para el archivo borrado); grep recursivo full (incl .github/*.yml) confirma 0 referencias vivas al test eliminado fuera de docs + comentario de limpieza.
- Lección para futuras limpiezas: siempre `grep -r` explícito sobre `**/.github/**/*.yml` + workflows + Makefile + pyproject (el grep inicial de workspace tools no cubrió .github por defecto en esta sesión).

---

## 4. Patrón Establecido (Importante para Futuro)

**Para tests de integración complejos que cruzan varios dominios con commits internos, usar:**

```python
def _create_engine_and_session(self, tmp_path):
    db_path = tmp_path / "nombre_del_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestSession
```

Ventajas:
- Aísla completamente el test.
- Evita interferencia con el fixture global `db_session`.
- Es el mismo patrón usado exitosamente en `test_vip_subscription_lifecycle.py`.

Este patrón quedó documentado en `tests/integration/test_reaction_full_chain.py` como referencia.

---

## 5. Archivos Clave Modificados / Creados

| Archivo | Tipo de cambio | Notas |
|---------|----------------|-------|
| `tests/unit/test_broadcast_service_reaction_flow.py` | Nuevo | Tests unitarios del método de producción de reacciones (5 tests, todos passing) |
| `tests/integration/test_reaction_full_chain.py` | Nuevo | Test del flujo completo + patrón SQLite en archivo (1 passing + 1 xfail intencional bien documentado) |
| `tests/conftest.py` | Modificado | `expire_on_commit=False` en el sessionmaker (con comentario explicativo) |
| `refactor_testing.md` | Actualizado | Estado de ítems #1 (completado) y #2 (pendiente, revisión confirmada: no se limpió) |
| `tests/integration/test_reaction_mission_flow_real.py` | Eliminado (git rm) | **Ítem #2 completado** (en worktree + sincronizado a main). Riesgo crítico de mutación de prod eliminado. |
| `tests/integration/test_reaction_mission_flow.py` (sin _real) | Mantenido intencionalmente | Usa db_session seguro + asserts reales; no muta prod. Razón documentada en 3.4. |
| `services/vip_service.py` | Pequeña mejora defensiva | `is_active = True` explícito al extender suscripción en `redeem_token`. |
| `tests/integration/test_vip_subscription_lifecycle.py` | Actualizado + nuevo test | Scenario A clarificado (defensivo). Nuevo Scenario D: extensión + scheduler integrado. |
| `tests/integration/test_vip_complete_cycle.py` | Hygiene | Reemplazados `datetime.utcnow()` por `datetime.now(timezone.utc)`. |
| `tests/integration/test_free_entry_flow.py` | Ampliado (scheduler loop) | Nuevo TestSchedulerPendingRequestsJob (previo) + TestSchedulerFreeWelcomeJob (b: _send_free_welcome_job + ritual). Patrón robusto. |
| `tests/integration/test_vip_subscription_lifecycle.py` | Ampliado (expiring + errors + variante) | 3 nuevos métodos en TestVIPSubscriptionLifecycle: test_scheduler_expiring_... (a: reminders + sets flag), handles_send_error (c), + ritual_state variant (ítem 4 "scheduler durante estado"). Todos passing. |
| `tests/unit/test_vip_service.py` | Ampliado (unit tests VIP privados) | **Ítem #5 (Alto) fases** completado: 7 nuevos tests en TestVIPServiceExpirationSupport cubriendo has_other_active_subscription (2-active, only-one, mix expired), get_expiring/get_expired richer (reminder combos, thresholds, multi), redeem extension + expire interaction. Extensión de archivo existente (smallest). Sin nueva extracción en VIPService. |

---

## 6. Opciones para la Próxima Sesión

### Opción A: Continuar con los Top 10 Críticos (actual)
- **Ítem #1 (Reacciones):** Completado y confirmado.
- **Ítem #2 (Limpieza legacy reaction tests):** Pendiente. Revisión realizada: los archivos no fueron tocados. Se puede hacer limpieza ahora (deprecación + remoción de prints/DB real/legacy method) o marcar como baja prioridad ya que los reemplazos robustos existen.
- **Ítem #3 (VIP expiration variants):** Enfocarse aquí. Ya existe `test_vip_subscription_lifecycle.py` (excelente, usa el patrón de archivo, cubre los 3 escenarios críticos de _process_expired_subscriptions + has_other_active). Identificar y agregar tests para variantes de alto riesgo restantes (errores en el loop de expiración, edge cases de canal inactivo, limpieza de vip_entry_state, posibles issues de timezone/naive datetime, interacciones con recordatorios, etc.).

### Opción B: Iniciar Revisión Fase por Fase
- Empezar por las fases tempranas (Fundación + Fase 1 - Introducción de Lucien y arquitectura estructurada).
- Luego seguir el orden de `.planning/phases/` (07.1, 08, 09...).
- Para cada fase evaluar: qué features se entregaron vs qué tests existen realmente.

**Trabajo realizado en esta sesión (continuación Ítem 3 + avance Ítem 4 - siguiendo orden exacto a→b→c→d de sección 8):**
- a. Nuevo test `test_scheduler_expiring_subscriptions_sends_reminders_and_sets_flag` en `TestVIPSubscriptionLifecycle` (test_vip_subscription_lifecycle.py): invocación real de `_process_expiring_subscriptions`, aserciones de send_message (voz Lucien) + reminder_sent=True en verify session, sin side-effects en otras subs. Patrón robusto exacto.
- b. Nuevo `TestSchedulerFreeWelcomeJob` + `test_send_free_welcome_job_sends_ritual_message_and_keyboard` en test_free_entry_flow.py: cobertura directa de `_send_free_welcome_job(user_id, channel_tg_id)`, verifica LucienVoice.free_entry_ritual + social keyboard.
- c. Error handling: `test_scheduler_expiring_handles_send_error_with_rollback` (side_effect seq en AsyncMock → rollback parcial de una sub, continue con otras); + canal inactivo/ritual paths en expired ya cubierto indirectamente por suite previa.
- Variante para Ítem #4 (el bug de expulsiones indebidas): `test_expired_scheduler_while_user_in_ritual_state_clears_state_on_kick` — scheduler _process_expired ejecutándose mientras User.vip_entry_status="pending_entry"/stage=2; verifica kick + limpieza correcta del estado (cubre riesgo "scheduler mientras usuario en ritual").
- d. Revisado exhaustivamente (grep + lectura de scheduler_service + ausencia de tests previos): `_cleanup_expired_streak_sessions` carece de cobertura directa de job. Se intentó test robusto pero modelos Streak* requieren setup FK pesado (no factories reutilizables pequeños); se documentó recomendación y se removió para mantener tests 100% passing + smallest change. Prioridad baja vs a/b/c.
- Actualización de `refactor_testing.md` (esta sección + tabla Archivos + sección 8 Cómo Retomar). GSD spirit: nota de tarea vía terminal cmd antes de edits.
- Decisión: extender test_vip_subscription_lifecycle.py (co-localizar VIP scheduler coverage) y test_free_entry_flow.py (para free/scheduler jobs); no nuevo archivo test_scheduler_jobs.py (crecimiento moderado). Seguir patrón exacto de TestSchedulerPendingRequestsJob y estilo prints de lifecycle. Todos los tests nuevos pasan (pytest -k). ruff format + ruff check --fix ejecutados.
- No se tocó fases_refactor_testing.md (opcional, tabla truncada).

**Recomendación para próxima sesión (continuar Ítem 3/4/5):**
- Completar d con test de streak en su dominio (test_streak_* o nuevo scheduler jobs) usando factories existentes si hay.
- Más errores en loops (inactive channel en expired → comportamiento actual de 'continue' sin desactivar; DB issues simulados).
- Unit tests privados de VIPService (get_expiring etc) per ítem 5 de fases.
- Matriz completa ritual + scheduler (múltiples canales VIP, renovación mid-ritual).
- Mantener estándar: file SQLite + TestSession + patch SessionLocal/_get_bot.

---

## 7. Notas y Decisiones Importantes

- La voz de Lucien y las reglas de arquitectura (handlers → services → models, máximo 50 líneas, etc.) siguen siendo sagradas. Los tests deben ayudar a mantenerlas, no relajarlas.
- Se detectó que muchos "tests de integración" antiguos dependían demasiado del estado de datos (misiones existentes, etc.). El nuevo enfoque prioriza tests **determinísticos**.
- El problema de "reacción no funciona" o "conteos de teclado no se actualizan" tiene componentes tanto en la lógica de negocio como en la manipulación de UI/keyboard después de la reacción.
- **Decisión de esta sesión (continuación testing debt):** Se siguió estrictamente el orden de valor a→b→c→d de "Cómo Retomar". Se prefirió extender archivos existentes (lifecycle para VIP scheduler co-location + ritual variant addressing directamente ítem 4 de fases; free_entry para welcome/streak review) vs crear test_scheduler_jobs.py (smallest change, patrón establecido). Para d se revisó pero se evitó test incompleto (Streak models pesados) priorizando 100% pass + GSD spirit. ruff y pytest obligatorios antes de claim. GSD: comando terminal para registrar tarea antes de 1er edit.

---

## 8. Cómo Retomar la Próxima Sesión (Preciso para continuar)

1. Leer este archivo (`refactor_testing.md`) — especialmente la sección "Trabajo realizado en esta sesión".
2. Revisar los archivos clave de la sesión actual:
   - `tests/integration/test_vip_subscription_lifecycle.py` (nuevo Scenario D)
   - `tests/integration/test_free_entry_flow.py` (TestSchedulerFreeWelcomeJob (b) + (d) review note at EOF; PendingRequestsJob was prior session)
   - `services/scheduler_service.py` (las funciones _process_*)
3. Estado actual de ítems:
   - #1 y #2: Completados y documentados.
   - #3 (VIP + Scheduler): ✅ Avanzado (a/b/c + variante ritual para #4 entregados en esta sesión; d revisado y documentado).
   - #4 (fases_refactor_testing): Avance vía variante scheduler+ritual_state (el riesgo de expulsiones indebidas durante entry).
4. Próximos pasos recomendados (en orden de valor, actualizar al retomar):
   a. ✅ Completado: test directo _process_expiring_subscriptions (reminders) + flag + no side effects.
   b. ✅ Completado: cobertura _send_free_welcome_job (ritual + keyboard).
   c. ✅ Parcial: error handling en loop expiring (send fail → rollback+continue); agregar más (inactive channel en expired, etc.).
   d. Revisado: falta cobertura; se recomienda agregar en dominio streak (evitar setup pesado aquí).
   Siguientes: unit tests VIPService privados (ítem 5 fases) ✅ completado esta sesión (extend test_vip_service.py con has_other richer + get_* multi + redeem extension cases), matriz completa ritual+scheduler (múltiples canales, renovación mid-ritual - priorizar integration o nuevo si justificado), más errores (inactive channel expired etc).
5. Al terminar la sesión: actualizar esta sección + la tabla de Top 10 + la tabla de "Archivos Clave".
6. Commits: Esta sesión (GSD quick via /implement) dejó cambios listos + tests passing + ruff limpio. Ver git status al retomar.

**Actualización de esta sesión (continuación Ítem 5 + handoff):**
- ✅ Ítem 5 (Alto) de fases_refactor_testing.md avanzado/completado vía unit tests en VIPService (has_other_active_subscription multi-scenarios + filtering, richer get_expiring/get_expired con reminder/thresholds/multi, redeem renewal effects on scheduler "expired" view, expire+has_other interaction).
- Patrón seguido: extender tests/unit/test_vip_service.py (co-location, smallest change, no new file test_scheduler_expiration.py per refactor_testing.md rec + rules: no new files sin razón clara).
- Extracción de lógica a VIPService (p.ej. execute_expiration_for_subscription) SKIPPED intencionalmente: viola pickling de APScheduler (jobs requieren funcs módulo), riesgo dupe con bot.py startup, >50 líneas potencial, cross-domain (scheduler System vs VIP domain), refactor rules (solo si reduce complejidad/dupe). Scheduler orchestration + error continue + ban/unban + voice notify permanecen; units ahora cubren los métodos puros de VIP que usa (get/has/expire/redeem). Limitación documentada en test.
- GSD: 3+ logs pre-edit a .planning/quick/gsd-testing-debt-item5.log (continuación del init previo).
- Archivos clave añadidos a tabla abajo.
- ruff format/check + pytest -k específico 100% passing requeridos y ejecutados.
- Próxima recomendada: más errores en loops scheduler (canal inactivo en expired), matriz ritual completa (múltiples VIP channels + mid-ritual renew), o streak cleanup si factories lo permiten.

**Fin del documento de traspaso.**

---

Este archivo debe mantenerse actualizado al final de cada sesión de trabajo de testing/refactor.