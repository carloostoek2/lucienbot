"""
Servicio de Recompensas - Lucien Bot

Gestiona la creacion y entrega de recompensas.
"""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import (
    Reward, RewardType, UserRewardHistory,
    Package, Tariff
)
from models.database import SessionLocal
from services.besito_service import BesitoService
from services.package_service import PackageService
from services.vip_service import VIPService
from models.models import TransactionSource
import logging

logger = logging.getLogger(__name__)


class RewardService:
    """Servicio para gestion de recompensas"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self.package_service = PackageService(self.db)
        self.vip_service = VIPService(self.db)
    
    # ==================== CREACION DE RECOMPENSAS ====================
    
    def create_reward_besitos(self, name: str, description: str, 
                              besito_amount: int, created_by: int = None) -> Reward:
        """Crea una recompensa de tipo besitos"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.BESITOS,
            besito_amount=besito_amount,
            created_by=created_by,
            is_active=True
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa de besitos creada: {name} ({besito_amount} besitos)")
        return reward
    
    def create_reward_package(self, name: str, description: str,
                              package_id: int, created_by: int = None) -> Reward:
        """Crea una recompensa de tipo paquete"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.PACKAGE,
            package_id=package_id,
            created_by=created_by,
            is_active=True
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa de paquete creada: {name} (package_id={package_id})")
        return reward
    
    def create_reward_vip(self, name: str, description: str,
                          tariff_id: int, created_by: int = None) -> Reward:
        """Crea una recompensa de tipo acceso VIP"""
        reward = Reward(
            name=name,
            description=description,
            reward_type=RewardType.VIP_ACCESS,
            tariff_id=tariff_id,
            created_by=created_by,
            is_active=True
        )
        self.db.add(reward)
        self.db.commit()
        self.db.refresh(reward)
        logger.info(f"Recompensa VIP creada: {name} (tariff_id={tariff_id})")
        return reward
    
    # ==================== CONSULTAS ====================
    
    def get_reward(self, reward_id: int) -> Optional[Reward]:
        """Obtiene una recompensa por ID"""
        return self.db.query(Reward).filter(Reward.id == reward_id).first()
    
    def get_all_rewards(self, active_only: bool = True) -> List[Reward]:
        """Obtiene todas las recompensas"""
        query = self.db.query(Reward)
        if active_only:
            query = query.filter(Reward.is_active == True)
        return query.order_by(desc(Reward.created_at)).all()
    
    def get_rewards_by_type(self, reward_type: RewardType) -> List[Reward]:
        """Obtiene recompensas por tipo"""
        return self.db.query(Reward).filter(
            Reward.reward_type == reward_type,
            Reward.is_active == True
        ).all()
    
    # ==================== ACTUALIZACION Y ELIMINACION ====================
    
    def update_reward(self, reward_id: int, **kwargs) -> bool:
        """Actualiza una recompensa"""
        reward = self.get_reward(reward_id)
        if not reward:
            return False
        
        allowed_fields = ['name', 'description', 'besito_amount', 
                         'package_id', 'tariff_id', 'is_active']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(reward, field):
                setattr(reward, field, value)
        
        self.db.commit()
        logger.info(f"Recompensa {reward_id} actualizada")
        return True
    
    def delete_reward(self, reward_id: int) -> bool:
        """Elimina (desactiva) una recompensa"""
        return self.update_reward(reward_id, is_active=False)
    
    # ==================== ENTREGA DE RECOMPENSAS ====================
    
    async def deliver_reward(self, bot, user_id: int, reward_id: int, 
                            mission_id: int = None) -> Tuple[bool, str]:
        """
        Entrega una recompensa a un usuario.
        
        Args:
            bot: Instancia del bot
            user_id: ID del usuario
            reward_id: ID de la recompensa
            mission_id: ID de la mision (opcional, para historial)
        
        Returns:
            Tuple (exito, mensaje)
        """
        reward = self.get_reward(reward_id)
        if not reward:
            return False, "Recompensa no encontrada"
        
        if not reward.is_active:
            return False, "Recompensa inactiva"
        
        try:
            if reward.reward_type == RewardType.BESITOS:
                return await self._deliver_besitos(user_id, reward)
            
            elif reward.reward_type == RewardType.PACKAGE:
                return await self._deliver_package(bot, user_id, reward)
            
            elif reward.reward_type == RewardType.VIP_ACCESS:
                return await self._deliver_vip_access(bot, user_id, reward)
            
            else:
                return False, "Tipo de recompensa no soportado"
        
        except Exception as e:
            logger.error(f"Error entregando recompensa {reward_id}: {e}")
            return False, f"Error al entregar recompensa: {str(e)}"
    
    async def _deliver_besitos(self, user_id: int, reward: Reward) -> Tuple[bool, str]:
        """Entrega recompensa de besitos"""
        success = self.besito_service.credit_besitos(
            user_id=user_id,
            amount=reward.besito_amount,
            source=TransactionSource.MISSION,
            description=f"Recompensa: {reward.name}",
            reference_id=reward.id
        )
        
        if success:
            balance = self.besito_service.get_balance(user_id)
            return True, f"Has recibido {reward.besito_amount} besitos! Tu saldo es: {balance}"
        else:
            return False, "Error al acreditar besitos"
    
    async def _deliver_package(self, bot, user_id: int, reward: Reward) -> Tuple[bool, str]:
        """Entrega recompensa de paquete"""
        if not reward.package_id:
            return False, "Paquete no configurado"
        
        # Verificar disponibilidad
        package = self.package_service.get_package(reward.package_id)
        if not package:
            return False, "Paquete no encontrado"
        
        if not package.is_available_for_reward:
            return False, "Paquete no disponible para recompensas"
        
        # Decrementar stock y entregar
        if not package.decrement_reward_stock():
            return False, "Stock de recompensas agotado"
        
        self.db.commit()
        
        # Enviar paquete
        success, message = await self.package_service.deliver_package_to_user(
            bot=bot, user_id=user_id, package_id=reward.package_id
        )
        
        return success, message if success else "Error al enviar paquete"
    
    async def _deliver_vip_access(self, bot, user_id: int, reward: Reward) -> Tuple[bool, str]:
        """Entrega recompensa de acceso VIP"""
        if not reward.tariff_id:
            return False, "Tarifa VIP no configurada"
        
        tariff = self.vip_service.get_tariff(reward.tariff_id)
        if not tariff:
            return False, "Tarifa no encontrada"
        
        # Generar token VIP
        token = self.vip_service.generate_token(reward.tariff_id)
        
        # Obtener info del bot para construir URL
        bot_info = await bot.get_me()
        token_url = f"https://t.me/{bot_info.username}?start={token.token_code}"
        
        # Enviar mensaje al usuario
        await bot.send_message(
            chat_id=user_id,
            text=f"""🎩 Lucien:

