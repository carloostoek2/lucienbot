"""
Servicio de Trivias Especiales - Lucien Bot

Gestiona categorias especiales de trivia: activacion, desactivacion,
descubrimiento de archivos JSON y consulta de estado.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import TriviaCategory

logger = logging.getLogger(__name__)


class TriviaCategoryService:
    """Servicio para gestion del estado de categorias especiales de trivia."""

    QUESTIONS_DIR = Path("docs")

    # Mapping from file stem to display name
    DISPLAY_NAME_MAP = {
        "preguntas_halloween": "\U0001f383 Trivia de Halloween",
        "preguntas_navidena": "❄️ Trivia Navidena",
    }

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def discover_categories(self) -> list[dict]:
        """Enumera archivos preguntas_*.json disponibles en docs/.
        Returns list of {category_id, display_name, question_count, file_name}."""
        categories = []
        for f in self.QUESTIONS_DIR.glob("preguntas_*.json"):
            if f.stem in ("preguntas", "preguntas_vip"):
                continue
            category_id = f.stem.replace("preguntas_", "")
            display_name = self.DISPLAY_NAME_MAP.get(
                f.stem, f.stem.replace("preguntas_", "").replace("_", " ").title()
            )
            categories.append(
                {
                    "file_name": f.name,
                    "category_id": category_id,
                    "display_name": display_name,
                    "question_count": self._count_questions(f),
                }
            )
        logger.info(
            f"trivia_category_service - discover_categories - found {len(categories)} categories"
        )
        return categories

    def get_active_category(self) -> dict | None:
        """Obtiene la categoria activa actual, o None si no hay ninguna."""
        db = self._get_db()
        cat = db.query(TriviaCategory).filter(TriviaCategory.is_active).first()
        if not cat:
            return None
        return {
            "id": cat.id,
            "category_id": cat.category_id,
            "display_name": cat.display_name,
            "activated_at": cat.activated_at,
            "scheduled_end": cat.scheduled_end,
        }

    def activate(
        self, category_id: str, display_name: str = None, scheduled_end: datetime = None
    ) -> bool:
        """Activa una categoria (desactiva cualquier otra activa primero). D-06."""
        db = self._get_db()
        try:
            db.query(TriviaCategory).filter(TriviaCategory.is_active).update(
                {"is_active": False, "scheduled_end": None}
            )
            cat = db.query(TriviaCategory).filter(TriviaCategory.category_id == category_id).first()
            if cat:
                cat.is_active = True
                cat.display_name = display_name or cat.display_name
                cat.activated_at = datetime.now(UTC)
                cat.scheduled_end = scheduled_end
            else:
                cat = TriviaCategory(
                    category_id=category_id,
                    display_name=display_name or category_id,
                    is_active=True,
                    activated_at=datetime.now(UTC),
                    scheduled_end=scheduled_end,
                )
                db.add(cat)
            db.commit()
            logger.info(
                f"trivia_category_service - activate - category_id:{category_id} - activated"
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"trivia_category_service - activate - error:{e}")
            return False

    def deactivate(self, category_id: str = None) -> bool:
        """Desactiva una categoria o la activa si no se especifica."""
        db = self._get_db()
        try:
            query = db.query(TriviaCategory).filter(TriviaCategory.is_active)
            if category_id:
                query = query.filter(TriviaCategory.category_id == category_id)
            query.update({"is_active": False, "scheduled_end": None})
            db.commit()
            logger.info(
                f"trivia_category_service - deactivate - category_id:{category_id or 'all_active'} - deactivated"
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"trivia_category_service - deactivate - error:{e}")
            return False

    def _count_questions(self, path: Path) -> int:
        """Cuenta preguntas en un archivo JSON."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else len(data.get("questions", []))
        except Exception as e:
            logger.warning(
                f"trivia_category_service - _count_questions - error reading {path}: {e}"
            )
            return 0
