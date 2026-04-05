---
title: Sección de recompensas en menú principal de usuarios
created: 2026-04-05
area: rewards
source: conversation
---

# Sección de recompensas en menú principal de usuarios

**Description:**
Poner una sección de recompensas en el menú principal de los usuarios en el que se muestren las recompensas disponibles en formato de botones. Mostrar cuántas recompensas hay disponibles y al entrar a cada recompensa mostrar sus detalles: qué recompensa es, lo que otorga, y a qué misión está ligada para que la puedan reclamar.

## Requirements

- [ ] Agregar botón "Recompensas" al menú principal de usuarios
- [ ] Mostrar listado de recompensas disponibles como botones
- [ ] Indicar cantidad total de recompensas disponibles
- [ ] Al entrar a una recompensa específica, mostrar:
  - Nombre/descripción de la recompensa
  - Qué otorga (besitos, paquete, VIP, etc.)
  - Misión asociada que debe completarse
  - Botón para reclamar (si cumple condiciones)

## Related Areas

- missions ( MissionService, RewardService )
- gamification ( BesitoService )
- handlers/user ( user menu )
