"""FSM states for store fulfillment user input capture."""

from aiogram.fsm.state import State, StatesGroup


class PurchaseInputStates(StatesGroup):
    """Captura de input del visitante post-compra."""

    awaiting_input = State()
    validating = State()


class BackpackInputStates(StatesGroup):
    """Captura de input pendiente desde mochila."""

    awaiting_input = State()
    validating = State()