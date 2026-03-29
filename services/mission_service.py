"""
Servicio de Misiones - Lucien Bot

Gestiona la creacion, progreso y completacion de misiones.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import (
    Mission, MissionType, MissionFrequency, UserMissionProgress,
    Reward, RewardType
)
from models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class MissionService:
    """Servicio para gestion de misiones"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    # ==================== CREACION DE MISIONES ====================
    
    def create_mission(self, name: str, description: str, mission_type: MissionType,
                       target_value: int, reward_id: int = None,
                       frequency: MissionFrequency = MissionFrequency.ONE_TIME,
                       start_date: datetime = None, end_date: datetime = None,
                       created_by: int = None) -> Mission:
        """Crea una nueva mision"""
        mission = Mission(
            name=name,
            description=description,
            mission_type=mission_type,
            target_value=target_value,
            reward_id=reward_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            is_active=True
        )
        self.db.add(mission)
        self.db.commit()
        self.db.refresh(mission)
        logger.info(f"Mision creada: {name} (ID: {mission.id})")
        return mission
    
    # ==================== CONSULTAS ====================
    
    def get_mission(self, mission_id: int) -> Optional[Mission]:
        """Obtiene una mision por ID"""
        return self.db.query(Mission).filter(Mission.id == mission_id).first()
    
    def get_all_missions(self, active_only: bool = True) -> List[Mission]:
        """Obtiene todas las misiones"""
        query = self.db.query(Mission)
        if active_only:
            query = query.filter(Mission.is_active == True)
        return query.order_by(desc(Mission.created_at)).all()
    
    def get_available_missions(self) -> List[Mission]:
        """Obtiene misiones disponibles actualmente"""
        now = datetime.utcnow()
        return self.db.query(Mission).filter(
            Mission.is_active == True,
            (Mission.start_date == None) | (Mission.start_date <= now),
            (Mission.end_date == None) | (Mission.end_date >= now)
        ).order_by(desc(Mission.created_at)).all()
    
    def get_missions_by_type(self, mission_type: MissionType) -> List[Mission]:
        """Obtiene misiones por tipo"""
        return self.db.query(Mission).filter(
            Mission.mission_type == mission_type,
            Mission.is_active == True
        ).all()
    
    # ==================== PROGRESO DE USUARIO ====================
    
    def get_or_create_progress(self, user_id: int, mission_id: int) -> UserMissionProgress:
        """Obtiene o crea el progreso de un usuario en una mision"""
        mission = self.get_mission(mission_id)
        if not mission:
            raise ValueError("Mision no encontrada")
        
        progress = self.db.query(UserMissionProgress).filter(
            UserMissionProgress.user_id == user_id,
            UserMissionProgress.mission_id == mission_id
        ).first()
        
        if not progress:
            progress = UserMissionProgress(
                user_id=user_id,
                mission_id=mission_id,
                target_value=mission.target_value,
                current_value=0,
                is_completed=False
            )
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)
            logger.info(f"Progreso creado: user={user_id}, mission={mission_id}")
        
        return progress
    
    def get_user_progress(self, user_id: int, mission_id: int) -> Optional[UserMissionProgress]:
        """Obtiene el progreso de un usuario en una mision"""
        return self.db.query(UserMissionProgress).filter(
            UserMissionProgress.user_id == user_id,
            UserMissionProgress.mission_id == mission_id
        ).first()
    
    def get_user_all_progress(self, user_id: int) -> List[UserMissionProgress]:
        """Obtiene todo el progreso de un usuario"""
        return self.db.query(UserMissionProgress).filter(
            UserMissionProgress.user_id == user_id
        ).order_by(desc(UserMissionProgress.last_updated)).all()
    
    def get_user_active_missions(self, user_id: int) -> List[dict]:
        """Obtiene las misiones activas de un usuario con su progreso"""
        available_missions = self.get_available_missions()
        result = []
        
        for mission in available_missions:
            progress = self.get_user_progress(user_id, mission.id)
            
            if progress and progress.is_completed and mission.frequency == MissionFrequency.ONE_TIME:
                continue  # Mision completada y no recurrente
            
            if not progress:
                progress = self.get_or_create_progress(user_id, mission.id)
            
            result.append({
                'mission': mission,
                'progress': progress,
                'percentage': min(100, int((progress.current_value / mission.target_value) * 100))
            })
        
        return result
    
    # ==================== ACTUALIZACION DE PROGRESO ====================
    
    def increment_progress(self, user_id: int, mission_type: MissionType, 
                           amount: int = 1) -> List[UserMissionProgress]:
        """
        Incrementa el progreso del usuario en todas las misiones del tipo especificado.
        Retorna las misiones completadas.
        """
        missions = self.get_missions_by_type(mission_type)
        completed = []
        
        for mission in missions:
            if not mission.is_available:
                continue
            
            progress = self.get_or_create_progress(user_id, mission.id)
            
            # Si ya esta completada y no es recurrente, saltar
            if progress.is_completed and mission.frequency == MissionFrequency.ONE_TIME:
                continue
            
            # Si esta completada y es recurrente, reiniciar
            if progress.is_completed and mission.frequency == MissionFrequency.RECURRING:
                progress.current_value = 0
                progress.is_completed = False
                progress.completed_at = None
            
            # Incrementar progreso
            progress.current_value += amount
            
            # Verificar completitud
            if progress.current_value >= mission.target_value:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
                completed.append(progress)
                logger.info(f"Mision completada: user={user_id}, mission={mission.id}")
            
            self.db.commit()
        
        return completed
    
    def set_progress(self, user_id: int, mission_id: int, value: int) -> Optional[UserMissionProgress]:
        """Establece el progreso de un usuario a un valor especifico"""
        mission = self.get_mission(mission_id)
        if not mission:
            return None
        
        progress = self.get_or_create_progress(user_id, mission_id)
        progress.current_value = value
        
        if progress.current_value >= mission.target_value:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
        else:
            progress.is_completed = False
            progress.completed_at = None
        
        self.db.commit()
        return progress
    
    # ==================== ACTUALIZACION Y ELIMINACION ====================
    
    def update_mission(self, mission_id: int, **kwargs) -> bool:
        """Actualiza una mision"""
        mission = self.get_mission(mission_id)
        if not mission:
            return False
        
        allowed_fields = ['name', 'description', 'target_value', 'reward_id', 
                         'frequency', 'start_date', 'end_date', 'is_active']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(mission, field):
                setattr(mission, field, value)
        
        self.db.commit()
        logger.info(f"Mision {mission_id} actualizada")
        return True
    
    def delete_mission(self, mission_id: int) -> bool:
        """Elimina (desactiva) una mision"""
        return self.update_mission(mission_id, is_active=False)
    
    # ==================== ESTADISTICAS ====================
    
    def get_mission_stats(self, mission_id: int) -> dict:
        """Obtiene estadisticas de una mision"""
        mission = self.get_mission(mission_id)
        if not mission:
            return {}
        
        progress_list = self.db.query(UserMissionProgress).filter(
            UserMissionProgress.mission_id == mission_id
        ).all()
        
        total_users = len(progress_list)
        completed = sum(1 for p in progress_list if p.is_completed)
        in_progress = total_users - completed
        
        return {
            'mission_name': mission.name,
            'total_users': total_users,
            'completed': completed,
            'in_progress': in_progress,
            'completion_rate': round((completed / total_users * 100), 2) if total_users > 0 else 0
        }
    
    def __del__(self):
        """Cierra la sesion de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
