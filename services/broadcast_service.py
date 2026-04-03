"""
Servicio de Broadcasting - Lucien Bot

Gestiona el envío de mensajes a canales con sistema de reacciones.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import (
    BroadcastMessage, BroadcastReaction, ReactionEmoji,
    Channel, ChannelType, MissionType
)
from models.database import SessionLocal
from services.besito_service import BesitoService
from services.mission_service import MissionService
from models.models import TransactionSource
import logging

logger = logging.getLogger(__name__)


class BroadcastService:
    """Servicio para gestión de broadcasting con reacciones"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
    
    # ==================== CONFIGURACIÓN DE EMOJIS ====================
    
    def create_reaction_emoji(self, emoji: str, name: str = None, 
                              besito_value: int = 1) -> ReactionEmoji:
        """Crea un nuevo emoji de reacción"""
        reaction = ReactionEmoji(
            emoji=emoji,
            name=name or emoji,
            besito_value=besito_value,
            is_active=True
        )
        self.db.add(reaction)
        self.db.commit()
        self.db.refresh(reaction)
        logger.info(f"Emoji de reacción creado: {emoji} = {besito_value} besitos")
        return reaction
    
    def get_reaction_emoji(self, emoji_id: int) -> Optional[ReactionEmoji]:
        """Obtiene un emoji por ID"""
        return self.db.query(ReactionEmoji).filter(ReactionEmoji.id == emoji_id).first()
    
    def get_reaction_emoji_by_emoji(self, emoji: str) -> Optional[ReactionEmoji]:
        """Obtiene un emoji por su caracter"""
        return self.db.query(ReactionEmoji).filter(
            ReactionEmoji.emoji == emoji,
            ReactionEmoji.is_active == True
        ).first()
    
    def get_all_emojis(self, active_only: bool = True) -> List[ReactionEmoji]:
        """Obtiene todos los emojis configurados"""
        query = self.db.query(ReactionEmoji)
        if active_only:
            query = query.filter(ReactionEmoji.is_active == True)
        return query.all()
    
    def update_emoji_value(self, emoji_id: int, besito_value: int) -> bool:
        """Actualiza el valor de besitos de un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            emoji.besito_value = besito_value
            self.db.commit()
            return True
        return False
    
    def toggle_emoji(self, emoji_id: int) -> bool:
        """Activa/desactiva un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            emoji.is_active = not emoji.is_active
            self.db.commit()
            return True
        return False
    
    def delete_emoji(self, emoji_id: int) -> bool:
        """Elimina un emoji"""
        emoji = self.get_reaction_emoji(emoji_id)
        if emoji:
            self.db.delete(emoji)
            self.db.commit()
            return True
        return False
    
    # ==================== MENSAJES DE BROADCAST ====================

    def create_broadcast_message(self, message_id: int, channel_id: int,
                                  admin_id: int, text: str = None,
                                  has_attachment: bool = False,
                                  attachment_type: str = None,
                                  attachment_file_id: str = None,
                                  has_reactions: bool = False,
                                  is_protected: bool = False,
                                  selected_emoji_ids: str = None) -> BroadcastMessage:
        """Registra un mensaje de broadcast en la base de datos"""
        broadcast = BroadcastMessage(
            message_id=message_id,
            channel_id=channel_id,
            admin_id=admin_id,
            text=text,
            has_attachment=has_attachment,
            attachment_type=attachment_type,
            attachment_file_id=attachment_file_id,
            has_reactions=has_reactions,
            is_protected=is_protected,
            selected_emoji_ids=selected_emoji_ids
        )
        self.db.add(broadcast)
        self.db.commit()
        self.db.refresh(broadcast)
        logger.info(f"Mensaje de broadcast registrado: {broadcast.id}")
        return broadcast
    
    def get_broadcast(self, broadcast_id: int) -> Optional[BroadcastMessage]:
        """Obtiene un mensaje de broadcast por ID"""
        return self.db.query(BroadcastMessage).filter(
            BroadcastMessage.id == broadcast_id
        ).first()

    def get_selected_emoji_ids(self, broadcast_id: int) -> List[int]:
        """Obtiene la lista de IDs de emojis seleccionados para un broadcast"""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast or not broadcast.selected_emoji_ids:
            return []
        try:
            return [int(eid) for eid in broadcast.selected_emoji_ids.split(',') if eid]
        except (ValueError, AttributeError):
            return []
    
    def get_broadcast_by_message_id(self, message_id: int, channel_id: int) -> Optional[BroadcastMessage]:
        """Obtiene un broadcast por ID de mensaje de Telegram y canal"""
        return self.db.query(BroadcastMessage).filter(
            BroadcastMessage.message_id == message_id,
            BroadcastMessage.channel_id == channel_id
        ).first()
    
    def get_recent_broadcasts(self, channel_id: int = None, limit: int = 20) -> List[BroadcastMessage]:
        """Obtiene mensajes de broadcast recientes"""
        query = self.db.query(BroadcastMessage)
        if channel_id:
            query = query.filter(BroadcastMessage.channel_id == channel_id)
        return query.order_by(desc(BroadcastMessage.created_at)).limit(limit).all()
    
    # ==================== REACCIONES ====================
    
    def has_user_reacted(self, broadcast_id: int, user_id: int) -> bool:
        """Verifica si un usuario ya reaccionó a un mensaje"""
        reaction = self.db.query(BroadcastReaction).filter(
            BroadcastReaction.broadcast_id == broadcast_id,
            BroadcastReaction.user_id == user_id
        ).first()
        return reaction is not None
    
    def register_reaction(self, broadcast_id: int, user_id: int, 
                          emoji_id: int, username: str = None) -> Optional[BroadcastReaction]:
        """
        Registra una reacción y otorga besitos al usuario.
        Retorna None si el usuario ya reaccionó.
        """
        # Verificar si ya reaccionó (con lock para evitar race conditions)
        existing = self.db.query(BroadcastReaction).filter(
            BroadcastReaction.broadcast_id == broadcast_id,
            BroadcastReaction.user_id == user_id
        ).with_for_update().first()
        if existing:
            logger.info(f"Usuario {user_id} ya reaccionó al broadcast {broadcast_id}")
            return None
        
        # Obtener el emoji y su valor
        emoji = self.get_reaction_emoji(emoji_id)
        if not emoji:
            logger.error(f"Emoji {emoji_id} no encontrado")
            return None
        
        besito_value = emoji.besito_value
        
        try:
            # Crear la reacción
            reaction = BroadcastReaction(
                broadcast_id=broadcast_id,
                user_id=user_id,
                username=username,
                reaction_emoji_id=emoji_id,
                besitos_awarded=besito_value
            )
            self.db.add(reaction)
            
            # Acreditar besitos al usuario
            description = f"Reacción con {emoji.emoji}"
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=besito_value,
                source=TransactionSource.REACTION,
                description=description,
                reference_id=broadcast_id
            )
            
            self.db.commit()
            self.db.refresh(reaction)

            # Incrementar progreso de misiones REACTION_COUNT
            mission_service = MissionService(self.db)
            completed_missions = mission_service.increment_progress(
                user_id, MissionType.REACTION_COUNT, amount=1
            )

            logger.info(f"Reacción registrada: user={user_id}, broadcast={broadcast_id}, besitos={besito_value}, misiones_completadas={len(completed_missions)}")
            return reaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registrando reacción: {e}")
            return None
    
    def get_reactions_by_broadcast(self, broadcast_id: int) -> List[BroadcastReaction]:
        """Obtiene todas las reacciones de un mensaje"""
        return self.db.query(BroadcastReaction).filter(
            BroadcastReaction.broadcast_id == broadcast_id
        ).all()
    
    def get_reaction_count(self, broadcast_id: int) -> int:
        """Obtiene el número de reacciones de un mensaje"""
        return self.db.query(BroadcastReaction).filter(
            BroadcastReaction.broadcast_id == broadcast_id
        ).count()
    
    def get_user_reactions(self, user_id: int, limit: int = 20) -> List[BroadcastReaction]:
        """Obtiene las reacciones de un usuario"""
        return self.db.query(BroadcastReaction).filter(
            BroadcastReaction.user_id == user_id
        ).order_by(desc(BroadcastReaction.created_at)).limit(limit).all()
    
    # ==================== ESTADÍSTICAS ====================
    
    def get_broadcast_stats(self, broadcast_id: int) -> dict:
        """Obtiene estadísticas de un mensaje de broadcast"""
        broadcast = self.get_broadcast(broadcast_id)
        if not broadcast:
            return {}
        
        reactions = self.get_reactions_by_broadcast(broadcast_id)
        total_besitos = sum(r.besitos_awarded for r in reactions)
        
        # Contar por emoji
        emoji_counts = {}
        for r in reactions:
            emoji_char = r.reaction_emoji.emoji if r.reaction_emoji else "?"
            emoji_counts[emoji_char] = emoji_counts.get(emoji_char, 0) + 1
        
        return {
            'total_reactions': len(reactions),
            'total_besitos_awarded': total_besitos,
            'emoji_breakdown': emoji_counts,
            'unique_users': len(set(r.user_id for r in reactions))
        }
    
    def __del__(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
