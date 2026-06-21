"""Integration tests for store/fulfillment callback data packing."""

import pytest

from keyboards.callback_data import (
    BackpackFulfillmentRetryCallback,
    BackpackReadChapterCallback,
    BackpackViewWaitlistCallback,
    FulfillmentAdminDeliverCallback,
    FulfillmentAdminItemCallback,
    FulfillmentAdminMarkCallback,
    FulfillmentAdminQueueCallback,
    StoreTierCallback,
)


@pytest.mark.integration
class TestStoreFulfillmentCallbackData:
    def test_tier_callback_roundtrip(self):
        raw = StoreTierCallback(tier_id=3).pack()
        parsed = StoreTierCallback.unpack(raw)
        assert parsed.tier_id == 3

    def test_fulfillment_admin_queue_roundtrip(self):
        raw = FulfillmentAdminQueueCallback(status="pending_input").pack()
        parsed = FulfillmentAdminQueueCallback.unpack(raw)
        assert parsed.status == "pending_input"

    def test_fulfillment_admin_item_roundtrip(self):
        raw = FulfillmentAdminItemCallback(fulfillment_id=42, filter_status="fulfilled").pack()
        parsed = FulfillmentAdminItemCallback.unpack(raw)
        assert parsed.fulfillment_id == 42
        assert parsed.filter_status == "fulfilled"

    def test_fulfillment_admin_mark_roundtrip(self):
        raw = FulfillmentAdminMarkCallback(fulfillment_id=7).pack()
        assert FulfillmentAdminMarkCallback.unpack(raw).fulfillment_id == 7

    def test_fulfillment_admin_deliver_roundtrip(self):
        raw = FulfillmentAdminDeliverCallback(fulfillment_id=1, package_id=9).pack()
        parsed = FulfillmentAdminDeliverCallback.unpack(raw)
        assert parsed.fulfillment_id == 1
        assert parsed.package_id == 9

    def test_backpack_fulfillment_retry_roundtrip(self):
        raw = BackpackFulfillmentRetryCallback(fulfillment_id=5).pack()
        assert BackpackFulfillmentRetryCallback.unpack(raw).fulfillment_id == 5

    def test_backpack_read_chapter_roundtrip(self):
        raw = BackpackReadChapterCallback(fulfillment_id=11).pack()
        assert BackpackReadChapterCallback.unpack(raw).fulfillment_id == 11

    def test_backpack_view_waitlist_roundtrip(self):
        raw = BackpackViewWaitlistCallback(fulfillment_id=13).pack()
        assert BackpackViewWaitlistCallback.unpack(raw).fulfillment_id == 13

    def test_backpack_submit_input_roundtrip(self):
        from keyboards.callback_data import BackpackSubmitInputCallback

        raw = BackpackSubmitInputCallback(fulfillment_id=21).pack()
        assert BackpackSubmitInputCallback.unpack(raw).fulfillment_id == 21