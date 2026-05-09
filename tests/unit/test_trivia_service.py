"""
Tests unitarios para TriviaCategoryService (Wave 0 stub).

Fase 16 - Trivias Especiales.
"""
import pytest
from datetime import datetime

from services.trivia_service import TriviaCategoryService
from models.models import TriviaCategory


@pytest.mark.unit
class TestTriviaCategoryService:
    """Tests para el servicio de categorias especiales de trivia."""

    def test_discover_categories_returns_list(self):
        """Verifica que discover_categories retorna una lista."""
        service = TriviaCategoryService()
        try:
            categories = service.discover_categories()
            assert isinstance(categories, list)
            # Without JSON files present, should return empty list
            for cat in categories:
                assert 'category_id' in cat
                assert 'display_name' in cat
                assert 'question_count' in cat
                assert 'file_name' in cat
        finally:
            service.close()

    def test_get_active_category_returns_none_when_none_active(self, db_session):
        """Verifica que get_active_category retorna None cuando no hay categorias activas."""
        service = TriviaCategoryService(db_session)
        result = service.get_active_category()
        assert result is None

    def test_activate_creates_new_category(self, db_session):
        """Verifica que activate crea una nueva categoria si no existe."""
        service = TriviaCategoryService(db_session)
        result = service.activate("halloween", display_name="🎃 Trivia de Halloween")
        assert result is True

        active = service.get_active_category()
        assert active is not None
        assert active['category_id'] == "halloween"
        assert active['display_name'] == "🎃 Trivia de Halloween"

    def test_activate_deactivates_previous(self, db_session):
        """Verifica D-06: activar una nueva categoria desactiva la anterior."""
        service = TriviaCategoryService(db_session)
        service.activate("halloween", display_name="Halloween")
        service.activate("navidena", display_name="Navidad")

        active = service.get_active_category()
        assert active['category_id'] == "navidena"

    def test_deactivate_clears_active(self, db_session):
        """Verifica que deactivate limpia la categoria activa."""
        service = TriviaCategoryService(db_session)
        service.activate("halloween")
        service.deactivate()

        active = service.get_active_category()
        assert active is None

    def test_category_state_transaction(self, db_session):
        """Verifica que las escrituras de estado usan transacciones atomicas."""
        service = TriviaCategoryService(db_session)
        service.activate("halloween")

        # Verify state persisted
        cat = db_session.query(TriviaCategory).filter(
            TriviaCategory.is_active == True
        ).first()
        assert cat is not None
        assert cat.category_id == "halloween"

    def test_category_file_not_found(self):
        """Verifica manejo graceful de archivos JSON inexistentes."""
        service = TriviaCategoryService()
        try:
            categories = service.discover_categories()
            # Should not raise, just return available categories
            assert isinstance(categories, list)
        finally:
            service.close()

    def test_independent_limits_stub(self):
        """Stub: verifica que limites tematicos son independientes."""
        # This test will be expanded when GameService is extended
        service = TriviaCategoryService()
        service.close()
        assert True  # Placeholder
