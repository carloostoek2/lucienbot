"""Topes en código para valores de economía editables por admin (informe #4).

Una sola fuente de verdad para los rangos permitidos:

- **Escritura** (servicio, nunca solo el handler): ``validate`` lanza
  ``EconomyLimitError`` con el rango, y el admin ve el mensaje. No se recorta en
  silencio.
- **Lectura** (uso real): ``clamp`` recorta los valores que lleguen fuera de rango
  por scripts o SQL manual. Quien acredita usa el valor recortado tanto en el
  crédito como en el mensaje.

Los topes dejan ~3x de holgura sobre los valores de prod al 2026-10-29: regalo 10;
dados 5/10; trivia 5/8, simple 5/8, trivia VIP 5; caps de besitos de trivia 10/15
diario y 50/70 semanal; reacciones 2 (🥵=5); recompensas de misión planeadas 5
(diaria) y 30 (semanal); racha 15/30.
``MAX_ADMIN_BESITO_GRANT`` (10 000, ``services/besito_service.py``) no cambia.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limit:
    label: str
    min: int
    max: int


LIMITS: dict[str, Limit] = {
    # Regalo diario (DailyGiftConfig.besito_amount)
    "daily_gift_amount": Limit("Regalo diario", 1, 30),
    # Dados: jugadas por día (TriviaConfig)
    "dice_limit_free": Limit("Dados (Free)", 0, 30),
    "dice_limit_vip": Limit("Dados (VIP)", 0, 30),
    # Trivia: jugadas por día
    "trivia_limit_free": Limit("Trivia (Free)", 0, 25),
    "trivia_limit_vip": Limit("Trivia (VIP)", 0, 25),
    "trivia_vip_limit": Limit("Trivia VIP", 0, 25),
    "trivia_simple_limit_free": Limit("Trivia simple (Free)", 0, 25),
    "trivia_simple_limit_vip": Limit("Trivia simple (VIP)", 0, 25),
    # Trivia: tope de besitos ganados
    "trivia_besitos_daily_free": Limit("Besitos trivia/día (Free)", 0, 50),
    "trivia_besitos_daily_vip": Limit("Besitos trivia/día (VIP)", 0, 50),
    "trivia_besitos_weekly_free": Limit("Besitos trivia/semana (Free)", 0, 250),
    "trivia_besitos_weekly_vip": Limit("Besitos trivia/semana (VIP)", 0, 250),
    # Racha de trivia en modo riesgo (pago en besitos)
    "streak_retire_besitos": Limit("Racha: pago al retirarse", 1, 50),
    "streak_complete_besitos": Limit("Racha: pago al completar", 1, 100),
    # Reacciones (ReactionEmoji.besito_value)
    "reaction_besito_value": Limit("Valor de reacción", 1, 15),
    # Recompensas de misión (Reward.besito_amount)
    "mission_reward_besitos": Limit("Recompensa de misión", 1, 100),
}


class EconomyLimitError(ValueError):
    """Valor fuera del rango permitido. ``str(exc)`` trae el rango para el admin."""

    def __init__(self, field: str, value):
        self.field = field
        self.value = value
        self.limit = LIMITS[field]
        super().__init__(
            f"{self.limit.label}: {value} fuera de rango "
            f"(permitido {self.limit.min}–{self.limit.max})"
        )


def validate(field: str, value) -> int:
    """Retorna ``value`` si es int dentro del rango; si no, lanza EconomyLimitError."""
    limit = LIMITS[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise EconomyLimitError(field, value)
    if value < limit.min or value > limit.max:
        raise EconomyLimitError(field, value)
    return value


def clamp(field: str, value: int | None) -> int:
    """Recorta en lectura un valor ya persistido (``None`` → mínimo)."""
    limit = LIMITS[field]
    if value is None:
        return limit.min
    return max(limit.min, min(limit.max, int(value)))


def range_text(field: str) -> str:
    """Texto corto del rango para mensajes de admin: ``1–30``."""
    limit = LIMITS[field]
    return f"{limit.min}–{limit.max}"
