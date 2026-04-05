"""
Servicio de Paquetes - Lucien Bot

Gestiona la creación, edición y entrega de paquetes de contenido.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from aiogram.types import InputMediaPhoto, InputMediaVideo
from models.models import Package, PackageFile, Category
from models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class PackageService:
    """Servicio para gestión de paquetes"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    # ==================== CREACIÓN DE PAQUETES ====================
    
    def create_package(self, name: str, description: str = None,
                       store_stock: int = -1, reward_stock: int = -1,
                       created_by: int = None) -> Package:
        """
        Crea un nuevo paquete.
        
        Args:
            name: Nombre del paquete
            description: Descripción opcional
            store_stock: Stock para tienda (-1 = ilimitado)
            reward_stock: Stock para recompensas (-1 = ilimitado)
            created_by: ID del admin que crea el paquete
        
        Returns:
            El paquete creado
        """
        package = Package(
            name=name,
            description=description,
            store_stock=store_stock,
            reward_stock=reward_stock,
            created_by=created_by,
            is_active=True
        )
        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        logger.info(f"Paquete creado: {name} (ID: {package.id})")
        return package
    
    def add_file_to_package(self, package_id: int, file_id: str,
                            file_type: str, file_name: str = None,
                            file_size: int = None,
                            order_index: int = 0) -> PackageFile:
        """
        Agrega un archivo a un paquete.
        
        Args:
            package_id: ID del paquete
            file_id: ID del archivo en Telegram
            file_type: Tipo de archivo (photo, video, document, animation)
            file_name: Nombre original del archivo
            file_size: Tamaño en bytes
            order_index: Orden en la secuencia
        
        Returns:
            El archivo creado
        """
        file_entry = PackageFile(
            package_id=package_id,
            file_id=file_id,
            file_type=file_type,
            file_name=file_name,
            file_size=file_size,
            order_index=order_index
        )
        self.db.add(file_entry)
        self.db.commit()
        self.db.refresh(file_entry)
        logger.info(f"Archivo agregado al paquete {package_id}: {file_type}")
        return file_entry
    
    # ==================== CONSULTAS ====================
    
    def get_package(self, package_id: int) -> Optional[Package]:
        """Obtiene un paquete por ID"""
        return self.db.query(Package).filter(Package.id == package_id).first()
    
    def get_all_packages(self, active_only: bool = True) -> List[Package]:
        """Obtiene todos los paquetes"""
        query = self.db.query(Package)
        if active_only:
            query = query.filter(Package.is_active == True)
        return query.order_by(desc(Package.created_at)).all()
    
    def get_available_packages_for_store(self) -> List[Package]:
        """Obtiene paquetes disponibles en tienda"""
        return self.db.query(Package).filter(
            Package.is_active == True,
            (Package.store_stock == -1) | (Package.store_stock > 0)
        ).order_by(desc(Package.created_at)).all()
    
    def get_available_packages_for_rewards(self) -> List[Package]:
        """Obtiene paquetes disponibles para recompensas"""
        return self.db.query(Package).filter(
            Package.is_active == True,
            (Package.reward_stock == -1) | (Package.reward_stock > 0)
        ).order_by(desc(Package.created_at)).all()
    
    def get_package_files(self, package_id: int) -> List[PackageFile]:
        """Obtiene los archivos de un paquete ordenados"""
        return self.db.query(PackageFile).filter(
            PackageFile.package_id == package_id
        ).order_by(PackageFile.order_index).all()
    
    # ==================== ACTUALIZACIÓN ====================
    
    def update_package(self, package_id: int, **kwargs) -> bool:
        """
        Actualiza un paquete.
        
        Args:
            package_id: ID del paquete
            **kwargs: Campos a actualizar (name, description, store_stock, reward_stock, is_active)
        
        Returns:
            True si se actualizó correctamente
        """
        package = self.get_package(package_id)
        if not package:
            return False
        
        allowed_fields = ['name', 'description', 'store_stock', 'reward_stock', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(package, field):
                setattr(package, field, value)
        
        self.db.commit()
        logger.info(f"Paquete {package_id} actualizado")
        return True
    
    def delete_package(self, package_id: int) -> bool:
        """
        Elimina (desactiva) un paquete.
        
        Args:
            package_id: ID del paquete
        
        Returns:
            True si se eliminó correctamente
        """
        return self.update_package(package_id, is_active=False)
    
    def remove_file_from_package(self, file_id: int) -> bool:
        """
        Elimina un archivo de un paquete.
        
        Args:
            file_id: ID del archivo en la base de datos
        
        Returns:
            True si se eliminó correctamente
        """
        file_entry = self.db.query(PackageFile).filter(PackageFile.id == file_id).first()
        if file_entry:
            self.db.delete(file_entry)
            self.db.commit()
            logger.info(f"Archivo {file_id} eliminado del paquete")
            return True
        return False
    
    # ==================== STOCK ====================
    
    def decrement_store_stock(self, package_id: int) -> bool:
        """
        Decrementa el stock de tienda de un paquete.
        
        Args:
            package_id: ID del paquete
        
        Returns:
            True si había stock disponible y se decrementó
        """
        package = self.get_package(package_id)
        if not package:
            return False
        
        success = package.decrement_store_stock()
        if success:
            self.db.commit()
            logger.info(f"Stock de tienda decrementado para paquete {package_id}")
        return success
    
    def decrement_reward_stock(self, package_id: int) -> bool:
        """
        Decrementa el stock de recompensas de un paquete.
        
        Args:
            package_id: ID del paquete
        
        Returns:
            True si había stock disponible y se decrementó
        """
        package = self.get_package(package_id)
        if not package:
            return False
        
        success = package.decrement_reward_stock()
        if success:
            self.db.commit()
            logger.info(f"Stock de recompensas decrementado para paquete {package_id}")
        return success
    
    def add_store_stock(self, package_id: int, amount: int) -> bool:
        """Agrega stock a la tienda"""
        package = self.get_package(package_id)
        if not package:
            return False
        
        if package.store_stock >= 0:
            package.store_stock += amount
            self.db.commit()
            logger.info(f"Agregados {amount} al stock de tienda del paquete {package_id}")
        return True
    
    def add_reward_stock(self, package_id: int, amount: int) -> bool:
        """Agrega stock a recompensas"""
        package = self.get_package(package_id)
        if not package:
            return False
        
        if package.reward_stock >= 0:
            package.reward_stock += amount
            self.db.commit()
            logger.info(f"Agregados {amount} al stock de recompensas del paquete {package_id}")
        return True
    
    # ==================== ENTREGA ====================
    
    def _build_media_groups(self, files: List[PackageFile]) -> Tuple[List[List], List[PackageFile]]:
        """
        Construye grupos de media para enviar como album.

        Args:
            files: Lista de archivos del paquete

        Returns:
            Tuple (lista de media groups, lista de archivos individuales)
        """
        media_groups = []
        current_group = []
        individual_files = []

        for file_entry in files:
            # Solo fotos y videos pueden agruparse
            if file_entry.file_type == "photo":
                media = InputMediaPhoto(media=file_entry.file_id)
                current_group.append(media)
            elif file_entry.file_type == "video":
                media = InputMediaVideo(media=file_entry.file_id)
                current_group.append(media)
            else:
                # Animaciones y documentos van individual
                individual_files.append(file_entry)
                continue

            # Telegram permite max 10 items por media_group
            if len(current_group) == 10:
                media_groups.append(current_group)
                current_group = []

        # Agregar grupo residual si existe
        if current_group:
            media_groups.append(current_group)

        return media_groups, individual_files

    async def deliver_package_to_user(self, bot, user_id: int, package_id: int) -> Tuple[bool, str]:
        """
        Entrega un paquete a un usuario enviando todos los archivos.
        Fotos y videos se agrupan en albums; animaciones y documentos se envían individual.

        Args:
            bot: Instancia del bot
            user_id: ID del usuario destino
            package_id: ID del paquete

        Returns:
            Tuple (éxito, mensaje)
        """
        package = self.get_package(package_id)
        if not package:
            return False, "Paquete no encontrado"

        files = self.get_package_files(package_id)
        if not files:
            return False, "El paquete no contiene archivos"

        try:
            # Construir grupos de media
            media_groups, individual_files = self._build_media_groups(files)

            # Enviar mensaje introductorio
            await bot.send_message(
                chat_id=user_id,
                text=f"""🎩 <b>Lucien:</b>

<i>Diana ha preparado algo especial para usted...</i>

📦 <b>{package.name}</b>

<i>{package.description or 'Un obsequio del reino...'}</i>

Enviando {len(files)} archivo(s)...""",
                parse_mode="HTML"
            )

            # Enviar media groups (fotos y videos agrupados)
            for media_group in media_groups:
                try:
                    await bot.send_media_group(
                        chat_id=user_id,
                        media=media_group
                    )
                except Exception as e:
                    logger.error(f"Error enviando media_group: {e}")

            # Enviar archivos individuales (animaciones y documentos)
            for file_entry in individual_files:
                try:
                    if file_entry.file_type == "animation":
                        await bot.send_animation(
                            chat_id=user_id,
                            animation=file_entry.file_id
                        )
                    else:  # document y otros
                        await bot.send_document(
                            chat_id=user_id,
                            document=file_entry.file_id,
                            caption=file_entry.file_name
                        )
                except Exception as e:
                    logger.error(f"Error enviando archivo {file_entry.id}: {e}")
                    continue

            logger.info(f"Paquete {package_id} entregado a usuario {user_id}")
            return True, f"Paquete '{package.name}' entregado exitosamente"

        except Exception as e:
            logger.error(f"Error entregando paquete {package_id}: {e}")
            return False, "Error al entregar el paquete"
    
    # ==================== ESTADÍSTICAS ====================
    
    def get_package_stats(self, package_id: int) -> dict:
        """Obtiene estadísticas de un paquete"""
        package = self.get_package(package_id)
        if not package:
            return {}
        
        files = self.get_package_files(package_id)
        
        return {
            'id': package.id,
            'name': package.name,
            'description': package.description,
            'file_count': len(files),
            'store_stock': package.store_stock,
            'reward_stock': package.reward_stock,
            'is_active': package.is_active,
            'available_in_store': package.is_available_in_store,
            'available_for_reward': package.is_available_for_reward
        }
    
    # ==================== CATEGORÍAS ====================

    def create_category(self, name: str, description: str = None,
                        order_index: int = 0) -> Category:
        """
        Crea una nueva categoría.

        Args:
            name: Nombre de la categoría
            description: Descripción opcional
            order_index: Orden de visualización

        Returns:
            La categoría creada
        """
        category = Category(
            name=name,
            description=description,
            order_index=order_index,
            is_active=True
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        logger.info(f"Categoría creada: {name} (ID: {category.id})")
        return category

    def get_category(self, category_id: int) -> Optional[Category]:
        """Obtiene una categoría por ID"""
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_all_categories(self, active_only: bool = True) -> List[Category]:
        """Obtiene todas las categorías ordenadas por order_index"""
        query = self.db.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.order_index).all()

    def update_category(self, category_id: int, **kwargs) -> bool:
        """
        Actualiza una categoría.

        Args:
            category_id: ID de la categoría
            **kwargs: Campos a actualizar (name, description, order_index, is_active)

        Returns:
            True si se actualizó correctamente
        """
        category = self.get_category(category_id)
        if not category:
            return False

        allowed_fields = ['name', 'description', 'order_index', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(category, field):
                setattr(category, field, value)

        self.db.commit()
        logger.info(f"Categoría {category_id} actualizada")
        return True

    def delete_category(self, category_id: int) -> bool:
        """
        Elimina (desactiva) una categoría.

        Args:
            category_id: ID de la categoría

        Returns:
            True si se eliminó correctamente
        """
        return self.update_category(category_id, is_active=False)

    def assign_package_to_category(self, package_id: int, category_id: int) -> bool:
        """
        Asigna un paquete a una categoría.

        Args:
            package_id: ID del paquete
            category_id: ID de la categoría

        Returns:
            True si se asignó correctamente
        """
        package = self.get_package(package_id)
        if not package:
            return False

        category = self.get_category(category_id)
        if not category:
            return False

        package.category_id = category_id
        self.db.commit()
        logger.info(f"Paquete {package_id} asignado a categoría {category_id}")
        return True

    def get_packages_by_category(self, category_id: int, active_only: bool = True) -> List[Package]:
        """
        Obtiene los paquetes de una categoría.

        Args:
            category_id: ID de la categoría
            active_only: Si solo obtener paquetes activos

        Returns:
            Lista de paquetes
        """
        query = self.db.query(Package).filter(Package.category_id == category_id)
        if active_only:
            query = query.filter(Package.is_active == True)
        return query.order_by(desc(Package.created_at)).all()

    def __del__(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
