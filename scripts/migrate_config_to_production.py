"""
Script de migración de configuración a producción - Lucien Bot

Este script migra la configuración inicial de gamificación a la base de datos
de producción en Railway (PostgreSQL).

Ejecutar en Railway:
    python scripts/migrate_config_to_production.py

O desde local con DATABASE_URL de producción:
    DATABASE_URL="postgresql://..." python scripts/migrate_config_to_production.py
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.models import (
    ReactionEmoji, DailyGiftConfig, Package, StoreProduct,
    Reward, RewardType, Mission, MissionType, MissionFrequency,
    Archetype, ArchetypeType, Base
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Obtiene la URL de la base de datos."""
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        # SQLAlchemy requiere postgresql:// en lugar de postgres://
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


def migrate_reaction_emojis(session):
    """Migra los emojis de reacción."""
    logger.info("Migrando emojis de reacción...")

    emojis_data = [
        ('🔥', 'Fuego', 2),
        ('😈', 'Diablillo', 2),
        ('💋', 'Beso', 2),
        ('❤️', 'Corazón', 2),
    ]

    for emoji_char, name, value in emojis_data:
        existing = session.query(ReactionEmoji).filter(
            ReactionEmoji.emoji == emoji_char
        ).first()

        if not existing:
            emoji = ReactionEmoji(
                emoji=emoji_char,
                name=name,
                besito_value=value,
                is_active=True
            )
            session.add(emoji)
            logger.info(f"  ✓ Creado: {emoji_char} ({name}) = {value} besitos")
        else:
            # Actualizar valores si ya existe
            existing.besito_value = value
            existing.is_active = True
            logger.info(f"  ℹ Actualizado: {emoji_char}")

    session.commit()
    logger.info("  ✓ Emojis migrados")


def migrate_daily_gift_config(session):
    """Migra la configuración del regalo diario."""
    logger.info("Migrando configuración de regalo diario...")

    config = session.query(DailyGiftConfig).first()
    if not config:
        config = DailyGiftConfig(besito_amount=5, is_active=True)
        session.add(config)
        logger.info("  ✓ Creado: 5 besitos por regalo diario")
    else:
        config.besito_amount = 5
        config.is_active = True
        logger.info("  ✓ Actualizado: 5 besitos por regalo diario")

    session.commit()


def migrate_packages(session):
    """Migra los paquetes de contenido."""
    logger.info("Migrando paquetes...")

    packages_data = [
        ('Pack Bienvenida - 5 Fotos', 'Pack de 5 fotos para onboarding (primera reacción)', -1, -1),
        ('Pack 1 - 10 Fotos', 'Pack de 10 fotos', -1, -2),
        ('Pack 2 - 20 Fotos', 'Pack de 20 fotos (requiere racha)', -1, -2),
        ('Pack 3 - 30 Fotos VIP', 'Pack de 30 fotos exclusivo para VIP', -1, -2),
        ('Pack Sorpresa', 'Entre 5 y 15 fotos aleatorias', -1, -2),
        ('Pool Sorpresa', 'Pool de contenido para packs sorpresa', -1, -2),
    ]

    package_map = {}  # Mapeo nombre -> ID

    for name, desc, store_stock, reward_stock in packages_data:
        existing = session.query(Package).filter(Package.name == name).first()

        if not existing:
            pkg = Package(
                name=name,
                description=desc,
                store_stock=store_stock,
                reward_stock=reward_stock,
                is_active=True
            )
            session.add(pkg)
            session.flush()  # Para obtener el ID
            package_map[name] = pkg.id
            logger.info(f"  ✓ Creado: {name} (ID: {pkg.id})")
        else:
            package_map[name] = existing.id
            logger.info(f"  ℹ Ya existe: {name} (ID: {existing.id})")

    session.commit()
    return package_map


