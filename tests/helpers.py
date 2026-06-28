"""Testing helpers for Lucien Bot tests.

model_mock: create an autospec mock for a SQLAlchemy model with preset attributes.
  Validates attribute names against the model definition at test time.
"""

from unittest.mock import create_autospec


def model_mock(model_class, **attrs):
    """Crea un autospec mock para un modelo SQLAlchemy con atributos predefinidos.

    Valida que los nombres de atributos existan en el modelo al momento del test.
    Evita typos silenciosos en nombres de columnas/relaciones.

    Uso::
        mission = model_mock(Mission, id=1, name="Test", target_value=10)
        reward = model_mock(Reward, id=1, reward_type=RewardType.BESITOS)
    """
    mock = create_autospec(model_class, spec_set=True, instance=True)
    for key, val in attrs.items():
        setattr(mock, key, val)
    return mock
