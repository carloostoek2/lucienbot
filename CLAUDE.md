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
| [@decisions.md] | Decisiones técnicas, estado de consolidate handlers |
| [@AGENTS.md] | Documentación técnica completa, diagramas, flujos |
| `services/{dominio}/CLAUDE.md` | Contexto específico de cada dominio |

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
- Rate limiting: `ThrottlingMiddleware` con `aiolimiter`, admin bypass
- FSM storage: `RedisStorage` si `REDIS_URL` está seteado, si no `MemoryStorage`

---

## GSD Workflow Enforcement

Antes de usar herramientas que modifiquen archivos, iniciar trabajo a través de GSD:

- `/gsd:quick` — fixes pequeños, updates de docs, tareas ad-hoc
- `/gsd:debug` — investigación y bug fixing
- `/gsd:execute-phase` — trabajo planificado por fases

**No hacer edits directos fuera de GSD** a menos que el usuario lo pida explícitamente.
