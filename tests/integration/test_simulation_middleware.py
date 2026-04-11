"""Integration tests for SimulationMiddleware."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from middlewares.simulation_middleware import SimulationMiddleware
from services.user_context import UserContext, SimulationRole


class TestSimulationMiddleware:
    """Test middleware context injection."""

    @pytest.fixture
    def middleware(self):
        return SimulationMiddleware()

    @pytest.fixture
    def mock_event(self):
        event = Mock()
        return event

    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 123
        return user

    @pytest.mark.asyncio
    async def test_middleware_injects_context(self, middleware, mock_event, mock_user):
        """Middleware injects user_context into data."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            assert "user_context" in data
            assert isinstance(data["user_context"], UserContext)

        with patch('middlewares.simulation_middleware.UserService') as mock_service:
            mock_instance = Mock()
            mock_instance.get_user.return_value = None  # Not in DB
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            await middleware(handler, mock_event, data)

    @pytest.mark.asyncio
    async def test_middleware_no_user(self, middleware, mock_event):
        """Middleware handles events without user."""
        data = {}  # No event_from_user

        async def handler(event, data):
            assert data.get("user_context") is None

        await middleware(handler, mock_event, data)

    @pytest.mark.asyncio
    async def test_middleware_respects_simulation(self, middleware, mock_event, mock_user):
        """Middleware uses simulation override if active."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            ctx = data["user_context"]
            assert ctx.is_simulation_active is True
            assert ctx.simulated_role == SimulationRole.VIP

        with patch('middlewares.simulation_middleware.UserService') as mock_user_svc, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            # Setup user service mock
            user_instance = Mock()
            db_user = Mock()
            db_user.role = Mock()
            db_user.role.name = "ADMIN"
            db_user.id = 123
            user_instance.get_user.return_value = db_user
            user_instance.is_admin.return_value = True
            user_instance.close = Mock()
            mock_user_svc.return_value = user_instance

            # Setup simulation service mock
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="admin",
                simulated_role=SimulationRole.VIP,
                is_simulation_active=True
            )

            await middleware(handler, mock_event, data)

    @pytest.mark.asyncio
    async def test_middleware_admin_user(self, middleware, mock_event, mock_user):
        """Middleware correctly identifies admin users."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            ctx = data["user_context"]
            assert ctx.real_role == "admin"
            assert ctx.is_admin is True

        with patch('middlewares.simulation_middleware.UserService') as mock_service, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            mock_instance = Mock()
            db_user = Mock()
            db_user.role = Mock()
            db_user.role.name = "ADMIN"
            db_user.id = 123
            mock_instance.get_user.return_value = db_user
            mock_instance.is_admin.return_value = True
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            # Setup simulation service to return admin context
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="admin"
            )

            await middleware(handler, mock_event, data)

    @pytest.mark.asyncio
    async def test_middleware_regular_user(self, middleware, mock_event, mock_user):
        """Middleware correctly identifies regular users."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            ctx = data["user_context"]
            assert ctx.real_role == "user"
            assert ctx.is_vip is False
            assert ctx.is_admin is False

        with patch('middlewares.simulation_middleware.UserService') as mock_service, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            mock_instance = Mock()
            db_user = Mock()
            db_user.role = Mock()
            db_user.role.name = "USER"
            db_user.id = 123
            mock_instance.get_user.return_value = db_user
            mock_instance.is_admin.return_value = False
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            # Setup simulation service to return user context
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="user"
            )

            await middleware(handler, mock_event, data)

    @pytest.mark.asyncio
    async def test_middleware_service_cleanup(self, middleware, mock_event, mock_user):
        """Middleware properly closes services."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            pass

        with patch('middlewares.simulation_middleware.UserService') as mock_service, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            mock_instance = Mock()
            mock_instance.get_user.return_value = None
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            # Setup simulation service
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="user"
            )

            await middleware(handler, mock_event, data)

            # Verify close was called
            mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_logs_simulation(self, middleware, mock_event, mock_user, caplog):
        """Middleware logs when user is in simulation mode."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            pass

        with patch('middlewares.simulation_middleware.UserService') as mock_service, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            mock_instance = Mock()
            mock_instance.get_user.return_value = None
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            # Setup simulation service to return simulated context
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="admin",
                simulated_role=SimulationRole.VIP,
                is_simulation_active=True
            )

            import logging
            with caplog.at_level(logging.INFO):
                await middleware(handler, mock_event, data)

            # Check that simulation was logged
            assert "simulation" in caplog.text.lower() or "vip" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_middleware_unknown_user_gets_default_role(self, middleware, mock_event, mock_user):
        """Middleware assigns 'user' role to unknown users."""
        data = {"event_from_user": mock_user}

        async def handler(event, data):
            ctx = data["user_context"]
            assert ctx.real_role == "user"

        with patch('middlewares.simulation_middleware.UserService') as mock_service, \
             patch('middlewares.simulation_middleware.simulation_service') as mock_sim:

            mock_instance = Mock()
            mock_instance.get_user.return_value = None  # User not in DB
            mock_instance.close = Mock()
            mock_service.return_value = mock_instance

            # Setup simulation service
            mock_sim.resolve_context.return_value = UserContext(
                user_id=123,
                real_role="user"
            )

            await middleware(handler, mock_event, data)
