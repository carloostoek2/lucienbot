# Lucien Bot

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández). Gestiona suscripciones VIP, canales de contenido, sistema de gamificación con besitos, misiones, tienda virtual, promociones y narrativa interactiva con arquetipos de personajes.

**Entry point:** `python bot.py`

---

## Arquitectura

```
handlers/ → services/ → models/ → database
```

- **handlers/**: Solo enrutan eventos, SIN lógica de negocio, SIN acceso a DB
- **services/**: Lógica de negocio por dominio
- **models/**: Entidades SQLAlchemy y acceso a DB

Para detalles completos: [@architecture.md]

---

## Dominios y Servicios

Cada dominio tiene su propio CLAUDE.md con contexto específico.

| Dominio | Services | Descripción |
|---------|---------|-------------|
| **VIP** | `VIPService`, `AnonymousMessageService` | Membresías exclusivas via tokens, tarifas, suscripciones. Canal `Subscription` ↔ `Token` ↔ `Tariff`. Mensajes anónimos VIP → Diana |
| **Gamificación** | `BesitoService`, `BroadcastService`, `DailyGiftService` | Besitos (puntos), reacciones con besitos, regalo diario |
| **Canales** | `ChannelService` | Canales VIP y free, auto-aprobación con wait time, `PendingRequest` |
| **Tienda** | `StoreService`, `PackageService` | Catálogo, carrito, compras, paquetes de contenido. Stock: `-1`=ilimitado, `-2`=no disponible |
| **Misiones** | `MissionService`, `RewardService` | Tareas recurrentes/únicas, recompensas (besitos/paquete/VIP). Entrega via `deliver_reward()` |
| **Promociones** | `PromotionService` | "Me Interesa", precios en centavos MXN (ej: 99900 = $999.00 MXN), bloqueo de usuarios |
| **Narrativa** | `StoryService` | Nodos de historia, arquetipos, logros. Quiz de arquetipos hardcodeado en el servicio |
| **Usuarios** | `UserService` | Perfiles, roles admin |
| **Sistema** | `SchedulerService`, `BackupService` | APScheduler con SQLAlchemyJobStore (jobs persisten en BD), backup dual (pg_dump/SQLite) |
| **Observabilidad** | `HealthService` | Checks read-only/best-effort: DB connectivity/latency, bot runtime, channels (free/VIP/pending/ready), scheduler jobs, EventBus listeners (besitos_awarded), critical sanity (neg balances, VIP expiring, narrative progress), backup age. Admin /health Command+cb "🛡️ Pulso del reino" (after analytics) + terminal `python -m scripts.health_check [--json] [--verbose]`. Follows AnalyticsService pattern al pie (get_service + is_admin + 1 call/handler, Lucien voice, no mutation). 0 impact on 3 crit or atomicity/EventBus/get_service contracts. (Item 11 / 29-observability-health + documentador ROADMAP update) |
| **Analytics** | `AnalyticsService` | Dashboard stats, exports CSV |

### Servicios adicionales
- `SchedulerService` y `BackupService` son **System domain** — no expuestos a usuarios, corren en background
- `AnalyticsService` es **Analytics domain** — solo accesible para Custodios
- `AnonymousMessageService` es **VIP domain** — mensajes anónimos de suscriptores VIP a Diana

---

## Documentos de Referencia

| Archivo | Contenido |
|---------|-----------|
| [@architecture.md] | Reglas de arquitectura, capas prohibidas, domain boundaries |
| [@rules.md] | Límite 50 líneas, naming (verbo+contexto+resultado), logging, anti-patterns |
| [@decisions.md] | Decisiones técnicas, estado de consolidate handlers + hardener Item entries + adoption of 6-agent + documentador standard |
| [@AGENTS.md] | Documentación técnica completa, diagramas, flujos |
| [@.planning/HARDENING_ROADMAP.md] | Living "hoja de ruta" del hardener: Initial Analysis, Decisions, What Has Been Done (por tirón/pool de 4 con outcomes + verifs arch/test/documentador), What Is Missing / Roadmap, Proposed Next (max 4), Metrics, pool/BATCH notes + verbatim "Pool anterior de 4 cerrado (tests passing per user)..." phrase. Actualizado por documentador al cierre de cada pool. |
| [.claude/agents/documentador.md] | Agente especializado post-pool: actualiza HARDENING_ROADMAP + extrae learnings + persiste report en agent-memory/documentador/ + MEMORY.md. Usa GSD pre-log + wc. Fuente de verdad: SUMMARYs + gsd logs + impact/arch/test-guardian reports del tirón. Pool phrase + 3 crit + contracts siempre. |
| [.claude/agents/claude-md-sync.md] | Agente para auditar/sincronizar CLAUDE.md (raíz + services/ + handlers/ + models/) con realidad del código + arquitectura. Codifica el hardener pattern (6-agent seq + documentador + pools de 4) como estándar ágil para hardening (reduce dependencia full GSD para este trabajo mientras preserva reglas core). Fuente: SUMMARYs + ROADMAP + decisions + agent reports. |
| [.claude/agents/ (impact-analyzer, gsd-planner, gsd-executor, arch-enforcer, test-guardian, etc.)] | Agentes del hardener: secuencia exacta de 6 pasos por ítem (impact map + risks a 3 crit, PLAN tight + golds, executor con pre-log + self-check PASSED, arch audit PASS/PASS WITH NOTES 0 crit, test-guardian "suite protege adecuadamente" + re-runs golds). GSD pre inside. |
| [models/CLAUDE.md] | Modelos SQLAlchemy, enum TransactionSource, **reglas de migraciones Alembic** |
| [services/CLAUDE.md] | Servicios por dominio + tabla actual (incl. HealthService/Observability Item 11), reglas, cross-cutting (EventBus PoC + get_service, Observability details + documentador refs), patrones hardener para nuevos (e.g. Health read-only best-effort). |
| `services/{dominio}/CLAUDE.md` | Contexto específico de cada dominio (cross sections para EventBus/Item5/6/10 etc. agregados por tirones) |

---

## Reglas Críticas (non-negotiable)

1. **PROHIBIDO** lógica en handlers — llamar exactamente 1 service
2. **PROHIBIDO** acceso a DB fuera de models
3. **PROHIBIDO** duplicación entre services
4. Funciones máximo 50 líneas
5. Nombrar: verbo + contexto + resultado
6. Cada acción importante debe loguear: módulo, acción, user_id, resultado

---

## Voz de Lucien

- Habla en 3ra persona ("Lucien gestiona...")
- Elegante, misterioso, nunca vulgar
- "Diana" como figura central
- "Visitantes" no "usuarios"
- "Custodios" no "admins"
- Dominio promotions usa lenguaje diferenciado ("forjar experiencias", "Gabinete de Oportunidades")

---

## Seguridad

- Validar IDs de callback siempre
- Verificar permisos admin con `is_admin()` antes de cualquier acción admin
- Verificar saldos (`has_sufficient_balance`) antes de transacciones
- Usar transacciones en BD para operaciones atómicas
- Rate limiting + idempotencia centralizados en middlewares/ (gsd-mw-hardening):
  - `ThrottlingMiddleware` (middlewares/rate_limiter.py, canonical; usa aiolimiter, real ADMIN_BYPASS + Custodios list, cleanup, Lucien voice, soporta CB)
  - `IdempotencyMiddleware` (middlewares/idempotency.py) para dedup de CallbackQuery (previene re-ejecuciones por retries de TG)
  - Registro: Error (outer) → Idempotency (cb) → Throttling (cb + messages)
  - Legacy manual guards en handlers removidos (phase 5); legacy rate file es shim DEPRECATED
  - Tests unit en tests/unit/test_*_middleware.py + actualizaciones en handler tests
- FSM storage: `RedisStorage` si `REDIS_URL` está seteado, si no `MemoryStorage`

---

## GSD Workflow Enforcement

Antes de usar herramientas que modifiquen archivos, iniciar trabajo a través de GSD:

- `/gsd:quick` — fixes pequeños, updates de docs, tareas ad-hoc
- `/gsd:debug` — investigación y bug fixing
- `/gsd:execute-phase` — trabajo planificado por fases

**No hacer edits directos fuera de GSD** a menos que el usuario lo pida explícitamente.

## Hardener Workflow — Agile Standard for telegram-bot-hardener (preferred for hardening / refactoring)

**Proven pattern (tirones 25-29 / Items 7-11 and ongoing):** For hardening and refactoring tasks scoped to the telegram-bot-hardener (tight scope, 0 behavior/0 atomicity change, protect 3 critical systems: gamification / narrative / channels-VIP + atomicity/EventBus/get_service contracts), the **preferred, lighter, more focused agile standard** is:

- Pools / tirones of **maximum 4 items**, automatically chained.
- **Exact 6-agent sequence per item:** impact-analyzer → gsd-planner → gsd-executor (with GSD pre-log before every edit/gate + self-check PASSED) → arch-enforcer (audit: PASS / PASS WITH NOTES / FAIL; 0 critical violations target) → test-guardian (veredict "suite protege adecuadamente"; re-runs of golds + targeted; coverage for contracts) → correr tests (exact flags from PLAN: -q --tb=line -p no:cov --override-ini="addopts=" + -k filters + re-runs of cross_service_atomicity / reaction_* / daily atomic / invariants + broader smoke; 0 attributable regressions).
- **Explicit launch of the documentador agent at the end of each pool** (after last item's test-guardian + tests green + self-check): updates .planning/HARDENING_ROADMAP.md (What Has Been Done per tirón with structured outcomes + verifs, What Is Missing / Roadmap refresh, Metrics, pool/BATCH notes), extracts learnings/patterns (e.g. "patrón de puros para <=50 LOC + 1-service", "local + EventBus observers para decoupling besitos con atomicity gold protegido"), persists traceability (agent-memory/documentador/ reports + pointers in MEMORY.md), follows GSD pre-log to its dedicated .planning/quick/gsd-documentador-*.log + wc -l.
- **Pool close phrase (verbatim in all SUMMARYs, agent reports, ROADMAP, decisions, gsd logs):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
- **Key proven practices enforced by sequence:** copy gold patterns al pie de la letra (Reward locals inside _deliver + 1-line test; story listener "MUST NOT credit/debit" + best-effort + DESIRED CONTRACT; atomicity golds with patch schedule_emit + TestSession/file + strict + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + N806 tol + 777 + try/finally + gather return_exceptions; daily hasattr guards + fallback); 1-service per handler (via with get_service(XXX) as svc: exactly 1 call); pure helpers (verb+context+result, stateless, "Función pura...", import-inside tests, Test*PureHelpers) for long admin/wizard funcs to <=50 LOC; locals on-demand BesitoService(db=...) inside credit/debit sites only (0 impact on caller tx/atomicity); thin delegates in services for cross (e.g. get_all_rewards_for_mission_wizard); thin admin views + is_admin + Lucien voice; read-only best-effort for observability (HealthService); central explicit EventBus reg in bot.py; GSD pre inside agents; arch + test-guardian + documentador for traceability/quality gates; 3 crit + contracts always in mind (0 mutation on gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM/quiz, channel pending/approve/expire/bans/subs + VIP grant/revoke).

**Evidence from recent tirones (source of truth):** 
- Item 9/27 (mission-admin-long-funcs, first of pool): 27-mission-admin-long-funcs-SUMMARY.md + PLAN + gsd-*.log (79+) + impact item9 + arch-enforcer/item9-arch-audit.md (PASS WITH NOTES, 0 critical; 9 with get_service(MissionService), 0 bare RewardService, 11 puros, LOC<=50 via inspect, delegates, UI 1:1, logging, 3 crit protected orthogonal); test-guardian/item9 ( "suite protege adecuadamente"; 55+11 pure +179 cross green); self-check PASSED + pool phrase + handoff.
- Item 10/28 (remaining-besito-store, second): 28-*-SUMMARY + PLAN + gsd (82+) + impact/arch (PASS WITH NOTES 0 crit) /test-guardian ("suite protege adecuadamente") reports; locals in 3 purchase sites + observer "MUST NOT... DESIRED CONTRACT" + "store | ..." + 1-line/guard ports + bot reg "+ Item 10 store"; golds 8/8 + broader protected atomicity contracts; 0 beh/0 atomicity.
- Item 11/29 (observability-health, third): 29-*-SUMMARY + PLAN + gsd (80+) + explicit "launch documentador agent" at F6 + "documentador used for ROADMAP/docs"; HealthService (read-only, Analytics pattern al pie, <50, logging, get_service 1 call, is_admin, /health + terminal + "🛡️ Pulso del reino"); 0 impact on 3 crit; self-check PASSED + pool phrase + arch/test-guardian + documentador handoff.
- Prior: Items 7/25 (reward 1svc+puros), 8/26 (store-admin puros+1svc), 5/6 (besito locals+observers+reg), etc. All in HARDENING_ROADMAP sec4 + decisions.md (Item entries mirror style + BATCH/pool) + .claude/agent-memory/documentador/ (tiron-*-closed.md reports + MEMORY.md) + tirón documentador updates.

**Full GSD (/gsd:execute-phase etc.) remains available** for general work, complex non-hardener changes, or when explicitly requested by user. The hardener pattern is the **documented, preferred way** for telegram-bot-hardener scope because it has delivered consistent results with tighter focus, built-in quality gates (arch/test-guardian/documentador), and living ROADMAP. Core non-negotiable rules (handlers call exactly 1 service, funcs <=50 LOC, naming verb+context+result, logging "módulo | acción | user_id | resultado", 3 critical systems always protected, get_service context manager, EventBus best-effort "MUST NOT mutate", atomicity contracts, is_admin before admin actions, etc.) are **intact and enforced** by this workflow (see arch-enforcer + test-guardian + documentador roles).

**References:** 
- .claude/agents/documentador.md (this agent's definition + GSD pre + pool phrase + source-of-truth SUMMARYs/agent-reports)
- .claude/agents/claude-md-sync.md (for future focused CLAUDE.md reality-syncs)
- .claude/agents/{impact-analyzer,gsd-planner,gsd-executor,arch-enforcer,test-guardian}.md
- .planning/HARDENING_ROADMAP.md (living; updated by documentador at each pool close)
- Recent: .planning/phases/{27-mission-admin-long-funcs,28-remaining-besito-store,29-observability-health}/*-SUMMARY.md + PLAN.md + gsd-*.log
- .claude/agent-memory/{impact-analyzer,arch-enforcer,test-guardian,documentador}/ (per-item reports + MEMORY.md)
- decisions.md (hardener Item entries + this adoption decision)
- services/CLAUDE.md (HealthService + EventBus cross-cutting)

**When in doubt for hardening work:** Use the 6-agent + documentador pattern (invoke via the hardener orchestrator or explicit agent launches). It keeps scope tight, protects the invariants, and keeps the roadmap actionable. 

## Workflow para Hardening (resumen accionable)
1. Hardener identifica pool de <=4 items (tight, from clusters + impact).
2. Por item: full 6-step sequence (GSD pre inside, copy golds al pie, self-check PASSED, arch/test veredicts, pool phrase at batch closes).
3. Al cerrar pool (post último test-guardian + tests passing + self-check): auto-invoke documentador para ROADMAP + learnings + agent-memory report + MEMORY pointer.
4. Repetir. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
5. Core rules + 3 crit + contracts: siempre protegidos y verificados explícitamente (no solo aspiracional).

This evolution reduces mandatory full-GSD overhead for this class of focused, high-discipline work while preserving (and actually strengthening via gates) all project invariants. See claude-md-sync agent for ongoing CLAUDE.md alignment work.
