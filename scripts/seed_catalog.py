#!/usr/bin/env python3
"""Seed idempotente del catálogo Kinky (22 productos, 5 tiers).

Crea productos con nombre, descripción, precio, tier y fulfillment ya configurados.
package_id, story_node_id y tariff_id quedan en NULL hasta que el custodio los enlace
desde el admin (o hasta que se pasen env vars opcionales al ejecutar el script).

Env opcionales (solo si ya tienes IDs reales):
  SEED_PLACEHOLDER_PACKAGE_ID
  SEED_PLACEHOLDER_STORY_NODE_ID
  SEED_PLACEHOLDER_TARIFF_ID
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal
from models.models import DeliveryMode, FulfillmentKind, StoreProduct, StoreTier

# (name, description, tier_slug, price, mode, kind, monthly_cap|None, fulfillment_config)
PRODUCTS = [
    (
        "Detrás del Velo",
        "Una foto que no estaba destinada para todos. Ahora es tuya.",
        "impulso",
        50,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "La Mañana de Diana",
        "3 minutos de su día que jamás verás en ningún otro lado.",
        "impulso",
        65,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "El Primer Susurro",
        "Un audio. Una confesión. Una cosa que solo tú sabrás.",
        "impulso",
        80,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "30s del Sensorium",
        "Una muestra de lo que se siente cuando el placer tiene textura sonora.",
        "impulso",
        90,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "Kinky Stamps",
        "Pack de stickers exclusivos. Para que el chat tenga su propio idioma.",
        "impulso",
        70,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "Fragmento Temático",
        "10–15 fotos de una sesión completa. Lencería, cosplay — lo que el destino decida.",
        "deseo",
        200,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "El Corto",
        "2 minutos. Sin prisa. Solo Diana.",
        "deseo",
        250,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "Primero Tú",
        "Acceso 24h antes que nadie al próximo lanzamiento. Para los que saben esperar.",
        "deseo",
        160,
        DeliveryMode.AUTO,
        FulfillmentKind.PRIVILEGE_EARLY_ACCESS,
        None,
        {"early_access_hours": 24},
    ),
    (
        "Una Sola Pregunta",
        "Escríbela. Diana la responde en audio. Solo una, pero respondida de verdad.",
        "deseo",
        300,
        DeliveryMode.MANUAL,
        FulfillmentKind.USER_INPUT_THEN_MANUAL,
        None,
        {"input_type": "question", "min_length": 3, "max_length": 500},
    ),
    (
        "Sesión Completa",
        "25+ fotos. No fragmentos: la sesión entera tal como fue.",
        "exclusivo",
        500,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "El Largo",
        "7 minutos. Diana en su elemento. Sin cortes.",
        "exclusivo",
        600,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "Ventaja Kinky",
        "Early access al siguiente drop + 20% de descuento. Para los que planean.",
        "exclusivo",
        450,
        DeliveryMode.MANUAL,
        FulfillmentKind.PRIVILEGE_EARLY_ACCESS,
        None,
        {"early_access_hours": 24, "companion_discount_pct": 20},
    ),
    (
        "Fragmento de la Historia",
        "Un capítulo exclusivo de la narrativa de Diana. Acceso que no se compra con dinero.",
        "exclusivo",
        700,
        DeliveryMode.AUTO,
        FulfillmentKind.STORY_UNLOCK,
        None,
        {},
    ),
    (
        "La Elección de Diana",
        "Ella abre el archivo. Ella elige. Lo que llega es lo que pensó que querías.",
        "reservado",
        1000,
        DeliveryMode.MANUAL,
        FulfillmentKind.PACKAGE_DEFERRED,
        None,
        {},
    ),
    (
        "Kinky Legendario",
        "Tu título en la descripción del canal durante un mes. Permanente en la memoria del reino.",
        "reservado",
        850,
        DeliveryMode.MANUAL,
        FulfillmentKind.CHANNEL_HONOR,
        None,
        {"honor_duration_days": 30},
    ),
    (
        "El Sensorium Completo",
        "El video y el audio neuroacústico. La experiencia sensorial que Diana diseñó desde cero.",
        "reservado",
        1200,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        None,
        {},
    ),
    (
        "La Lista",
        "Entrada a la lista de espera del Círculo Íntimo. No es una promesa. Es una posición.",
        "reservado",
        1500,
        DeliveryMode.MANUAL,
        FulfillmentKind.WAITLIST_ENTRY,
        None,
        {},
    ),
    (
        "El Director",
        "El próximo tema de sesión lo propones tú. Diana lo ejecuta. Tu fantasía, su arte.",
        "mitico",
        3000,
        DeliveryMode.MANUAL,
        FulfillmentKind.USER_INPUT_THEN_MANUAL,
        2,
        {"input_type": "session_theme"},
    ),
    (
        "En Los Créditos",
        "Tu nombre en el siguiente pack premium. Para siempre, en ese archivo.",
        "mitico",
        2200,
        DeliveryMode.MANUAL,
        FulfillmentKind.USER_INPUT_THEN_MANUAL,
        3,
        {"input_type": "credit_name"},
    ),
    (
        "Mes a Su Lado",
        "Un mes de acceso VIP ganado sin pagar. Solo con tiempo y presencia.",
        "mitico",
        2500,
        DeliveryMode.AUTO,
        FulfillmentKind.VIP_GRANT,
        3,
        {},
    ),
    (
        "Lo Que Nadie Ha Visto",
        "Contenido inédito. No está en el VIP. Existe solo para quien lo compre hoy.",
        "mitico",
        4000,
        DeliveryMode.AUTO,
        FulfillmentKind.PACKAGE,
        2,
        {},
    ),
    (
        "Círculo de Uno",
        "30 minutos de chat personalizado con Diana. Una sola unidad existe este mes.",
        "mitico",
        5000,
        DeliveryMode.MANUAL,
        FulfillmentKind.SCHEDULED_CHAT,
        1,
        {"duration_minutes": 30},
    ),
]


def _optional_env_int(name: str) -> int | None:
    """Return int only when the env var is set explicitly (no default placeholder)."""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    return int(raw)


def _resolve_foreign_keys(kind: FulfillmentKind) -> tuple[int | None, int | None, int | None]:
    """Link package/story/tariff only when custodio opted in via env vars."""
    package_id = None
    story_node_id = None
    tariff_id = None
    pkg = _optional_env_int("SEED_PLACEHOLDER_PACKAGE_ID")
    story = _optional_env_int("SEED_PLACEHOLDER_STORY_NODE_ID")
    tariff = _optional_env_int("SEED_PLACEHOLDER_TARIFF_ID")
    if kind == FulfillmentKind.PACKAGE and pkg is not None:
        package_id = pkg
    elif kind == FulfillmentKind.STORY_UNLOCK and story is not None:
        story_node_id = story
    elif kind == FulfillmentKind.VIP_GRANT and tariff is not None:
        tariff_id = tariff
    return package_id, story_node_id, tariff_id


def seed_tiers(db) -> dict[str, int]:
    slug_to_id = {}
    tiers = [
        ("impulso", "IMPULSO", "Vende curiosidad · Compra sin pensar", 50, 120, 1),
        ("deseo", "DESEO", "Vende acceso · El corazón del catálogo", 150, 350, 2),
        ("exclusivo", "EXCLUSIVO", "Vende completitud · Vale guardar para esto", 400, 700, 3),
        ("reservado", "RESERVADO", "Vende poder · Solo para los que llegaron lejos", 800, 1500, 4),
        ("mitico", "MÍTICO", "Vende leyenda · Stock limitado · Solo existe este mes", 2000, 5000, 5),
    ]
    for slug, name, tagline, pmin, pmax, order_idx in tiers:
        tier = db.query(StoreTier).filter(StoreTier.slug == slug).first()
        if not tier:
            tier = StoreTier(
                slug=slug,
                name=name,
                tagline=tagline,
                price_min=pmin,
                price_max=pmax,
                order_index=order_idx,
                is_active=True,
            )
            db.add(tier)
            db.flush()
        slug_to_id[slug] = tier.id
    db.commit()
    return slug_to_id


def seed_products(db, slug_to_id: dict[str, int]) -> tuple[int, int]:
    created = 0
    pending_link = 0
    for idx, row in enumerate(PRODUCTS):
        name, description, tier_slug, price, mode, kind, monthly_cap, cfg = row
        if db.query(StoreProduct).filter(StoreProduct.name == name).first():
            continue
        package_id, story_node_id, tariff_id = _resolve_foreign_keys(kind)
        if kind == FulfillmentKind.PACKAGE and package_id is None:
            pending_link += 1
        elif kind == FulfillmentKind.STORY_UNLOCK and story_node_id is None:
            pending_link += 1
        elif kind == FulfillmentKind.VIP_GRANT and tariff_id is None:
            pending_link += 1
        product = StoreProduct(
            name=name,
            description=description,
            price=price,
            stock=-1,
            package_id=package_id,
            delivery_mode=mode,
            fulfillment_kind=kind,
            tier_id=slug_to_id[tier_slug],
            story_node_id=story_node_id,
            tariff_id=tariff_id,
            fulfillment_config=json.dumps(cfg) if cfg else None,
            monthly_stock_cap=monthly_cap,
            sort_order=idx + 1,
            is_active=False,
        )
        db.add(product)
        created += 1
    db.commit()
    return created, pending_link


def sync_products(db, slug_to_id: dict[str, int]) -> tuple[int, int]:
    """Refresh existing catalog products (descriptions, caps, FKs) from PRODUCTS."""
    updated = 0
    pending_link = 0
    for idx, row in enumerate(PRODUCTS):
        name, description, tier_slug, price, mode, kind, monthly_cap, cfg = row
        product = db.query(StoreProduct).filter(StoreProduct.name == name).first()
        if not product:
            continue
        package_id, story_node_id, tariff_id = _resolve_foreign_keys(kind)
        product.description = description
        product.price = price
        product.delivery_mode = mode
        product.fulfillment_kind = kind
        product.tier_id = slug_to_id[tier_slug]
        product.package_id = package_id
        product.story_node_id = story_node_id
        product.tariff_id = tariff_id
        product.fulfillment_config = json.dumps(cfg) if cfg else None
        product.monthly_stock_cap = monthly_cap
        product.sort_order = idx + 1
        updated += 1
        if kind == FulfillmentKind.PACKAGE and package_id is None:
            pending_link += 1
        elif kind == FulfillmentKind.STORY_UNLOCK and story_node_id is None:
            pending_link += 1
        elif kind == FulfillmentKind.VIP_GRANT and tariff_id is None:
            pending_link += 1
    db.commit()
    return updated, pending_link


def _print_pending_link_note(pending_link: int) -> None:
    if pending_link:
        print(
            "seed_catalog | note=Productos PACKAGE/STORY_UNLOCK/VIP_GRANT sin enlace; "
            "actualiza package_id / story_node_id / tariff_id desde admin cuando tengas el contenido."
        )


def main():
    parser = argparse.ArgumentParser(description="Seed idempotente del catálogo Kinky")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Actualiza productos existentes (descripciones, caps, enlaces NULL por defecto)",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        tiers = seed_tiers(db)
        if args.sync:
            updated, pending_link = sync_products(db, tiers)
            print(
                f"seed_catalog | mode=sync | tiers={len(tiers)} | products_updated={updated} | "
                f"pending_content_link={pending_link} | result=ok"
            )
            _print_pending_link_note(pending_link)
            return
        created, pending_link = seed_products(db, tiers)
        print(
            f"seed_catalog | tiers={len(tiers)} | products_created={created} | "
            f"pending_content_link={pending_link} | result=ok"
        )
        _print_pending_link_note(pending_link)
    finally:
        db.close()


if __name__ == "__main__":
    main()