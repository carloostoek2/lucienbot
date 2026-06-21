"""FSM states for package management wizards."""

from aiogram.fsm.state import State, StatesGroup


class PackageWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_files = State()
    waiting_store_stock = State()
    waiting_reward_stock = State()
    confirming = State()


class SendPackageStates(StatesGroup):
    selecting_package = State()
    waiting_user_id = State()
    confirming = State()


class UpdatePackageStates(StatesGroup):
    selecting_package = State()
    waiting_files = State()
    confirming = State()


class DeleteFileStates(StatesGroup):
    selecting_package = State()
    deleting_files = State()
