"""
Servicio de Paquetes - Lucien Bot

Gestiona la creación, edición y entrega de paquetes de contenido.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import Package, PackageFile
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
    
    async def deliver_package_to_user(self, bot, user_id: int, package_id: int) -> Tuple[bool, str]:
        """
        Entrega un paquete a un usuario enviando todos los archivos.
        
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
            
            # Enviar cada archivo
            for file_entry in files:
                try:
                    if file_entry.file_type == "photo":
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=file_entry.file_id
                        )
                    elif file_entry.file_type == "video":
                        await bot.send_video(
                            chat_id=user_id,
                            video=file_entry.file_id
                        )
                    elif file_entry.file_type == "animation":
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
    
    def __del__(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
