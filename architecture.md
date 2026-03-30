# SYSTEM ARCHITECTURE (ENFORCED)

## 1. System Overview

Telegram bot modular con dominios:

- Gamification
- Missions
- Store
- Promotions
- VIP Access
- Narrative

Arquitectura basada en separación estricta de responsabilidades.

---

## 2. Core Layers

### handlers/
Responsabilidad:
- Entrada desde Telegram
- Routing de eventos

Reglas:
- PROHIBIDO lógica de negocio
- PROHIBIDO acceso a DB

---

### services/
Responsabilidad:
- Lógica de negocio por dominio

Estructura esperada:
- Un service por dominio (NO por feature fragmentada)

Ejemplo correcto:
- gamification_service.py
- mission_service.py

Ejemplo incorrecto:
- 10 services pequeños duplicando lógica

---

### models/
Responsabilidad:
- Definición de entidades
- Acceso a DB

---

### keyboards/
Responsabilidad:
- UI de Telegram (inline keyboards)

---

### config/
Responsabilidad:
- Configuración global

---

## 3. Domain Boundaries (CRÍTICO)

Cada dominio debe ser independiente:

### Gamification
- puntos
- niveles
- recompensas

### Missions
- tareas
- progreso
- completado

### Store
- productos
- compras

---

PROHIBIDO:
- lógica de un dominio dentro de otro

---

## 4. Data Flow

handler → service → model → service → handler

---

## 5. Architectural Constraints

- No lógica en handlers
- No duplicación entre services
- Cada dominio tiene un punto único de entrada (service principal)

---

## 6. LLM Constraints

El LLM DEBE:

- respetar separación de capas
- no crear nuevos handlers innecesarios
- no duplicar lógica entre dominios
