"""
Tests unitarios para IdempotencyCache.
"""
import pytest
import time
from middlewares.idempotency import IdempotencyCache


@pytest.mark.unit
class TestIdempotencyCache:
    """Tests para el cache de idempotencia de callbacks."""

    def test_first_callback_is_not_duplicate(self):
        """Test que un callback nuevo no se marca como duplicado."""
        cache = IdempotencyCache(ttl_seconds=60)
        callback_id = "callback_123"

        assert cache.is_duplicate(callback_id) is False

    def test_same_callback_within_ttl_is_duplicate(self):
        """Test que el mismo callback dentro del TTL se marca duplicado."""
        cache = IdempotencyCache(ttl_seconds=60)
        callback_id = "callback_456"

        assert cache.is_duplicate(callback_id) is False
        assert cache.is_duplicate(callback_id) is True

    def test_different_callbacks_are_independent(self):
        """Test que callbacks diferentes no se marcan como duplicados."""
        cache = IdempotencyCache(ttl_seconds=60)

        assert cache.is_duplicate("cb_A") is False
        assert cache.is_duplicate("cb_B") is False
        assert cache.is_duplicate("cb_A") is True
        assert cache.is_duplicate("cb_B") is True

    def test_callback_expires_after_ttl(self):
        """Test que un callback expira después del TTL."""
        cache = IdempotencyCache(ttl_seconds=1)

        assert cache.is_duplicate("cb_expire") is False
        time.sleep(1.1)
        assert cache.is_duplicate("cb_expire") is False

    def test_old_entries_cleaned_up_on_check(self):
        """Test que entradas expiradas se limpian al verificar."""
        cache = IdempotencyCache(ttl_seconds=1)

        cache.is_duplicate("cb_old_1")
        cache.is_duplicate("cb_old_2")
        time.sleep(1.1)

        assert cache.is_duplicate("cb_old_1") is False
        assert cache._seen, "Cache should be empty after expired entries cleaned"

    def test_mark_processed_adds_to_seen(self):
        """Test que mark_processed agrega el callback al cache."""
        cache = IdempotencyCache(ttl_seconds=60)
        callback_id = "cb_marked"

        cache.mark_processed(callback_id)
        assert cache.is_duplicate(callback_id) is True

    def test_empty_callback_id_handled(self):
        """Test que callbacks con ID vacío no crashean."""
        cache = IdempotencyCache(ttl_seconds=60)

        assert cache.is_duplicate("") is False
        assert cache.is_duplicate("") is True
