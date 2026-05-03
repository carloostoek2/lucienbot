"""
QuestionSet Service - Gestión de Sets de Preguntas de Trivia

Lógica de negocio para crear, activar y gestionar sets temáticos de preguntas.
"""
import logging
from typing import Optional

from models.database import SessionLocal
from models.models import QuestionSet

logger = logging.getLogger(__name__)


class QuestionSetService:
    """Servicio para gestionar sets de preguntas de trivia"""

    def __init__(self, db=None):
        """Acepta db opcional para compatibilidad con get_service"""
        pass

    def close(self):
        """Cierra el servicio (no hay recursos externos)"""
        pass

    def get_all_sets(self) -> list[QuestionSet]:
        """Obtiene todos los sets ordenados por fecha de creación descendente"""
        with SessionLocal() as session:
            sets = session.query(QuestionSet).order_by(QuestionSet.created_at.desc()).all()
            logger.info(f"question_set_service - get_all_sets - count: {len(sets)}")
            return sets

    def get_set_by_name(self, name: str) -> Optional[QuestionSet]:
        """Obtiene un set por nombre"""
        with SessionLocal() as session:
            return session.query(QuestionSet).filter(QuestionSet.name == name).first()

    def get_set_by_id(self, set_id: int) -> Optional[QuestionSet]:
        """Obtiene un set por ID"""
        with SessionLocal() as session:
            return session.get(QuestionSet, set_id)

    def create_set(
        self,
        name: str,
        file_path: str,
        description: Optional[str] = None
    ) -> Optional[QuestionSet]:
        """Crea un nuevo set de preguntas"""
        with SessionLocal() as session:
            try:
                new_set = QuestionSet(
                    name=name,
                    file_path=file_path,
                    description=description,
                    is_active=False,
                    is_override=False
                )
                session.add(new_set)
                session.commit()
                session.refresh(new_set)
                logger.info(
                    f"question_set_service - create_set - success: "
                    f"set_id={new_set.id}, name={name}"
                )
                return new_set
            except Exception as e:
                session.rollback()
                logger.error(f"question_set_service - create_set - error: {e}")
                return None

    def activate_set(self, set_id: int) -> Optional[QuestionSet]:
        """Activa un set como override, desactivando cualquier override anterior"""
        with SessionLocal() as session:
            try:
                # Desactivar override en todos los sets
                session.query(QuestionSet).filter(
                    QuestionSet.is_override == True
                ).update({"is_active": False, "is_override": False})

                # Activar el set seleccionado
                target_set = session.get(QuestionSet, set_id)
                if target_set:
                    target_set.is_active = True
                    target_set.is_override = True
                    session.commit()
                    session.refresh(target_set)
                    logger.info(
                        f"question_set_service - activate_set - success: "
                        f"set_id={set_id}, name={target_set.name}"
                    )
                return target_set
            except Exception as e:
                session.rollback()
                logger.error(f"question_set_service - activate_set - error: {e}")
                return None

    def deactivate_all_overrides(self) -> int:
        """Desactiva todos los overrides, devuelve la cantidad de sets actualizados"""
        with SessionLocal() as session:
            try:
                updated = session.query(QuestionSet).filter(
                    QuestionSet.is_override == True
                ).update({"is_active": False, "is_override": False})
                session.commit()
                logger.info(
                    f"question_set_service - deactivate_all_overrides - "
                    f"sets_updated={updated}"
                )
                return updated
            except Exception as e:
                session.rollback()
                logger.error(f"question_set_service - deactivate_all_overrides - error: {e}")
                return 0

    def exists_by_name(self, name: str) -> bool:
        """Verifica si existe un set con el nombre dado"""
        with SessionLocal() as session:
            return session.query(QuestionSet).filter(QuestionSet.name == name).first() is not None