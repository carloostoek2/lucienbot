# Documentador — Pool 36 / Item 1: store-catalog-tier-nav

**Date:** 2026-06-28  
**Source:** 34-store-catalog-tier-nav-SUMMARY.md + gsd-34-store-catalog-tier-nav.log + arch/testg reports

## Outcome

Visitante ve tiers del catálogo (IMPULSO→MÍTICO) al explorar estanterías; ya no lista vacía de categorías de paquetes.

## Pattern

Cuando `docs/catalogo.md` define tiers como secciones, el menú visitante debe usar `StoreTier` + `get_tiers_for_shop`, no `Category`/`get_categories_for_shop`.

## Verifs

- 108 store tests + 89 gold smoke green
- arch PWN 0c; testg suite protege

## Pool phrase (verbatim)

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.