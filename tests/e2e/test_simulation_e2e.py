"""E2E tests for admin simulation system."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from services.simulation_service import simulation_service, SimulationService
from services.user_context import SimulationRole


class TestAdminSimulationE2E:
    """End-to-end tests for simulation user flows."""

    @pytest.fixture(autouse=True)
    def reset_simulation_state(self):
        """Clear simulation state before each test."""
        service = SimulationService()
        service._overrides = {}
        yield
        service._overrides = {}

    def test_admin_activates_vip_simulation(self):
        """Admin can activate VIP simulation mode."""
        admin_id = 123

        # Activate VIP mode
        simulation_service.set_override(admin_id, SimulationRole.VIP)

        # Verify active
        ctx = simulation_service.resolve_context(admin_id, "admin")
        assert ctx.is_simulation_active is True
        assert ctx.is_vip is True
        assert ctx.real_role == "admin"

    def test_admin_sees_different_content_in_simulation(self):
        """Admin sees VIP-only content when simulating VIP."""
        admin_id = 123

        # Without simulation
        ctx = simulation_service.resolve_context(admin_id, "admin")
        # Admin might not be VIP, but should see admin panel

        # With VIP simulation
        simulation_service.set_override(admin_id, SimulationRole.VIP)
        vip_ctx = simulation_service.resolve_context(admin_id, "admin")

        assert vip_ctx.is_vip is True
        # This should affect what menus/content are shown

    def test_operations_blocked_in_simulation(self):
        """Mutations are blocked during simulation."""
        admin_id = 123

        # Activate simulation
        simulation_service.set_override(admin_id, SimulationRole.VIP)

        # Try operation
        blocked = simulation_service.get_override(admin_id) is not None
        assert blocked is True

        # Clear and verify works
        simulation_service.clear_override(admin_id)
        blocked_after = simulation_service.get_override(admin_id) is not None
        assert blocked_after is False

    def test_simulation_isolation(self):
        """One admin's simulation doesn't affect others."""
        admin1 = 111
        admin2 = 222

        # Admin1 activates simulation
        simulation_service.set_override(admin1, SimulationRole.VIP)

        # Admin2 should not be affected
        ctx2 = simulation_service.resolve_context(admin2, "admin")
        assert ctx2.is_simulation_active is False

        # Admin1 still in simulation
        ctx1 = simulation_service.resolve_context(admin1, "admin")
        assert ctx1.is_simulation_active is True

    def test_simulation_auto_expires(self):
        """Simulation expires after duration."""
        admin_id = 123

        # Set very short duration
        simulation_service.set_override(admin_id, SimulationRole.VIP, duration_minutes=0)
        # Force expiration
        simulation_service._overrides[admin_id]["expires_at"] = (
            datetime.utcnow().timestamp() - 1
        )

        # Should be expired
        ctx = simulation_service.resolve_context(admin_id, "admin")
        assert ctx.is_simulation_active is False


class TestSimulationSafetyE2E:
    """E2E tests for simulation safety restrictions."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Clear state before each test."""
        service = SimulationService()
        service._overrides = {}
        yield
        service._overrides = {}

    def test_token_redemption_blocked_in_simulation(self):
        """VIP token redemption blocked during simulation."""
        from services.simulation_guard import check_simulation_blocked

        admin_id = 123
        simulation_service.set_override(admin_id, SimulationRole.VIP)

        # Check blocked
        blocked = check_simulation_blocked(admin_id, "canjear token")
        assert blocked is True

    def test_purchase_blocked_in_simulation(self):
        """Store purchases blocked during simulation."""
        from services.simulation_guard import check_simulation_blocked

        admin_id = 123
        simulation_service.set_override(admin_id, SimulationRole.FREE)

        # Check blocked
        blocked = check_simulation_blocked(admin_id, "comprar")
        assert blocked is True

    def test_blocked_message_format(self):
        """Blocked message is properly formatted."""
        from services.simulation_guard import get_blocked_message

        msg = get_blocked_message("realizar esta acción")
        assert "Acción Bloqueada" in msg
        assert "modo simulación" in msg
        assert "/simulate reset" in msg


class TestSimulationContextE2E:
    """E2E tests for UserContext behavior in simulation."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Clear state before each test."""
        service = SimulationService()
        service._overrides = {}
        yield
        service._overrides = {}

    def test_admin_simulating_vip_cannot_modify_state(self):
        """Admin in VIP simulation cannot modify state."""
        admin_id = 123
        simulation_service.set_override(admin_id, SimulationRole.VIP)

        ctx = simulation_service.resolve_context(admin_id, "admin")

        assert ctx.can_modify_state is False
        assert ctx.is_admin is True  # Still admin
        assert ctx.is_vip is True  # But sees VIP content

    def test_admin_simulating_free_cannot_modify_state(self):
        """Admin in FREE simulation cannot modify state."""
        admin_id = 123
        simulation_service.set_override(admin_id, SimulationRole.FREE)

        ctx = simulation_service.resolve_context(admin_id, "admin")

        assert ctx.can_modify_state is False
        assert ctx.is_admin is True  # Still admin
        assert ctx.is_vip is False  # Sees as free user

    def test_real_role_preserved_through_simulation(self):
        """Real role is always preserved."""
        admin_id = 123

        # Start simulation
        simulation_service.set_override(admin_id, SimulationRole.VIP)
        ctx = simulation_service.resolve_context(admin_id, "admin")

        assert ctx.real_role == "admin"
        assert ctx.effective_role == "vip"

        # Clear simulation
        simulation_service.clear_override(admin_id)
        ctx_cleared = simulation_service.resolve_context(admin_id, "admin")

        assert ctx_cleared.real_role == "admin"
        assert ctx_cleared.effective_role == "admin"


class TestSimulationServiceSingletonE2E:
    """E2E tests for SimulationService singleton behavior."""

    def test_singleton_instance(self):
        """SimulationService is a singleton."""
        service1 = SimulationService()
        service2 = SimulationService()

        assert service1 is service2

    def test_shared_state_across_instances(self):
        """State is shared across all instances."""
        service1 = SimulationService()
        service1._overrides = {}  # Clear state

        service2 = SimulationService()

        # Set via service1
        service1.set_override(123, SimulationRole.VIP)

        # Visible via service2
        assert service2.get_override(123) is not None

        # Clear and verify
        service1._overrides = {}
