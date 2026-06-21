"""
Servicio de Narrativa - Lucien Bot

Gestion de la historia interactiva, arquetipos y progreso de usuarios.
Con la voz caracteristica de Lucien.
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.database import SessionLocal
from models.models import (
    Archetype,
    ArchetypeType,
    NodeType,
    StoryAchievement,
    StoryChoice,
    StoryNode,
    TransactionSource,
    UserStoryAchievement,
    UserStoryProgress,
)
from services.besito_service import BesitoService
from services.package_service import PackageService
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)


class StoryService:
    """Servicio para gestion de narrativa interactiva y arquetipos"""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)
        self._vip_service = VIPService(self.db)

    def is_user_vip(self, user_id: int) -> bool:
        """Delega verificación VIP para mantener handlers en un solo servicio."""
        return self._vip_service.is_user_vip(user_id)

    def close(self):
        """Cierra la sesion si fue creada por este servicio"""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== NODOS DE HISTORIA ====================

    def create_node(
        self,
        title: str,
        content: str,
        node_type: NodeType = NodeType.NARRATIVE,
        chapter: int = 1,
        order_in_chapter: int = 0,
        required_archetype: ArchetypeType = None,
        required_vip: bool = False,
        cost_besitos: int = 0,
        is_starting_node: bool = False,
        created_by: int = None,
    ) -> StoryNode:
        """Crea un nuevo nodo de historia"""
        node = StoryNode(
            title=title,
            content=content,
            node_type=node_type,
            chapter=chapter,
            order_in_chapter=order_in_chapter,
            required_archetype=required_archetype,
            required_vip=required_vip,
            cost_besitos=cost_besitos,
            is_starting_node=is_starting_node,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        logger.info(f"Nodo creado: {title} (ID: {node.id})")
        return node

    def get_node(self, node_id: int) -> StoryNode | None:
        """Obtiene un nodo por ID"""
        return self.db.query(StoryNode).filter(StoryNode.id == node_id).first()

    def get_all_nodes(self, active_only: bool = True) -> list[StoryNode]:
        """Obtiene todos los nodos"""
        query = self.db.query(StoryNode)
        if active_only:
            query = query.filter(StoryNode.is_active)
        return query.order_by(StoryNode.chapter, StoryNode.order_in_chapter).all()

    def get_nodes_by_chapter(self, chapter: int) -> list[StoryNode]:
        """Obtiene nodos de un capitulo especifico"""
        return (
            self.db.query(StoryNode)
            .filter(StoryNode.chapter == chapter, StoryNode.is_active)
            .order_by(StoryNode.order_in_chapter)
            .all()
        )

    def get_starting_node(self) -> StoryNode | None:
        """Obtiene el nodo inicial de la historia"""
        return (
            self.db.query(StoryNode).filter(StoryNode.is_starting_node, StoryNode.is_active).first()
        )

    def update_node(self, node_id: int, **kwargs) -> bool:
        """Actualiza un nodo"""
        node = self.get_node(node_id)
        if not node:
            return False

        allowed_fields = [
            "title",
            "content",
            "node_type",
            "chapter",
            "order_in_chapter",
            "required_archetype",
            "required_vip",
            "cost_besitos",
            "is_active",
            "is_starting_node",
        ]
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(node, field):
                setattr(node, field, value)

        self.db.commit()
        logger.info(f"Nodo {node_id} actualizado")
        return True

    def delete_node(self, node_id: int) -> bool:
        """Elimina un nodo; reasigna progreso y limpia referencias FK."""
        node = self.get_node(node_id)
        if not node:
            logger.warning(f"story_service | delete_node | node_id={node_id} | result=not_found")
            return False

        starting = self.get_starting_node()
        fallback_id = starting.id if starting and starting.id != node_id else None

        for progress in (
            self.db.query(UserStoryProgress)
            .filter(UserStoryProgress.current_node_id == node_id)
            .all()
        ):
            progress.current_node_id = fallback_id

        for choice in self.get_node_choices(node_id):
            self.db.delete(choice)

        for choice in self.db.query(StoryChoice).filter(StoryChoice.next_node_id == node_id).all():
            choice.next_node_id = None

        self.db.delete(node)
        self.db.commit()
        logger.info(f"story_service | delete_node | node_id={node_id} | result=ok")
        return True

    # ==================== OPCIONES/DECISIONES ====================

    def create_choice(
        self,
        node_id: int,
        text: str,
        next_node_id: int = None,
        choice_archetype: ArchetypeType = None,
        archetype_points: int = 0,
        additional_cost: int = 0,
    ) -> StoryChoice:
        """Crea una opcion de decision para un nodo"""
        choice = StoryChoice(
            node_id=node_id,
            text=text,
            next_node_id=next_node_id,
            choice_archetype=choice_archetype,
            archetype_points=archetype_points,
            additional_cost=additional_cost,
        )
        self.db.add(choice)
        self.db.commit()
        self.db.refresh(choice)
        logger.info(f"Opcion creada para nodo {node_id}")
        return choice

    def add_choice_to_node(
        self,
        node_id: int,
        text: str,
        next_node_id: int = None,
        choice_archetype: ArchetypeType = None,
        archetype_points: int = 0,
        additional_cost: int = 0,
    ) -> StoryChoice:
        """Alias para crear una opcion de decision para un nodo"""
        return self.create_choice(
            node_id=node_id,
            text=text,
            next_node_id=next_node_id,
            choice_archetype=choice_archetype,
            archetype_points=archetype_points,
            additional_cost=additional_cost,
        )

    def get_choice(self, choice_id: int) -> StoryChoice | None:
        """Obtiene una opcion por ID"""
        return self.db.query(StoryChoice).filter(StoryChoice.id == choice_id).first()

    def get_node_choices(self, node_id: int) -> list[StoryChoice]:
        """Obtiene las opciones de un nodo"""
        return self.db.query(StoryChoice).filter(StoryChoice.node_id == node_id).all()

    def update_choice(self, choice_id: int, **kwargs) -> bool:
        """Actualiza una opcion"""
        choice = self.get_choice(choice_id)
        if not choice:
            return False

        allowed_fields = ["text", "next_node_id", "archetype_points", "additional_cost"]
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(choice, field):
                setattr(choice, field, value)

        self.db.commit()
        return True

    def delete_choice(self, choice_id: int) -> bool:
        """Elimina una opcion"""
        choice = self.get_choice(choice_id)
        if choice:
            self.db.delete(choice)
            self.db.commit()
            return True
        return False

    # ==================== PROGRESO DEL USUARIO ====================

    def get_user_progress(self, user_id: int) -> UserStoryProgress | None:
        """Obtiene el progreso de un usuario"""
        return self.db.query(UserStoryProgress).filter(UserStoryProgress.user_id == user_id).first()

    def get_or_create_progress(self, user_id: int) -> UserStoryProgress:
        """Obtiene el progreso de un usuario o lo crea si no existe"""
        progress = self.get_user_progress(user_id)
        if not progress:
            progress = self.create_user_progress(user_id)
        return progress

    def create_user_progress(
        self, user_id: int, starting_node_id: int = None, *, commit: bool = True
    ) -> UserStoryProgress:
        """Crea el progreso inicial para un usuario."""
        progress = UserStoryProgress(
            user_id=user_id,
            current_node_id=starting_node_id,
            archetype=None,
            visited_nodes="[]",
            current_chapter=1,
        )
        self.db.add(progress)
        if commit:
            self.db.commit()
            self.db.refresh(progress)
        else:
            self.db.flush()
        logger.info(f"story_service | create_progress | user_id={user_id} | result=ok")
        return progress

    def has_started_story(self, user_id: int) -> bool:
        """Verifica si el usuario ha iniciado la historia"""
        progress = self.get_user_progress(user_id)
        return progress is not None

    def grant_node_access(
        self, user_id: int, node_id: int, *, reference_fulfillment_id: int
    ) -> tuple[bool, str | None]:
        """Desbloquea nodo por compra sin debit ni avance de historia principal."""
        node = self.get_node(node_id)
        if not node or not node.is_active:
            return False, LucienVoice.story_fragment_unavailable()
        from models.models import OrderFulfillment

        fulfillment = (
            self.db.query(OrderFulfillment)
            .filter(OrderFulfillment.id == reference_fulfillment_id)
            .first()
        )
        if fulfillment and fulfillment.auto_result:
            try:
                auto = json.loads(fulfillment.auto_result)
                if auto.get("node_granted"):
                    logger.info(
                        f"story_service | grant_node_access | user_id={user_id} | "
                        f"node_id={node_id} | result=idem"
                    )
                    return True, None
            except (json.JSONDecodeError, TypeError):
                pass
        progress = self.get_or_create_progress(user_id)
        visited = self._parse_visited_nodes(progress)
        if node_id not in visited:
            visited.append(node_id)
            progress.visited_nodes = json.dumps(visited)
        if fulfillment:
            fulfillment.auto_result = json.dumps({"node_granted": True, "node_id": node_id})
        self.db.commit()
        logger.info(
            f"story_service | grant_node_access | user_id={user_id} | node_id={node_id} | result=ok"
        )
        return True, None

    def _compute_access_cost(self, node: StoryNode, choice_id: int | None) -> int:
        """Costo total de acceso: nodo + recargo de elección."""
        total = node.cost_besitos
        if choice_id:
            choice = self.get_choice(choice_id)
            if choice:
                total += choice.additional_cost
        return total

    def _parse_visited_nodes(self, progress: UserStoryProgress | None) -> list[int]:
        """Parse seguro de visited_nodes JSON."""
        if not progress or not progress.visited_nodes:
            return []
        try:
            return json.loads(progress.visited_nodes)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "story_service | parse_visited_nodes | result=corrupt_json"
            )
            return []

    def _is_node_visited(self, progress: UserStoryProgress | None, node_id: int) -> bool:
        """True si el usuario ya visitó el nodo (pay-once para cost_besitos)."""
        return node_id in self._parse_visited_nodes(progress)

    def _compute_debit_amount(
        self, node: StoryNode, choice_id: int | None, already_visited: bool
    ) -> int:
        """Monto a debitar: node.cost_besitos solo en primera visita; additional_cost siempre."""
        amount = 0 if already_visited else node.cost_besitos
        if choice_id:
            choice = self.get_choice(choice_id)
            if choice:
                amount += choice.additional_cost
        return amount

    def _has_fulfillment_node_unlock(self, user_id: int, node_id: int) -> bool:
        """True si STORY_UNLOCK fulfilled otorgó acceso a este nodo."""
        from models.models import FulfillmentKind, FulfillmentStatus, OrderFulfillment

        rows = (
            self.db.query(OrderFulfillment)
            .filter(
                OrderFulfillment.user_id == user_id,
                OrderFulfillment.fulfillment_kind == FulfillmentKind.STORY_UNLOCK,
                OrderFulfillment.status == FulfillmentStatus.FULFILLED,
            )
            .all()
        )
        for row in rows:
            if not row.auto_result:
                continue
            try:
                auto = json.loads(row.auto_result)
            except (json.JSONDecodeError, TypeError):
                continue
            if auto.get("node_id") == node_id:
                return True
        return False

    def can_access_node(
        self,
        user_id: int,
        node_id: int,
        is_vip: bool | None = None,
        choice_id: int | None = None,
    ) -> tuple:
        """Verifica si el usuario puede acceder a un nodo. Retorna (puede_acceder, razon)."""
        if is_vip is None:
            is_vip = self.is_user_vip(user_id)

        node = self.get_node(node_id)
        if not node or not node.is_active:
            return False, LucienVoice.story_fragment_unavailable()

        if self._has_fulfillment_node_unlock(user_id, node_id):
            return True, None

        progress = self.get_user_progress(user_id)

        if node.required_vip and not is_vip:
            return False, LucienVoice.story_fragment_vip_required()

        if node.required_archetype and (
            not progress or progress.archetype != node.required_archetype
        ):
            archetype_name = node.required_archetype.value.title()
            return False, LucienVoice.story_fragment_archetype_required(archetype_name)

        already_visited = self._is_node_visited(progress, node_id)
        debit_amount = self._compute_debit_amount(node, choice_id, already_visited)
        if debit_amount > 0:
            balance = self.besito_service.get_balance(user_id)
            if balance < debit_amount:
                return False, LucienVoice.story_fragment_cost_needed(debit_amount)

        return True, None

    def resolve_next_narrative_node(self, node_id: int) -> int | None:
        """Siguiente nodo lineal en el mismo capítulo (sin elecciones)."""
        node = self.get_node(node_id)
        if not node:
            return None
        chapter_nodes = self.get_nodes_by_chapter(node.chapter)
        current_idx = next((i for i, n in enumerate(chapter_nodes) if n.id == node_id), -1)
        if current_idx >= 0 and current_idx + 1 < len(chapter_nodes):
            return chapter_nodes[current_idx + 1].id
        return None

    def validate_continue_transition(self, user_id: int, target_node_id: int) -> tuple[bool, str | None]:
        """Valida que target_node_id sea el sucesor lineal desde el nodo actual."""
        progress = self.get_user_progress(user_id)
        if not progress or not progress.current_node_id:
            return False, LucienVoice.story_fragment_unavailable()
        expected = self.resolve_next_narrative_node(progress.current_node_id)
        if expected != target_node_id:
            return False, LucienVoice.story_fragment_unavailable()
        return True, None

    def _validate_choice_transition(
        self, user_id: int, choice_id: int, target_node_id: int
    ) -> tuple[bool, str | None]:
        """Valida que choice_id pertenezca al nodo actual y apunte al destino."""
        choice = self.get_choice(choice_id)
        if not choice:
            return False, LucienVoice.story_invalid_choice()

        progress = self.get_user_progress(user_id)
        if not progress or progress.current_node_id != choice.node_id:
            return False, LucienVoice.story_invalid_choice()

        expected_next = choice.next_node_id
        if expected_next is None:
            if target_node_id != choice.node_id:
                return False, LucienVoice.story_invalid_choice()
        elif expected_next != target_node_id:
            return False, LucienVoice.story_invalid_choice()

        return True, None

    def _debit_node_access_cost(
        self, user_id: int, node: StoryNode, choice_id: int | None, already_visited: bool
    ) -> bool:
        """Debita costo: pay-once en node.cost_besitos; additional_cost siempre con choice_id."""
        total_cost = self._compute_debit_amount(node, choice_id, already_visited)
        if total_cost <= 0:
            return True

        return self.besito_service.debit_besitos(
            user_id=user_id,
            amount=total_cost,
            source=TransactionSource.PURCHASE,
            description=f"Acceso a fragmento: {node.title}",
            reference_id=node.id,
            commit=False,
        )

    def _apply_progress_update(
        self, progress: UserStoryProgress, node: StoryNode, choice_id: int | None
    ) -> None:
        """Actualiza progreso, visitas y puntos de arquetipo (sin commit)."""
        if choice_id:
            choice = self.get_choice(choice_id)
            if choice and choice.archetype_points > 0:
                self._add_archetype_points(progress, choice)

        progress.current_node_id = node.id
        progress.current_chapter = node.chapter
        progress.last_interaction = datetime.now(UTC)

        visited = json.loads(progress.visited_nodes)
        if node.id not in visited:
            visited.append(node.id)
            progress.visited_nodes = json.dumps(visited)

        if node.node_type == NodeType.ENDING:
            progress.completed_at = datetime.now(UTC)
            if not progress.archetype:
                progress.archetype = progress.get_dominant_archetype()

    def _lock_user_progress(self, user_id: int) -> UserStoryProgress | None:
        """Bloquea fila de progreso para evitar doble débito concurrente."""
        return (
            self.db.query(UserStoryProgress)
            .filter(UserStoryProgress.user_id == user_id)
            .with_for_update()
            .first()
        )

    def _execute_advance_transaction(
        self,
        user_id: int,
        node: StoryNode,
        choice_id: int | None,
    ) -> tuple[bool, str | None, UserStoryProgress | None]:
        """Transacción atómica: lock progreso, débito, actualización."""
        for attempt in range(2):
            savepoint = self.db.begin_nested()
            try:
                progress = self._lock_user_progress(user_id)
                if not progress:
                    try:
                        progress = self.create_user_progress(user_id, node.id, commit=False)
                    except IntegrityError:
                        savepoint.rollback()
                        if attempt == 0:
                            logger.info(
                                f"story_service | execute_advance | user_id={user_id} | "
                                f"result=concurrent_progress_retry"
                            )
                            continue
                        logger.warning(
                            f"story_service | execute_advance | user_id={user_id} | "
                            f"result=concurrent_progress_failed"
                        )
                        return False, LucienVoice.story_payment_failed(), None

                already_visited = self._is_node_visited(progress, node.id)
                if not self._debit_node_access_cost(
                    user_id, node, choice_id, already_visited
                ):
                    savepoint.rollback()
                    return False, LucienVoice.story_payment_failed(), None

                self._apply_progress_update(progress, node, choice_id)
                savepoint.commit()
                self.db.commit()
                self.db.refresh(progress)
                return True, None, progress
            except IntegrityError:
                savepoint.rollback()
                if attempt == 0:
                    logger.info(
                        f"story_service | execute_advance | user_id={user_id} | "
                        f"result=integrity_retry"
                    )
                    continue
                logger.warning(
                    f"story_service | execute_advance | user_id={user_id} | "
                    f"result=integrity_failed"
                )
                return False, LucienVoice.story_payment_failed(), None
            except Exception:
                savepoint.rollback()
                logger.exception(
                    f"story_service | execute_advance | user_id={user_id} | "
                    f"node_id={node.id} | result=error"
                )
                return False, LucienVoice.story_payment_failed(), None

        return False, LucienVoice.story_payment_failed(), None

    def advance_to_node(
        self,
        user_id: int,
        node_id: int,
        choice_id: int | None = None,
        is_vip: bool | None = None,
    ) -> tuple:
        """Avanza al usuario a un nuevo nodo. Retorna (exito, mensaje, progreso)."""
        if is_vip is None:
            is_vip = self.is_user_vip(user_id)

        if choice_id is not None:
            valid, reason = self._validate_choice_transition(user_id, choice_id, node_id)
            if not valid:
                logger.info(
                    f"story_service | advance_denied | user_id={user_id} | "
                    f"choice_id={choice_id} | result=invalid_choice"
                )
                return False, reason, None

        can_access, reason = self.can_access_node(user_id, node_id, is_vip, choice_id)
        if not can_access:
            logger.info(
                f"story_service | advance_denied | user_id={user_id} | "
                f"node_id={node_id} | result=access_denied"
            )
            return False, reason, None

        node = self.get_node(node_id)
        if not node:
            return False, LucienVoice.story_fragment_unavailable(), None

        success, message, progress = self._execute_advance_transaction(
            user_id, node, choice_id
        )
        if not success:
            return False, message, None

        try:
            self._check_achievements(user_id, progress)
        except Exception:
            logger.exception(
                f"story_service | check_achievements | user_id={user_id} | result=error"
            )

        logger.info(
            f"story_service | advance_to_node | user_id={user_id} | "
            f"node_id={node_id} | result=ok"
        )
        return True, None, progress

    def _add_archetype_points(self, progress: UserStoryProgress, choice: StoryChoice):
        """Agrega puntos al arquetipo correspondiente de la eleccion (sin commit — se delega al llamador)."""
        if not choice.choice_archetype:
            # Si la opcion no define arquetipo, no sumar puntos
            return

        archetype_field = f"{choice.choice_archetype.value}_points"
        if hasattr(progress, archetype_field):
            current = getattr(progress, archetype_field)
            setattr(progress, archetype_field, current + choice.archetype_points)

    def _check_achievements(self, user_id: int, progress: UserStoryProgress):
        """Verifica y otorga logros al usuario"""
        achievements = self.db.query(StoryAchievement).filter(StoryAchievement.is_active).all()

        for achievement in achievements:
            # Verificar si ya lo tiene
            existing = (
                self.db.query(UserStoryAchievement)
                .filter(
                    UserStoryAchievement.user_id == user_id,
                    UserStoryAchievement.achievement_id == achievement.id,
                )
                .first()
            )

            if existing:
                continue

            requirements: list[bool] = []
            if achievement.required_node_id:
                visited = self._parse_visited_nodes(progress)
                requirements.append(achievement.required_node_id in visited)
            if achievement.required_archetype:
                requirements.append(progress.archetype == achievement.required_archetype)
            if achievement.required_chapter:
                requirements.append(progress.current_chapter >= achievement.required_chapter)

            if requirements and all(requirements):
                self._grant_achievement(user_id, achievement)

    def _grant_achievement(self, user_id: int, achievement: StoryAchievement):
        """Otorga un logro al usuario (achievement + besitos en una transacción si hay recompensa).

        reward_package_id: valida existencia del paquete; entrega async vía bot queda diferida
        (requiere contexto Telegram). Se registra el logro con reward_delivered=False.
        """
        achievement_name = achievement.name
        user_achievement = UserStoryAchievement(
            user_id=user_id, achievement_id=achievement.id, reward_delivered=False
        )
        self.db.add(user_achievement)

        try:
            if achievement.reward_besitos > 0:
                user_achievement.reward_delivered = True
                user_achievement.reward_delivered_at = datetime.now(UTC)
                if not self.besito_service.credit_besitos(
                    user_id=user_id,
                    amount=achievement.reward_besitos,
                    source=TransactionSource.MISSION,
                    description=f"Logro desbloqueado: {achievement_name}",
                    reference_id=achievement.id,
                ):
                    self.db.expunge(user_achievement)
                    logger.error(
                        f"story_service | grant_achievement | user_id={user_id} | "
                        f"result=credit_failed | achievement={achievement_name}"
                    )
                    return
            elif achievement.reward_package_id:
                pkg_svc = PackageService(self.db)
                package = pkg_svc.get_package(achievement.reward_package_id)
                if package:
                    logger.info(
                        f"story_service | grant_achievement | user_id={user_id} | "
                        f"result=package_pending | achievement={achievement_name} | "
                        f"package_id={achievement.reward_package_id}"
                    )
                else:
                    logger.warning(
                        f"story_service | grant_achievement | user_id={user_id} | "
                        f"result=package_not_found | package_id={achievement.reward_package_id}"
                    )
                self.db.commit()
            else:
                self.db.commit()
        except IntegrityError:
            self.db.rollback()
            logger.info(
                f"story_service | grant_achievement | user_id={user_id} | "
                f"result=duplicate | achievement={achievement_name}"
            )
            return

        logger.info(
            f"story_service | grant_achievement | user_id={user_id} | "
            f"result=ok | achievement={achievement_name}"
        )

    # ==================== ARQUETIPOS ====================

    def create_archetype(
        self,
        archetype_type: ArchetypeType,
        name: str,
        description: str,
        traits: dict = None,
        unlock_description: str = None,
        welcome_message: str = None,
        created_by: int = None,
    ) -> Archetype:
        """Crea un nuevo arquetipo"""
        archetype = Archetype(
            archetype_type=archetype_type,
            name=name,
            description=description,
            traits=json.dumps(traits) if traits else None,
            unlock_description=unlock_description,
            welcome_message=welcome_message,
            created_by=created_by,
        )
        self.db.add(archetype)
        self.db.commit()
        self.db.refresh(archetype)
        logger.info(f"Arquetipo creado: {name}")
        return archetype

    def get_archetype(self, archetype_type: ArchetypeType) -> Archetype | None:
        """Obtiene un arquetipo por tipo"""
        return self.db.query(Archetype).filter(Archetype.archetype_type == archetype_type).first()

    def get_all_archetypes(self) -> list[Archetype]:
        """Obtiene todos los arquetipos"""
        return self.db.query(Archetype).all()

    def assign_archetype_to_user(
        self, user_id: int, archetype_type: ArchetypeType, *, force: bool = False
    ) -> bool:
        """Asigna un arquetipo a un usuario (inmutable tras primera asignación)."""
        progress = self.get_user_progress(user_id)
        if not progress:
            return False

        if progress.archetype and not force:
            logger.info(
                f"story_service | assign_archetype | user_id={user_id} | "
                f"result=already_assigned | archetype={progress.archetype.value}"
            )
            return False

        progress.archetype = archetype_type
        self.db.commit()
        logger.info(
            f"story_service | assign_archetype | user_id={user_id} | "
            f"result=ok | archetype={archetype_type.value}"
        )
        return True

    def update_archetype(self, archetype_type: ArchetypeType, **kwargs) -> bool:
        """Actualiza metadatos de un arquetipo existente (tipo fijo)."""
        archetype = self.get_archetype(archetype_type)
        if not archetype:
            return False

        allowed_fields = ["name", "description", "unlock_description", "welcome_message", "traits"]
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(archetype, field):
                if field == "traits" and value is not None:
                    value = json.dumps(value)
                setattr(archetype, field, value)

        self.db.commit()
        logger.info(
            f"story_service | update_archetype | type={archetype_type.value} | result=ok"
        )
        return True

    def get_user_archetype(self, user_id: int) -> ArchetypeType | None:
        """Obtiene el arquetipo de un usuario"""
        progress = self.get_user_progress(user_id)
        return progress.archetype if progress else None

    def calculate_archetype(self, progress: UserStoryProgress) -> ArchetypeType | None:
        """Calcula el arquetipo dominante basado en los puntos acumulados"""
        return progress.get_dominant_archetype()

    def get_archetype_description(self, archetype_type: ArchetypeType) -> str:
        """Obtiene la descripcion de un arquetipo"""
        archetype = self.get_archetype(archetype_type)
        return archetype.description if archetype else "Un misterio por descubrir..."

    # ==================== LOGROS ====================

    def create_achievement(
        self,
        name: str,
        description: str,
        icon: str = "🏆",
        required_node_id: int = None,
        required_archetype: ArchetypeType = None,
        required_chapter: int = None,
        reward_besitos: int = 0,
        reward_package_id: int = None,
        created_by: int = None,
    ) -> StoryAchievement:
        """Crea un nuevo logro"""
        achievement = StoryAchievement(
            name=name,
            description=description,
            icon=icon,
            required_node_id=required_node_id,
            required_archetype=required_archetype,
            required_chapter=required_chapter,
            reward_besitos=reward_besitos,
            reward_package_id=reward_package_id,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(achievement)
        self.db.commit()
        self.db.refresh(achievement)
        logger.info(f"Logro creado: {name}")
        return achievement

    def get_all_achievements(self, active_only: bool = True) -> list[StoryAchievement]:
        """Obtiene todos los logros disponibles"""
        query = self.db.query(StoryAchievement)
        if active_only:
            query = query.filter(StoryAchievement.is_active)
        return query.order_by(desc(StoryAchievement.created_at)).all()

    def get_user_achievements(self, user_id: int) -> list[UserStoryAchievement]:
        """Obtiene los logros de un usuario con datos del logro eager-loaded."""
        return (
            self.db.query(UserStoryAchievement)
            .options(joinedload(UserStoryAchievement.achievement))
            .filter(UserStoryAchievement.user_id == user_id)
            .order_by(desc(UserStoryAchievement.unlocked_at))
            .all()
        )

    def get_visited_node_count(self, user_id: int) -> int:
        """Cuenta nodos visitados con parse seguro del JSON."""
        progress = self.get_user_progress(user_id)
        if not progress or not progress.visited_nodes:
            return 0
        try:
            return len(json.loads(progress.visited_nodes))
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                f"story_service | get_visited_node_count | user_id={user_id} | result=corrupt_json"
            )
            return 0

    # ==================== CUESTIONARIO DE ARQUETIPO ====================

    def get_archetype_quiz_questions(self) -> list[dict]:
        """
        Retorna las preguntas del cuestionario para determinar arquetipo.
        Cada pregunta tiene opciones que suman puntos a diferentes arquetipos.
        """
        return [
            {
                "question": "Cuando observa el contenido de Diana, que es lo que mas le atrae?",
                "options": [
                    {
                        "text": "La sensualidad y el deseo que transmite",
                        "points": {"seductor": 3, "intrepido": 1},
                    },
                    {
                        "text": "Los detalles y la estetica cuidada",
                        "points": {"observer": 3, "misterioso": 1},
                    },
                    {
                        "text": "La conexion genuina que siento",
                        "points": {"devoto": 3, "seductor": 1},
                    },
                    {
                        "text": "Descubrir cosas nuevas cada vez",
                        "points": {"explorador": 3, "intrepido": 1},
                    },
                    {
                        "text": "El misterio que hay detras",
                        "points": {"misterioso": 3, "observer": 1},
                    },
                    {
                        "text": "La audacia de mostrarse sin filtros",
                        "points": {"intrepido": 3, "explorador": 1},
                    },
                ],
            },
            {
                "question": "Como describiria su relacion con Diana?",
                "options": [
                    {
                        "text": "Un juego de seduccion mutua",
                        "points": {"seductor": 3, "misterioso": 1},
                    },
                    {"text": "Soy un observador atento", "points": {"observer": 3, "devoto": 1}},
                    {"text": "Leal y comprometido", "points": {"devoto": 3, "intrepido": 1}},
                    {
                        "text": "Una aventura que disfruto explorar",
                        "points": {"explorador": 3, "seductor": 1},
                    },
                    {
                        "text": "Algo profundo y enigmatico",
                        "points": {"misterioso": 3, "observer": 1},
                    },
                    {"text": "Intensa y sin limites", "points": {"intrepido": 3, "explorador": 1}},
                ],
            },
            {
                "question": "Que busca principalmente en la experiencia?",
                "options": [
                    {"text": "Placer y disfrute", "points": {"seductor": 3, "explorador": 1}},
                    {"text": "Contemplar y apreciar", "points": {"observer": 3, "misterioso": 1}},
                    {"text": "Conexion y cercania", "points": {"devoto": 3, "seductor": 1}},
                    {
                        "text": "Novedad y descubrimiento",
                        "points": {"explorador": 3, "intrepido": 1},
                    },
                    {"text": "Profundidad y significado", "points": {"misterioso": 3, "devoto": 1}},
                    {"text": "Emocion intensa", "points": {"intrepido": 3, "seductor": 1}},
                ],
            },
        ]

    def calculate_quiz_scores(self, answers: list[int]) -> dict[str, int]:
        """Calcula puntuaciones por arquetipo desde respuestas del cuestionario."""
        questions = self.get_archetype_quiz_questions()
        scores = {archetype.value: 0 for archetype in ArchetypeType}

        for i, answer_idx in enumerate(answers):
            if i < len(questions):
                question = questions[i]
                if 0 <= answer_idx < len(question["options"]):
                    option = question["options"][answer_idx]
                    for archetype, points in option["points"].items():
                        scores[archetype] += points
        return scores

    def apply_quiz_scores_to_progress(
        self, progress: UserStoryProgress, answers: list[int]
    ) -> None:
        """Persiste totales del quiz en las columnas *_points del progreso."""
        scores = self.calculate_quiz_scores(answers)
        for archetype_value, points in scores.items():
            if points <= 0:
                continue
            field = f"{archetype_value}_points"
            if hasattr(progress, field):
                current = getattr(progress, field)
                setattr(progress, field, current + points)

    def calculate_archetype_from_quiz(self, answers: list[int]) -> ArchetypeType:
        """
        Calcula el arquetipo basado en las respuestas del cuestionario.
        answers es una lista de indices de opciones seleccionadas.
        """
        scores = self.calculate_quiz_scores(answers)
        dominant = max(scores, key=scores.get)
        return ArchetypeType(dominant)

    # ==================== ESTADISTICAS ====================

    def get_story_stats(self) -> dict:
        """Obtiene estadisticas de la narrativa"""
        total_nodes = self.db.query(StoryNode).filter(StoryNode.is_active).count()
        total_chapters = (
            self.db.query(StoryNode.chapter).filter(StoryNode.is_active).distinct().count()
        )

        total_users = self.db.query(UserStoryProgress).count()
        completed_users = (
            self.db.query(UserStoryProgress)
            .filter(UserStoryProgress.completed_at.isnot(None))
            .count()
        )

        archetype_counts = {}
        for archetype in ArchetypeType:
            count = (
                self.db.query(UserStoryProgress)
                .filter(UserStoryProgress.archetype == archetype)
                .count()
            )
            archetype_counts[archetype.value] = count

        total_achievements = (
            self.db.query(StoryAchievement).filter(StoryAchievement.is_active).count()
        )

        return {
            "total_nodes": total_nodes,
            "total_chapters": total_chapters,
            "total_users": total_users,
            "completed_users": completed_users,
            "archetype_distribution": archetype_counts,
            "total_achievements": total_achievements,
        }

    def __del__(self):
        """Cierra la sesion de base de datos (fallback)"""
        self.close()


# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (narrative domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# to avoid re-entrancy with _grant_achievement (which already does a credit for rewards).
# =============================================================================


async def on_besitos_awarded_from_gamification(payload: dict) -> None:
    """
    Listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos post-commit).

    DESIRED: log reception with full context; PoC is observational + wiring proof.
    Future extensions (progress by besitos, hints, etc.) belong in this module and
    should use get_service(StoryService) if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"narrative | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative).
