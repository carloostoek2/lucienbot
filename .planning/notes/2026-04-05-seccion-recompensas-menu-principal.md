# Sección de Recompensas en Menú Principal

**Fecha:** 2026-04-05

## Idea

Agregar una sección de "Recompensas" en el menú principal de usuarios que muestre:

- Lista de recompensas disponibles en formato de botones
- Contador de cuántas recompensas hay disponibles
- Al entrar a cada recompensa: detalles de qué es, qué otorga, y a qué misión está ligada
- Botón para reclamar la recompensa directamente desde ahí

## Motivación

Hacer más visible el sistema de recompensas y facilitar que los usuarios descubran y reclamen sus recompensas pendientes sin tener que navegar por múltiples menús.

## Posible Implementación

- Nuevo handler/menu en `bot/handlers/user/rewards_menu.py`
- Integración con `MissionService` y `RewardService`
- Botones: "🎁 Recompensas (3 disponibles)"
- Callback: `reward_details:{reward_id}`
- Vista detalle con: nombre, descripción, recompensa (besitos/paquete/VIP), misión asociada, botón "Reclamar"

## Relacionado

- Sistema de misiones existente
- Menú principal en `bot/handlers/user/main_menu.py`
