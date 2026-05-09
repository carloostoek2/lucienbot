# Phase 16: Trivias Temáticas - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 16-Trivias Temáticas
**Areas discussed:** Modelo de Categorías, Sistema de Mazo, Recompensas por Racha, Integración con Trivia Existente

---

## Modelo de Categorías

| Option | Description | Selected |
|--------|-------------|----------|
| Campo en JSON | Agregar campo 'category' a cada pregunta en preguntas.json | |
| Modelo en DB | Categorías como tabla SQLAlchemy con admin UI | |
| Archivos separados | Un JSON por categoría | ✓ |

**User's choice:** Archivos separados
**Notes:** File name = category identifier. No metadata file needed.

| Option | Description | Selected |
|--------|-------------|----------|
| Nombre archivo = categoría | El nombre del archivo es el identificador | ✓ |
| Archivo índice + archivos | index.json lista categorías con nombre visible | |

**User's choice:** Nombre archivo = categoría

| Option | Description | Selected |
|--------|-------------|----------|
| Son la categoría 'General' | Migrar preguntas.json a preguntas_general.json | |
| Se distribuyen en categorías | Clasificar existentes en nuevas categorías | |
| Se mantienen como están | preguntas.json sigue como trivia no categorizada | ✓ |

**User's choice:** Se mantienen como están

| Option | Description | Selected |
|--------|-------------|----------|
| Selector de categoría | Usuario elige categoría de un menú | |
| Categoría aleatoria | Sistema asigna categoría al azar | |

**User's choice (free text):** El usuario nunca verá las categorías. Son herramientas internas de administración para dinámicas/fechas especiales. Por defecto siempre están las preguntas generales.

---

## Sistema de Mazo

| Option | Description | Selected |
|--------|-------------|----------|
| Cada 24h | Mazo se reinicia diariamente | ✓ |
| Al agotarse | Solo se reinicia cuando todas las preguntas han sido respondidas | |
| Manual por admin | Admin decide cuándo reiniciar | |

**User's choice:** Cada 24h

| Option | Description | Selected |
|--------|-------------|----------|
| Por usuario | Cada visitante tiene su propio registro | ✓ |
| Global | Una vez respondida, nadie más la ve | |

**User's choice:** Por usuario

| Option | Description | Selected |
|--------|-------------|----------|
| Mazo dentro del límite | Draw sin repetición dentro del límite diario | |
| Mazo independiente | Mazo solo controla no repetición, no afecta límites | ✓ |

**User's choice:** Mazo independiente

| Option | Description | Selected |
|--------|-------------|----------|
| Pool combinado | Categorías activas se fusionan | |
| Prioridad por categoría | Admin define prioridad | |

**User's choice (free text):** Únicamente habrá empalme cuando haya dinámica. Activación manual o por fecha. Siempre se presenta el mazo general por defecto. Cuando hay dinámica se reemplaza por completo por el mazo temático.

---

## Recompensas por Racha

| Option | Description | Selected |
|--------|-------------|----------|
| Besitos bonus en hitos | Bonus al alcanzar hitos (3, 5, 7, 10) | ✓ |
| Multiplicador progresivo | Cada acierto consecutivo vale más | |
| Solo mensajes, sin bonus | Mantener sistema actual | |

**User's choice:** Besitos bonus en hitos

| Option | Description | Selected |
|--------|-------------|----------|
| Mismos hitos, diferente bonus | Hitos iguales, VIP da el doble | ✓ |
| Mismos hitos y bonus | Bonus iguales para todos | |
| VIP tiene hitos extra | VIP tiene hitos adicionales más altos | |

**User's choice:** Mismos hitos, diferente bonus

| Option | Description | Selected |
|--------|-------------|----------|
| Moderado: 3=+2/+4, 5=+5/+10, 7=+10/+20, 10=+20/+40 | Escala progresiva | ✓ |
| Conservador: 3=+1/+2, 5=+3/+6, 7=+5/+10, 10=+10/+20 | Bonus discretos | |
| Agresivo: 3=+3/+6, 5=+10/+20, 7=+20/+40, 10=+50/+100 | Bonus altos | |

**User's choice:** Moderado

---

## Integración con Trivia Existente

| Option | Description | Selected |
|--------|-------------|----------|
| Mismo botón 'Trivia', contenido diferente | Cambia automáticamente al mazo temático | |
| Botón especial visible durante dinámicas | Botón adicional en el menú cuando hay categoría activa | ✓ |

**User's choice:** Botón especial visible solo durante dinámicas

| Option | Description | Selected |
|--------|-------------|----------|
| Mismos límites | Comparte intentos diarios con la general | |
| Límites independientes | Límites propios para trivia temática | ✓ |
| Sin límite durante dinámicas | Ilimitado cuando categoría activa | |

**User's choice:** Límites independientes

| Option | Description | Selected |
|--------|-------------|----------|
| Panel admin con comandos | /categoria_activar, /categoria_desactivar, etc. | |
| Activación manual + fechas | Fecha programada en archivo, sistema automático | |
| Solo manual desde admin | Admin enciende/apaga manualmente | |

**User's choice (free text):** Combinación: lógica de comandos pero con interfaz visual de botones inline. Que el admin gestione los mazos desde el panel con teclado propio.

| Option | Description | Selected |
|--------|-------------|----------|
| Dentro del panel admin existente | Botón '🎯 Mazos de Trivia' en admin actual | ✓ |
| Sección separada | Handler/router nuevo separado | |

**User's choice:** Dentro del panel admin existente

| Option | Description | Selected |
|--------|-------------|----------|
| Admin via bot con wizard | Crear categorías y preguntas desde el chat | |
| Archivos JSON preparados | Diana/equipo preparan JSON externamente | ✓ |
| Híbrido | Admin crea desde bot o carga JSON | |

**User's choice:** Archivos JSON preparados por Diana/equipo

---

## Claude's Discretion

- Montos exactos de bonus de racha pueden ajustarse por balance
- Formato/nombre/ícono del botón temático en menú de juegos

## Deferred Ideas

None.
