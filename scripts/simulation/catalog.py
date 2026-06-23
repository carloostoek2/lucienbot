"""Catálogo de productos para simulación (fuente: seed_catalog.py / docs/catalogo.md)."""

from __future__ import annotations

from dataclasses import dataclass

# (name, tier_slug, price) — 22 productos del catálogo Kinky
CATALOG_PRODUCTS: list[tuple[str, str, int]] = [
    ("Detrás del Velo", "impulso", 50),
    ("La Mañana de Diana", "impulso", 65),
    ("El Primer Susurro", "impulso", 80),
    ("30s del Sensorium", "impulso", 90),
    ("Kinky Stamps", "impulso", 70),
    ("Fragmento Temático", "deseo", 200),
    ("El Corto", "deseo", 250),
    ("Primero Tú", "deseo", 160),
    ("Una Sola Pregunta", "deseo", 300),
    ("Sesión Completa", "exclusivo", 500),
    ("El Largo", "exclusivo", 600),
    ("Ventaja Kinky", "exclusivo", 450),
    ("Fragmento de la Historia", "exclusivo", 700),
    ("La Elección de Diana", "reservado", 1000),
    ("Kinky Legendario", "reservado", 850),
    ("El Sensorium Completo", "reservado", 1200),
    ("La Lista", "reservado", 1500),
    ("El Director", "mitico", 3000),
    ("En Los Créditos", "mitico", 2200),
    ("Mes a Su Lado", "mitico", 2500),
    ("Lo Que Nadie Ha Visto", "mitico", 4000),
    ("Círculo de Uno", "mitico", 5000),
]

TIER_ORDER = ("impulso", "deseo", "exclusivo", "reservado", "mitico")
TIER_LABELS = {
    "impulso": "TIER 1 — IMPULSO (50–120)",
    "deseo": "TIER 2 — DESEO (150–350)",
    "exclusivo": "TIER 3 — EXCLUSIVO (400–700)",
    "reservado": "TIER 4 — RESERVADO (800–1,500)",
    "mitico": "TIER 5 — MÍTICO (2,000–5,000)",
}


@dataclass(frozen=True)
class StoreProductSim:
    name: str
    tier_slug: str
    price: int


def get_catalog_products() -> list[StoreProductSim]:
    return [StoreProductSim(name=n, tier_slug=t, price=p) for n, t, p in CATALOG_PRODUCTS]


def load_products_from_db() -> list[StoreProductSim]:
    """Carga productos activos desde BD (modo --from-db)."""
    from models.database import SessionLocal
    from models.models import StoreProduct, StoreTier

    db = SessionLocal()
    try:
        rows = (
            db.query(StoreProduct, StoreTier)
            .outerjoin(StoreTier, StoreProduct.tier_id == StoreTier.id)
            .filter(StoreProduct.is_active.is_(True))
            .order_by(StoreProduct.price.asc())
            .all()
        )
        products: list[StoreProductSim] = []
        for product, tier in rows:
            slug = tier.slug if tier else "sin_tier"
            products.append(
                StoreProductSim(name=product.name, tier_slug=slug, price=product.price)
            )
        return products if products else get_catalog_products()
    finally:
        db.close()