"""
Tests unitarios para TriviaConfigService.
"""
import pytest
from datetime import datetime
from unittest.mock import patch

from services.trivia_config_service import TriviaConfigService
from models.models import TriviaConfig


@pytest.mark.unit
class TestTriviaConfigService:
    """Tests para TriviaConfigService"""

    def test_get_config_creates_default(self, db_session):
        """Debe crear config por defecto si no existe."""
        service = TriviaConfigService(db_session)
        config = service.get_config()

        assert config is not None
        assert config.daily_trivia_limit_free == 7
        assert config.daily_trivia_limit_vip == 15
        assert config.daily_trivia_vip_limit == 5

    def test_get_config_returns_existing(self, db_session):
        """Debe retornar config existente si ya existe."""
        existing = TriviaConfig(
            daily_trivia_limit_free=10,
            daily_trivia_limit_vip=20,
            daily_trivia_vip_limit=8,
            is_active=True
        )
        db_session.add(existing)
        db_session.commit()

        service = TriviaConfigService(db_session)
        config = service.get_config()

        assert config.daily_trivia_limit_free == 10
        assert config.daily_trivia_limit_vip == 20

    def test_update_config(self, db_session):
        """Debe actualizar la configuración."""
        service = TriviaConfigService(db_session)
        config = service.update_config(
            daily_trivia_limit_free=12,
            daily_trivia_limit_vip=25,
            daily_trivia_vip_limit=10,
            admin_id=999
        )

        assert config.daily_trivia_limit_free == 12
        assert config.daily_trivia_limit_vip == 25
        assert config.daily_trivia_vip_limit == 10
        assert config.updated_by == 999
        assert config.updated_at is not None

    def test_get_limits_for_user_vip(self, db_session):
        """Debe retornar límites VIP."""
        service = TriviaConfigService(db_session)
        limits = service.get_limits_for_user(is_vip=True)

        assert limits["trivia_limit"] == 15
        assert limits["trivia_vip_limit"] == 5

    def test_get_limits_for_user_free(self, db_session):
        """Debe retornar límites Free."""
        service = TriviaConfigService(db_session)
        limits = service.get_limits_for_user(is_vip=False)

        assert limits["trivia_limit"] == 7
        assert limits["trivia_vip_limit"] == 5