def migrate_store_products(session, package_map):
    """Migra los productos de la tienda."""
    logger.info("Migrando productos de tienda...")

    products_data = [
        ('Pack 1 - 10 Fotos', '10 fotos para disfrutar', 'Pack 1 - 10 Fotos', 80, -1),
        ('Pack 2 - 20 Fotos', '20 fotos (desbloquea con racha de 3 reacciones)', 'Pack 2 - 20 Fotos', 150, -1),
        ('Pack 3 - 30 Fotos VIP', '30 fotos exclusivo para miembros VIP', 'Pack 3 - 30 Fotos VIP', 300, -1),
        ('Pack Sorpresa', 'Entre 5 y 15 fotos aleatorias', 'Pack Sorpresa', 70, -1),
    ]

    for name, desc, pkg_name, price, stock in products_data:
        pkg_id = package_map.get(pkg_name)
        if not pkg_id:
            logger.warning(f"  ⚠ Paquete no encontrado: {pkg_name}")
            continue

        existing = session.query(StoreProduct).filter(StoreProduct.name == name).first()

        if not existing:
            product = StoreProduct(
                name=name,
                description=desc,
                package_id=pkg_id,
                price=price,
                stock=stock,
                is_active=True
            )
            session.add(product)
            logger.info(f"  ✓ Creado: {name} - {price} besitos")
        else:
            logger.info(f"  ℹ Ya existe: {name}")

    session.commit()


def migrate_rewards(session, package_map):
    """Migra las recompensas."""
    logger.info("Migrando recompensas...")

    rewards_data = [
        ('Besitos - Recompensa Básica', '5 besitos por reaccionar', RewardType.BESITOS, 5, None),
        ('Besitos - Recompensa Racha', '15 besitos por racha de 3 posts', RewardType.BESITOS, 15, None),
        ('Pack Bienvenida', 'Pack de 5 fotos para nuevos usuarios', RewardType.PACKAGE, None, 'Pack Bienvenida - 5 Fotos'),
    ]

    reward_map = {}

    for name, desc, r_type, besitos, pkg_name in rewards_data:
        pkg_id = None
        if pkg_name:
            pkg_id = package_map.get(pkg_name)

        existing = session.query(Reward).filter(Reward.name == name).first()

        if not existing:
            reward = Reward(
                name=name,
                description=desc,
                reward_type=r_type,
                besito_amount=besitos,
                package_id=pkg_id,
                is_active=True
            )
            session.add(reward)
            session.flush()
            reward_map[name] = reward.id

            if r_type == RewardType.BESITOS:
                logger.info(f"  ✓ Creado: {name} - {besitos} besitos")
            else:
                logger.info(f"  ✓ Creado: {name} - Paquete")
        else:
            reward_map[name] = existing.id
            logger.info(f"  ℹ Ya existe: {name}")

    session.commit()
    return reward_map


def migrate_missions(session, reward_map):
    """Migra las misiones."""
    logger.info("Migrando misiones...")

    missions_data = [
        ('Reacciona y Gana', 'Reacciona a la última publicación para ganar besitos',
         MissionType.REACTION_COUNT, 1, MissionFrequency.RECURRING, 'Besitos - Recompensa Básica'),
        ('Racha de 3 Posts', 'Reacciona a 3 publicaciones consecutivas para obtener la recompensa de racha',
         MissionType.REACTION_COUNT, 3, MissionFrequency.RECURRING, 'Besitos - Recompensa Racha'),
    ]

    for name, desc, m_type, target, freq, reward_name in missions_data:
        reward_id = reward_map.get(reward_name)

        existing = session.query(Mission).filter(Mission.name == name).first()

        if not existing:
            mission = Mission(
                name=name,
                description=desc,
                mission_type=m_type,
                target_value=target,
                frequency=freq,
                reward_id=reward_id,
                is_active=True
            )
            session.add(mission)
            logger.info(f"  ✓ Creado: {name}")
        else:
            logger.info(f"  ℹ Ya existe: {name}")

    session.commit()


