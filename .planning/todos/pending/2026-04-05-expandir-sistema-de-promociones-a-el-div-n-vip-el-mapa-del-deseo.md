---
created: 2026-04-05T10:05:25.745Z
title: Expandir sistema de promociones a El Diván VIP - El Mapa del Deseo
area: promotions
files: []
---

## Problem

Se requiere expandir el sistema de promociones actual para incluir promociones exclusivas en la sección "El Diván" destinadas únicamente a usuarios VIP.

Nueva sección: "El Mapa del Deseo" - será un botón dentro de El Diván que identifica 4 secciones/secciones de contenido. Estas promociones deben integrarse con el sistema de promociones existente para no agregar lógica innecesaria.

## Solution

- Reutilizar el sistema de promociones actual (PromotionService, Promotion model)
- Crear un botón "El Mapa del Deseo" dentro de El Diván
- Definir 4 secciones/categorías dentro de esta nueva área
- Las promociones estarán disponibles solo para usuarios con membresía VIP activa
- Posiblemente agregar un campo o flag para identificar promociones "exclusivas de El Diván"

TBD: Definir las 4 secciones específicas del Mapa del Deseo
TBD: Diseñar la navegación y presentación visual dentro de El Diván
TBD: Determinar si se requiere filtrado especial en el listado de promociones