Diana te ha concedido acceso al circulo exclusivo...

👑 Recompensa VIP Activada

📋 Tarifa: {tariff.name}
⏱ Duracion: {tariff.duration_days} dias

🔗 Tu enlace de acceso:
{token_url}

Haz clic para activar tu membresia VIP."""
        )
        
        return True, f"Has recibido acceso VIP: {tariff.name} ({tariff.duration_days} dias)"
    
    # ==================== HISTORIAL ====================
    
    def log_reward_delivery(self, user_id: int, reward_id: int, 
                           mission_id: int = None, details: str = None):
        """Registra la entrega de una recompensa"""
        history = UserRewardHistory(
            user_id=user_id,
            reward_id=reward_id,
            mission_id=mission_id,
            details=details
        )
        self.db.add(history)
        self.db.commit()
    
    def get_user_reward_history(self, user_id: int, limit: int = 20) -> List[UserRewardHistory]:
        """Obtiene el historial de recompensas de un usuario"""
        return self.db.query(UserRewardHistory).filter(
            UserRewardHistory.user_id == user_id
        ).order_by(desc(UserRewardHistory.delivered_at)).limit(limit).all()
    
    # ==================== ESTADISTICAS ====================
    
    def get_reward_stats(self, reward_id: int) -> dict:
        """Obtiene estadisticas de una recompensa"""
        reward = self.get_reward(reward_id)
        if not reward:
            return {}
        
        deliveries = self.db.query(UserRewardHistory).filter(
            UserRewardHistory.reward_id == reward_id
        ).count()
        
        return {
            'reward_name': reward.name,
            'type': reward.reward_type.value,
            'total_deliveries': deliveries
        }
    
    def __del__(self):
        """Cierra la sesion de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