def migrate_archetypes(session):
    """Migra los arquetipos."""
    logger.info("Migrando arquetipos...")

    archetypes_data = [
        (ArchetypeType.SEDUCTOR, 'El Seductor',
         'Busca el placer y la conquista. Disfruta del juego de la seducción y la atracción mutua.',
         'Sumando puntos al elegir opciones que buscan placer y disfrute.',
         'Bienvenido al círculo de los que buscan el placer sin reservas...'),

        (ArchetypeType.OBSERVER, 'El Observador',
         'Analiza y contempla. Valora los detalles y la estética cuidada.',
         'Sumando puntos al elegir opciones que valoran la contemplación.',
         'Tu mirada atenta no escapa nada. Bienvenido, Observador...'),

        (ArchetypeType.DEVOTO, 'El Devoto',
         'Leal y dedicado. Busca la conexión genuina y la cercanía.',
         'Sumando puntos al elegir opciones que priorizan la conexión.',
         'Tu lealtad es tu mayor virtud. El círculo te recibe, Devoto...'),

        (ArchetypeType.EXPLORADOR, 'El Explorador',
         'Curioso y aventurero. Busca la novedad y el descubrimiento constante.',
         'Sumando puntos al elegir opciones que buscan nuevas experiencias.',
         'Siempre hay algo nuevo por descubrir. Adelante, Explorador...'),

        (ArchetypeType.MISTERIOSO, 'El Misterioso',
         'Enigmático y reservado. Atraído por lo oculto y el significado profundo.',
         'Sumando puntos al elegir opciones que buscan profundidad.',
         'Los secretos te llaman. Bienvenido al lado misterioso...'),

        (ArchetypeType.INTREPIDO, 'El Intrépido',
         'Audaz y sin miedo. Busca la emoción intensa y los límites.',
         'Sumando puntos al elegir opciones audaces y sin filtros.',
         'Sin miedo, sin límites. El círculo te espera, Intrépido...'),
    ]

    for arch_type, name, desc, unlock_msg, welcome_msg in archetypes_data:
        existing = session.query(Archetype).filter(
            Archetype.archetype_type == arch_type
        ).first()

        if not existing:
            archetype = Archetype(
                archetype_type=arch_type,
                name=name,
                description=desc,
                unlock_description=unlock_msg,
                welcome_message=welcome_msg
            )
            session.add(archetype)
            logger.info(f"  ✓ Creado: {name}")
        else:
            # Actualizar si ya existe
            existing.name = name
            existing.description = desc
            existing.unlock_description = unlock_msg
            existing.welcome_message = welcome_msg
            logger.info(f"  ℹ Actualizado: {name}")

    session.commit()


def main():
    """Función principal de migración."""
    print("="*70)
    print("MIGRACIÓN DE CONFIGURACIÓN A PRODUCCIÓN - Lucien Bot")
    print("="*70)
    print()

    database_url = get_database_url()
    if not database_url:
        logger.error("ERROR: DATABASE_URL no está configurada")
        logger.error("Ejemplo: export DATABASE_URL='postgresql://user:pass@host/db'")
        sys.exit(1)

    logger.info(f"Conectando a: {database_url.split('@')[1] if '@' in database_url else 'database'}")

    try:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Verificar conexión
        session.execute(text("SELECT 1"))
        logger.info("✓ Conexión exitosa")
        print()

        # Ejecutar migraciones en orden
        migrate_reaction_emojis(session)
        migrate_daily_gift_config(session)
        package_map = migrate_packages(session)
        migrate_store_products(session, package_map)
        reward_map = migrate_rewards(session, package_map)
        migrate_missions(session, reward_map)
        migrate_archetypes(session)

        session.close()

        print()
        print("="*70)
        print("✓ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*70)
        print()
        print("Configuración migrada:")
        print("  • Emojis de reacción: 4")
        print("  • Regalo diario: configurado")
        print("  • Paquetes: 6")
        print("  • Productos de tienda: 4")
        print("  • Recompensas: 3")
        print("  • Misiones: 2")
        print("  • Arquetipos: 6")
        print()
        print("IMPORTANTE: Los paquetes están vacíos.")
        print("Usa el bot en producción para subir los archivos:")
        print("  Admin → Gestión de Paquetes → Actualizar paquete")

    except Exception as e:
        logger.error(f"ERROR durante la migración: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
