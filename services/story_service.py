"""
Servicio de Narrativa - Lucien Bot

Gestion de la historia interactiva, arquetipos y progreso de usuarios.
Con la voz caracteristica de Lucien.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from models.models import (
    StoryNode, StoryChoice, UserStoryProgress, Archetype,
    ArchetypeType, NodeType, StoryAchievement, UserStoryAchievement,
    Package
)
from models.database import SessionLocal
from services.besito_service import BesitoService
from models.models import TransactionSource
import logging

logger = logging.getLogger(__name__)


class StoryService:
    """Servicio para gestion de narrativa interactiva y arquetipos"""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)

    def close(self):
        """Cierra la sesion si fue creada por este servicio"""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== NODOS DE HISTORIA ====================

    def create_node(self, title: str, content: str, node_type: NodeType = NodeType.NARRATIVE,
                    chapter: int = 1, order_in_chapter: int = 0,
                    required_archetype: ArchetypeType = None, required_vip: bool = False,
                    cost_besitos: int = 0, is_starting_node: bool = False,
                    created_by: int = None) -> StoryNode:
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
            is_active=True
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        logger.info(f"Nodo creado: {title} (ID: {node.id})")
        return node

    def get_node(self, node_id: int) -> Optional[StoryNode]:
        """Obtiene un nodo por ID"""
        return self.db.query(StoryNode).filter(StoryNode.id == node_id).first()

    def get_all_nodes(self, active_only: bool = True) -> List[StoryNode]:
        """Obtiene todos los nodos"""
        query = self.db.query(StoryNode)
        if active_only:
            query = query.filter(StoryNode.is_active == True)
        return query.order_by(StoryNode.chapter, StoryNode.order_in_chapter).all()

    def get_nodes_by_chapter(self, chapter: int) -> List[StoryNode]:
        """Obtiene nodos de un capitulo especifico"""
        return self.db.query(StoryNode).filter(
            StoryNode.chapter == chapter,
            StoryNode.is_active == True
        ).order_by(StoryNode.order_in_chapter).all()

    def get_starting_node(self) -> Optional[StoryNode]:
        """Obtiene el nodo inicial de la historia"""
        return self.db.query(StoryNode).filter(
            StoryNode.is_starting_node == True,
            StoryNode.is_active == True
        ).first()

    def update_node(self, node_id: int, **kwargs) -> bool:
        """Actualiza un nodo"""
        node = self.get_node(node_id)
        if not node:
            return False

        allowed_fields = ['title', 'content', 'node_type', 'chapter', 'order_in_chapter',
                         'required_archetype', 'required_vip', 'cost_besitos',
                         'is_active', 'is_starting_node']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(node, field):
                setattr(node, field, value)

        self.db.commit()
        logger.info(f"Nodo {node_id} actualizado")
        return True

    def delete_node(self, node_id: int) -> bool:
        """Elimina (desactiva) un nodo"""
        return self.update_node(node_id, is_active=False)

    # ==================== OPCIONES/DECISIONES ====================

    def create_choice(self, node_id: int, text: str, next_node_id: int = None,
                      choice_archetype: ArchetypeType = None,
                      archetype_points: int = 0, additional_cost: int = 0) -> StoryChoice:
        """Crea una opcion de decision para un nodo"""
        choice = StoryChoice(
            node_id=node_id,
            text=text,
            next_node_id=next_node_id,
            choice_archetype=choice_archetype,
            archetype_points=archetype_points,
            additional_cost=additional_cost
        )
        self.db.add(choice)
        self.db.commit()
        self.db.refresh(choice)
        logger.info(f"Opcion creada para nodo {node_id}")
        return choice

    def get_choice(self, choice_id: int) -> Optional[StoryChoice]:
        """Obtiene una opcion por ID"""
        return self.db.query(StoryChoice).filter(StoryChoice.id == choice_id).first()

    def get_node_choices(self, node_id: int) -> List[StoryChoice]:
        """Obtiene las opciones de un nodo"""
        return self.db.query(StoryChoice).filter(StoryChoice.node_id == node_id).all()

    def update_choice(self, choice_id: int, **kwargs) -> bool:
        """Actualiza una opcion"""
        choice = self.get_choice(choice_id)
        if not choice:
            return False

        allowed_fields = ['text', 'next_node_id', 'archetype_points', 'additional_cost']
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

    def get_user_progress(self, user_id: int) -> Optional[UserStoryProgress]:
        """Obtiene el progreso de un usuario"""
        return self.db.query(UserStoryProgress).filter(
            UserStoryProgress.user_id == user_id
        ).first()

    def create_user_progress(self, user_id: int, starting_node_id: int = None) -> UserStoryProgress:
        """Crea el progreso inicial para un usuario"""
        progress = UserStoryProgress(
            user_id=user_id,
            current_node_id=starting_node_id,
            archetype=None,
            visited_nodes="[]",
            current_chapter=1
        )
        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)
        logger.info(f"Progreso creado para usuario {user_id}")
        return progress

    def has_started_story(self, user_id: int) -> bool:
        """Verifica si el usuario ha iniciado la historia"""
        progress = self.get_user_progress(user_id)
        return progress is not None

    def can_access_node(self, user_id: int, node_id: int, is_vip: bool = False) -> tuple:
        """
        Verifica si el usuario puede acceder a un nodo.
        Retorna (puede_acceder, razon)
        """
        node = self.get_node(node_id)
        if not node or not node.is_active:
            return False, "Este fragmento no esta disponible"

        progress = self.get_user_progress(user_id)

        # Verificar VIP
        if node.required_vip and not is_vip:
            return False, "Este fragmento requiere acceso al circulo exclusivo"

        # Verificar arquetipo requerido
        if node.required_archetype:
            if not progress or progress.archetype != node.required_archetype:
                archetype_name = node.required_archetype.value.title()
                return False, f"Este fragmento solo esta disponible para quienes han despertado el arquetipo del {archetype_name}"

        # Verificar besitos
        if node.cost_besitos > 0:
            balance = self.besito_service.get_balance(user_id)
            if balance < node.cost_besitos:
                return False, f"Necesita {node.cost_besitos} besitos para acceder a este fragmento"

        return True, None

    def advance_to_node(self, user_id: int, node_id: int, choice_id: int = None,
                        is_vip: bool = False) -> tuple:
        """
        Avanza al usuario a un nuevo nodo.
        Retorna (exito, mensaje, progreso)
        """
        # Verificar acceso
        can_access, reason = self.can_access_node(user_id, node_id, is_vip)
        if not can_access:
            return False, reason, None

        node = self.get_node(node_id)
        progress = self.get_user_progress(user_id)

        if not progress:
            progress = self.create_user_progress(user_id, node_id)

        # Cobrar besitos si aplica
        if node.cost_besitos > 0:
            success = self.besito_service.debit_besitos(
                user_id=user_id,
                amount=node.cost_besitos,
                source=TransactionSource.PURCHASE,
                description=f"Acceso a fragmento: {node.title}",
                reference_id=node.id
            )
            if not success:
                return False, "No se pudo procesar el pago", None

        # Sumar puntos de arquetipo si viene de una eleccion
        if choice_id:
            choice = self.get_choice(choice_id)
            if choice and choice.archetype_points > 0:
                self._add_archetype_points(progress, choice)

        # Actualizar progreso
        progress.current_node_id = node_id
        progress.current_chapter = node.chapter
        progress.last_interaction = datetime.now(timezone.utc)

        # Agregar a nodos visitados
        visited = json.loads(progress.visited_nodes)
        if node_id not in visited:
            visited.append(node_id)
            progress.visited_nodes = json.dumps(visited)

        # Verificar si es nodo final
        if node.node_type == NodeType.ENDING:
            progress.completed_at = datetime.now(timezone.utc)
            # Asignar arquetipo si no tiene
            if not progress.archetype:
                progress.archetype = progress.get_dominant_archetype()

        self.db.commit()
        self.db.refresh(progress)

        # Verificar logros
        self._check_achievements(user_id, progress)

        return True, None, progress

    def _add_archetype_points(self, progress: UserStoryProgress, choice: StoryChoice):
        """Agrega puntos al arquetipo correspondiente de la eleccion"""
        if not choice.choice_archetype:
            # Si la opcion no define arquetipo, no sumar puntos
            return

        archetype_field = f"{choice.choice_archetype.value}_points"
        if hasattr(progress, archetype_field):
            current = getattr(progress, archetype_field)
            setattr(progress, archetype_field, current + choice.archetype_points)
            self.db.commit()

    def _check_achievements(self, user_id: int, progress: UserStoryProgress):
        """Verifica y otorga logros al usuario"""
        achievements = self.db.query(StoryAchievement).filter(
            StoryAchievement.is_active == True
        ).all()

        for achievement in achievements:
            # Verificar si ya lo tiene
            existing = self.db.query(UserStoryAchievement).filter(
                UserStoryAchievement.user_id == user_id,
                UserStoryAchievement.achievement_id == achievement.id
            ).first()

            if existing:
                continue

            # Verificar requisitos
            unlocked = False

            if achievement.required_node_id:
                visited = json.loads(progress.visited_nodes)
                if achievement.required_node_id in visited:
                    unlocked = True

            if achievement.required_archetype:
                if progress.archetype == achievement.required_archetype:
                    unlocked = True

            if achievement.required_chapter:
                if progress.current_chapter >= achievement.required_chapter:
                    unlocked = True

            if unlocked:
                self._grant_achievement(user_id, achievement)

    def _grant_achievement(self, user_id: int, achievement: StoryAchievement):
        """Otorga un logro al usuario"""
        user_achievement = UserStoryAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            reward_delivered=False
        )
        self.db.add(user_achievement)
        self.db.commit()

        # Otorgar recompensa en besitos
        if achievement.reward_besitos > 0:
            self.besito_service.credit_besitos(
                user_id=user_id,
                amount=achievement.reward_besitos,
                source=TransactionSource.MISSION,
                description=f"Logro desbloqueado: {achievement.name}",
                reference_id=achievement.id
            )

        logger.info(f"Logro '{achievement.name}' otorgado a usuario {user_id}")

    # ==================== ARQUETIPOS ====================

    def create_archetype(self, archetype_type: ArchetypeType, name: str,
                         description: str, traits: dict = None,
                         unlock_description: str = None,
                         welcome_message: str = None,
                         created_by: int = None) -> Archetype:
        """Crea un nuevo arquetipo"""
        archetype = Archetype(
            archetype_type=archetype_type,
            name=name,
            description=description,
            traits=json.dumps(traits) if traits else None,
            unlock_description=unlock_description,
            welcome_message=welcome_message,
            created_by=created_by
        )
        self.db.add(archetype)
        self.db.commit()
        self.db.refresh(archetype)
        logger.info(f"Arquetipo creado: {name}")
        return archetype

    def get_archetype(self, archetype_type: ArchetypeType) -> Optional[Archetype]:
        """Obtiene un arquetipo por tipo"""
        return self.db.query(Archetype).filter(
            Archetype.archetype_type == archetype_type
        ).first()

    def get_all_archetypes(self) -> List[Archetype]:
        """Obtiene todos los arquetipos"""
        return self.db.query(Archetype).all()

    def assign_archetype_to_user(self, user_id: int, archetype_type: ArchetypeType) -> bool:
        """Asigna un arquetipo a un usuario"""
        progress = self.get_user_progress(user_id)
        if not progress:
            return False

        progress.archetype = archetype_type
        self.db.commit()
        logger.info(f"Arquetipo {archetype_type.value} asignado a usuario {user_id}")
        return True

    def get_user_archetype(self, user_id: int) -> Optional[ArchetypeType]:
        """Obtiene el arquetipo de un usuario"""
        progress = self.get_user_progress(user_id)
        return progress.archetype if progress else None

    def get_archetype_description(self, archetype_type: ArchetypeType) -> str:
        """Obtiene la descripcion de un arquetipo"""
        archetype = self.get_archetype(archetype_type)
        return archetype.description if archetype else "Un misterio por descubrir..."

    # ==================== LOGROS ====================

    def create_achievement(self, name: str, description: str,
                           icon: str = "🏆",
                           required_node_id: int = None,
                           required_archetype: ArchetypeType = None,
                           required_chapter: int = None,
                           reward_besitos: int = 0,
                           reward_package_id: int = None,
                           created_by: int = None) -> StoryAchievement:
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
            is_active=True
        )
        self.db.add(achievement)
        self.db.commit()
        self.db.refresh(achievement)
        logger.info(f"Logro creado: {name}")
        return achievement

    def get_all_achievements(self, active_only: bool = True) -> List[StoryAchievement]:
        """Obtiene todos los logros disponibles"""
        query = self.db.query(StoryAchievement)
        if active_only:
            query = query.filter(StoryAchievement.is_active == True)
        return query.order_by(desc(StoryAchievement.created_at)).all()

    def get_user_achievements(self, user_id: int) -> List[UserStoryAchievement]:
        """Obtiene los logros de un usuario"""
        return self.db.query(UserStoryAchievement).filter(
            UserStoryAchievement.user_id == user_id
        ).order_by(desc(UserStoryAchievement.unlocked_at)).all()

    # ==================== CUESTIONARIO DE ARQUETIPO ====================

    def get_archetype_quiz_questions(self) -> List[Dict]:
        """
        Retorna las preguntas del cuestionario para determinar arquetipo.
        Cada pregunta tiene opciones que suman puntos a diferentes arquetipos.
        """
        return [
            {
                "question": "Cuando observa el contenido de Diana, que es lo que mas le atrae?",
                "options": [
                    {"text": "La sensualidad y el deseo que transmite", "points": {"seductor": 3, "intrepido": 1}},
                    {"text": "Los detalles y la estetica cuidada", "points": {"observer": 3, "misterioso": 1}},
                    {"text": "La conexion genuina que siento", "points": {"devoto": 3, "seductor": 1}},
                    {"text": "Descubrir cosas nuevas cada vez", "points": {"explorador": 3, "intrepido": 1}},
                    {"text": "El misterio que hay detras", "points": {"misterioso": 3, "observer": 1}},
                    {"text": "La audacia de mostrarse sin filtros", "points": {"intrepido": 3, "explorador": 1}}
                ]
            },
            {
                "question": "Como describiria su relacion con Diana?",
                "options": [
                    {"text": "Un juego de seduccion mutua", "points": {"seductor": 3, "misterioso": 1}},
                    {"text": "Soy un observador atento", "points": {"observer": 3, "devoto": 1}},
                    {"text": "Leal y comprometido", "points": {"devoto": 3, "intrepido": 1}},
                    {"text": "Una aventura que disfruto explorar", "points": {"explorador": 3, "seductor": 1}},
                    {"text": "Algo profundo y enigmatico", "points": {"misterioso": 3, "observer": 1}},
                    {"text": "Intensa y sin limites", "points": {"intrepido": 3, "explorador": 1}}
                ]
            },
            {
                "question": "Que busca principalmente en la experiencia?",
                "options": [
                    {"text": "Placer y disfrute", "points": {"seductor": 3, "explorador": 1}},
                    {"text": "Contemplar y apreciar", "points": {"observer": 3, "misterioso": 1}},
                    {"text": "Conexion y cercania", "points": {"devoto": 3, "seductor": 1}},
                    {"text": "Novedad y descubrimiento", "points": {"explorador": 3, "intrepido": 1}},
                    {"text": "Profundidad y significado", "points": {"misterioso": 3, "devoto": 1}},
                    {"text": "Emocion intensa", "points": {"intrepido": 3, "seductor": 1}}
                ]
            }
        ]

    def calculate_archetype_from_quiz(self, answers: List[int]) -> ArchetypeType:
        """
        Calcula el arquetipo basado en las respuestas del cuestionario.
        answers es una lista de indices de opciones seleccionadas.
        """
        questions = self.get_archetype_quiz_questions()
        scores = {archetype.value: 0 for archetype in ArchetypeType}

        for i, answer_idx in enumerate(answers):
            if i < len(questions):
                question = questions[i]
                if answer_idx < len(question["options"]):
                    option = question["options"][answer_idx]
                    for archetype, points in option["points"].items():
                        scores[archetype] += points

        # Retornar el arquetipo con mayor puntuacion
        dominant = max(scores, key=scores.get)
        return ArchetypeType(dominant)

    # ==================== ESTADISTICAS ====================

    def get_story_stats(self) -> dict:
        """Obtiene estadisticas de la narrativa"""
        total_nodes = self.db.query(StoryNode).filter(StoryNode.is_active == True).count()
        total_chapters = self.db.query(StoryNode.chapter).filter(
            StoryNode.is_active == True
        ).distinct().count()

        total_users = self.db.query(UserStoryProgress).count()
        completed_users = self.db.query(UserStoryProgress).filter(
            UserStoryProgress.completed_at.isnot(None)
        ).count()

        archetype_counts = {}
        for archetype in ArchetypeType:
            count = self.db.query(UserStoryProgress).filter(
                UserStoryProgress.archetype == archetype
            ).count()
            archetype_counts[archetype.value] = count

        total_achievements = self.db.query(StoryAchievement).filter(
            StoryAchievement.is_active == True
        ).count()

        return {
            'total_nodes': total_nodes,
            'total_chapters': total_chapters,
            'total_users': total_users,
            'completed_users': completed_users,
            'archetype_distribution': archetype_counts,
            'total_achievements': total_achievements
        }

    def __del__(self):
        """Cierra la sesion de base de datos (fallback)"""
        self.close()
