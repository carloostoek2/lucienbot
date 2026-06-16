"""Helpers para resolver la instancia del bot en runtime sin handler."""


def resolve_delivery_bot(bot=None):
    """Usa el bot del handler si existe; si no, el bot lazy del scheduler."""
    if bot is not None:
        return bot
    try:
        from services.scheduler_service import _get_bot

        return _get_bot()
    except RuntimeError:
        return None