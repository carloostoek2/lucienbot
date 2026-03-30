# Lucien Bot

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández).

## Quick Commands
```bash
python bot.py                    # Iniciar bot
```

## Arquitectura
```
handlers/ → services/ → models/ → database
```
- **handlers/**: Solo enrutan eventos, SIN lógica de negocio
- **services/**: Lógica de negocio por dominio (un service = un dominio)
- **models/**: Entidades y acceso a DB

## Dominios
Cada dominio tiene su propio CLAUDE.md con contexto específico:

| Dominio | Service | Carpeta |
|---------|---------|---------|
| Gamificación | besito_service.py, daily_gift_service.py | [@services/besito_service.py] |
| Missions | mission_service.py, reward_service.py | [@services/mission_service.py] |
| Store | store_service.py, package_service.py | [@services/store_service.py] |
| Promotions | promotion_service.py | [@services/promotion_service.py] |
| VIP | vip_service.py | [@services/vip_service.py] |
| Narrative | story_service.py | [@services/story_service.py] |
| Users | user_service.py | [@services/user_service.py] |
| Channels | channel_service.py | [@services/channel_service.py] |
| Broadcast | broadcast_service.py | [@handlers/broadcast_handlers.py] |

## Documentos de Referencia
- [@architecture.md] - Reglas de arquitectura (CAPAS PROHIBIDAS)
- [@rules.md] - Reglas del sistema (50 líneas máx, sin lógica en handlers)
- [@decisions.md] - Decisiones técnicas
- [@AGENTS.md] - Documentación técnica completa

## Reglas Críticas
1. **PROHIBIDO** lógica en handlers
2. **PROHIBIDO** acceso a DB fuera de models
3. **PROHIBIDO** duplicación entre services
4. Funciones máximo 50 líneas
5. Nombrar: verbo + contexto + resultado

## Voz de Lucien
- Habla en 3ra persona ("Lucien gestiona...")
- Elegante, misterioso, nunca vulgar
- "Diana" como figura central
- "Visitantes" no "usuarios"
- "Custodios" no "admins"

## Seguridad
- Validar IDs de callback
- Verificar permisos admin
- Verificar saldos antes de transacciones
- Usar transacciones en BD
