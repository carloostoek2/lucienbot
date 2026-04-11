"""Tests for SimulationService."""
import pytest
import time
from datetime import datetime
from services.simulation_service import SimulationService
from services.user_context import SimulationRole


class TestSimulationService:
    """Test SimulationService functionality."""

    @pytest.fixture
    def service(self):
        """Fresh service instance for each test."""
        s = SimulationService()
        s._overrides = {}  # Clear any existing state
        return s

    def test_set_override_creates_entry(self, service):
        """set_override creates an override entry."""
        service.set_override(123, SimulationRole.VIP)

        override = service.get_override(123)
        assert override is not None
        assert override["role"] == SimulationRole.VIP

    def test_set_override_with_duration(self, service):
        """set_override respects duration parameter."""
        service.set_override(123, SimulationRole.VIP, duration_minutes=10)

        override = service.get_override(123)
        # Check expiration is roughly 10 minutes from now
        expected_expires = datetime.utcnow().timestamp() + (10 * 60)
        diff = abs(override["expires_at"] - expected_expires)
        assert diff < 5  # Within 5 seconds

    def test_get_override_returns_none_if_not_set(self, service):
        """get_override returns None if no override exists."""
        result = service.get_override(999)
        assert result is None

    def test_get_override_returns_none_after_clear(self, service):
        """get_override returns None after clear_override."""
        service.set_override(123, SimulationRole.VIP)
        service.clear_override(123)

        result = service.get_override(123)
        assert result is None

    def test_get_override_auto_expires(self, service):
        """get_override returns None and clears if expired."""
        # Set override with very short duration
        service.set_override(123, SimulationRole.VIP, duration_minutes=0)
        # Manually set expiration to past
        service._overrides[123]["expires_at"] = datetime.utcnow().timestamp() - 1

        result = service.get_override(123)
        assert result is None
        assert 123 not in service._overrides  # Should be cleared

    def test_resolve_context_without_override(self, service):
        """resolve_context returns base context without override."""
        ctx = service.resolve_context(123, "user")

        assert ctx.user_id == 123
        assert ctx.real_role == "user"
        assert ctx.is_simulation_active is False
        assert ctx.simulated_role is None

    def test_resolve_context_with_active_override(self, service):
        """resolve_context returns simulated context with override."""
        service.set_override(123, SimulationRole.VIP)

        ctx = service.resolve_context(123, "admin")

        assert ctx.user_id == 123
        assert ctx.real_role == "admin"
        assert ctx.is_simulation_active is True
        assert ctx.simulated_role == SimulationRole.VIP
        assert ctx.is_vip is True

    def test_resolve_context_non_admin_with_override(self, service):
        """Override only applies to admin users (based on real_role)."""
        service.set_override(123, SimulationRole.VIP)

        # User tries to use override (should not work - only admins can simulate)
        ctx = service.resolve_context(123, "user")

        # Override exists but doesn't apply to non-admins
        assert ctx.is_simulation_active is False
        assert ctx.real_role == "user"
        assert ctx.effective_role == "user"

    def test_get_simulation_status_active(self, service):
        """get_simulation_status returns string for active override."""
        service.set_override(123, SimulationRole.VIP)

        status = service.get_simulation_status(123)
        assert status is not None
        assert "VIP" in status
        assert "min" in status

    def test_get_simulation_status_inactive(self, service):
        """get_simulation_status returns None if no override."""
        status = service.get_simulation_status(123)
        assert status is None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, service):
        """cleanup_expired removes expired overrides."""
        # Set up expired override
        service.set_override(123, SimulationRole.VIP, duration_minutes=0)
        service._overrides[123]["expires_at"] = datetime.utcnow().timestamp() - 1

        # Set up active override
        service.set_override(456, SimulationRole.FREE, duration_minutes=30)

        await service.cleanup_expired()

        assert 123 not in service._overrides
        assert 456 in service._overrides
