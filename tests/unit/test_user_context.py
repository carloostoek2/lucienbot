"""Tests for UserContext dataclass."""
import pytest
from datetime import datetime, timedelta
from services.user_context import UserContext, SimulationRole


class TestUserContext:
    """Test UserContext properties and methods."""

    def test_real_role_preserved(self):
        """Real role should be accessible even during simulation."""
        ctx = UserContext(user_id=123, real_role="admin")
        assert ctx.real_role == "admin"

        vip_ctx = ctx.with_simulation(SimulationRole.VIP)
        assert vip_ctx.real_role == "admin"

    def test_effective_role_no_simulation(self):
        """Without simulation, effective_role equals real_role."""
        ctx = UserContext(user_id=123, real_role="vip")
        assert ctx.effective_role == "vip"

        ctx = UserContext(user_id=123, real_role="user")
        assert ctx.effective_role == "user"

    def test_effective_role_with_vip_simulation(self):
        """VIP simulation changes effective_role to vip."""
        ctx = UserContext(user_id=123, real_role="user")
        vip_ctx = ctx.with_simulation(SimulationRole.VIP)

        assert vip_ctx.effective_role == "vip"
        assert vip_ctx.is_vip is True

    def test_effective_role_with_free_simulation(self):
        """FREE simulation changes effective_role to user."""
        ctx = UserContext(user_id=123, real_role="admin")
        free_ctx = ctx.with_simulation(SimulationRole.FREE)

        assert free_ctx.effective_role == "user"
        assert free_ctx.is_vip is False

    def test_admin_role_unchanged_in_simulation(self):
        """Admin real_role is preserved even when simulating free."""
        ctx = UserContext(user_id=123, real_role="admin")
        free_ctx = ctx.with_simulation(SimulationRole.FREE)

        assert free_ctx.is_admin is True
        assert free_ctx.real_role == "admin"

    def test_is_vip_property(self):
        """is_vip should be True for vip role or vip simulation."""
        # Real VIP
        vip_ctx = UserContext(user_id=123, real_role="vip")
        assert vip_ctx.is_vip is True

        # User simulating VIP
        user_ctx = UserContext(user_id=123, real_role="user")
        sim_vip = user_ctx.with_simulation(SimulationRole.VIP)
        assert sim_vip.is_vip is True

        # Regular user
        regular = UserContext(user_id=123, real_role="user")
        assert regular.is_vip is False

    def test_can_modify_state(self):
        """can_modify_state is False during simulation."""
        ctx = UserContext(user_id=123, real_role="admin")
        assert ctx.can_modify_state is True

        sim_ctx = ctx.with_simulation(SimulationRole.VIP)
        assert sim_ctx.can_modify_state is False

    def test_with_simulation_sets_expiration(self):
        """with_simulation sets expiration time."""
        ctx = UserContext(user_id=123, real_role="admin")
        sim_ctx = ctx.with_simulation(SimulationRole.VIP, duration_minutes=30)

        assert sim_ctx.is_simulation_active is True
        assert sim_ctx.simulated_role == SimulationRole.VIP
        assert sim_ctx.simulation_expires_at is not None

        # Check expiration is roughly 30 minutes from now
        expected = datetime.utcnow() + timedelta(minutes=30)
        diff = abs((sim_ctx.simulation_expires_at - expected).total_seconds())
        assert diff < 5  # Within 5 seconds

    def test_without_simulation_clears_state(self):
        """without_simulation returns context with simulation cleared."""
        ctx = UserContext(user_id=123, real_role="admin")
        sim_ctx = ctx.with_simulation(SimulationRole.VIP)
        reset_ctx = sim_ctx.without_simulation()

        assert reset_ctx.is_simulation_active is False
        assert reset_ctx.simulated_role is None
        assert reset_ctx.simulation_expires_at is None
        assert reset_ctx.is_vip is False  # Back to admin real_role


class TestSimulationRole:
    """Test SimulationRole enum."""

    def test_role_values(self):
        """SimulationRole has correct values."""
        assert SimulationRole.VIP.value == "vip"
        assert SimulationRole.FREE.value == "free"
        assert SimulationRole.REAL.value is None
