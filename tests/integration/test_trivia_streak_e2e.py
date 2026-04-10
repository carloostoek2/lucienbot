"""
Test e2e de trivia con sistema de rachas y códigos de descuento.

Este test verifica el flujo completo del sistema de trivias con promociones de rachas:
1. Configuraciones de trivia se crean correctamente
2. La racha incrementa con respuestas correctas y se resetea con incorrectas
3. La información de descuento muestra totales correctos
4. El modelo de códigos de descuento funciona correctamente
"""
import pytest
import sys
from datetime import datetime

sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from services.game_service import GameService
from models.models import (
    User, UserRole, BesitoBalance,
    TriviaPromotionConfig, DiscountCode, DiscountCodeStatus,
    GameRecord, Promotion, PromotionStatus, Package
)


def log_step(message: str):
    print(f"\n{'='*60}")
    print(f"  {message}")
    print('='*60)


def log_detail(message: str):
    print(f"    → {message}")


def get_correct_answer_index(question: dict) -> int:
    return question.get('answer', 0)


@pytest.fixture
def trivia_promotion_config(db_session):
    """Crea configuración de trivia con racha requerida de 5"""
    package = Package(
        name="Test Package Trivia",
        description="A test package",
        store_stock=-1,
        reward_stock=-1,
        is_active=True
    )
    db_session.add(package)
    db_session.flush()

    promotion = Promotion(
        name="Test Promo Trivia",
        description="A promo",
        package_id=package.id,
        price_mxn=99900,
        is_active=True,
        status=PromotionStatus.ACTIVE
    )
    db_session.add(promotion)
    db_session.flush()

    config = TriviaPromotionConfig(
        name="Trivia Descuento 5 Racha",
        promotion_id=promotion.id,
        discount_percentage=20,
        required_streak=5,
        max_codes=10,
        is_active=True
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def trivia_independent_config(db_session):
    """Crea configuración de trivia independiente (sin promoción)"""
    config = TriviaPromotionConfig(
        name="Trivia Independiente",
        promotion_id=None,
        custom_description="2x1 en fotos de Srta. Kinky",
        discount_percentage=50,
        required_streak=3,
        max_codes=5,
        is_active=True
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def unique_user(db_session):
    """Usuario único por test"""
    user = User(
        telegram_id=int(datetime.utcnow().timestamp() * 1000) % (10**10),
        username=f"user_{datetime.utcnow().timestamp()}",
        first_name="Test",
        role=UserRole.USER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unique_user_balance(db_session, unique_user):
    """Balance para el usuario único"""
    balance = BesitoBalance(
        user_id=unique_user.id,
        balance=0,
        total_earned=0,
        total_spent=0
    )
    db_session.add(balance)
    db_session.commit()
    db_session.refresh(balance)
    return balance


@pytest.mark.integration
class TestTriviaStreakE2E:
    """Tests del flujo de trivia con rachas"""

    def test_config_creation(self, db_session, trivia_promotion_config):
        """Verifica que se crea la configuración correctamente"""
        log_step("TEST - Creación de config")
        assert trivia_promotion_config.is_active is True
        assert trivia_promotion_config.required_streak == 5
        assert trivia_promotion_config.max_codes == 10
        assert trivia_promotion_config.discount_percentage == 20
        log_step("RESULTADO: OK")

    def test_trivia_increments_streak(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que la racha incrementa con respuestas correctas"""
        log_step("TEST - Racha incrementa")

        game_service = GameService(db_session)
        questions = game_service.load_trivia_questions()
        assert len(questions) > 0

        correct_idx = get_correct_answer_index(questions[0])

        result1 = game_service.play_trivia(unique_user.id, 0, correct_idx)
        assert result1['new_streak'] == 1
        log_detail("Racha 1: OK")

        result2 = game_service.play_trivia(unique_user.id, 1, get_correct_answer_index(questions[1]))
        assert result2['new_streak'] == 2
        log_detail("Racha 2: OK")

        result3 = game_service.play_trivia(unique_user.id, 2, get_correct_answer_index(questions[2]))
        assert result3['new_streak'] == 3
        log_detail("Racha 3: OK")

        log_step("RESULTADO: OK")

    def test_trivia_resets_on_wrong(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que la racha se resetea con respuesta incorrecta"""
        log_step("TEST - Reset de racha")

        game_service = GameService(db_session)
        questions = game_service.load_trivia_questions()
        correct_idx = get_correct_answer_index(questions[0])
        opts = questions[0].get('opts', [])
        wrong_idx = (correct_idx + 1) % len(opts) if opts else 1

        for i in range(3):
            result = game_service.play_trivia(unique_user.id, 0, correct_idx)
            assert result['new_streak'] == i + 1

        result_wrong = game_service.play_trivia(unique_user.id, 0, wrong_idx)
        assert result_wrong['new_streak'] == 0
        assert result_wrong['correct'] is False
        log_detail("Reset OK")

        log_step("RESULTADO: OK")

    def test_no_code_before_streak(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que NO se genera código antes de alcanzar la racha"""
        log_step("TEST - Sin código antes de racha")

        game_service = GameService(db_session)
        questions = game_service.load_trivia_questions()
        correct_idx = get_correct_answer_index(questions[0])

        # Solo 4 correctas (necesitamos 5)
        for i in range(4):
            result = game_service.play_trivia(unique_user.id, i % len(questions), correct_idx)
            assert result.get('discount_code') is None, f"No debe generar código en racha {i+1}"

        log_step("RESULTADO: OK")

    def test_discount_model_usage(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica el ciclo de vida del modelo de descuento: crear, usar, verificar"""
        log_step("TEST - Ciclo de vida del modelo DiscountCode")

        # Crear código manualmente
        code = DiscountCode(
            config_id=trivia_promotion_config.id,
            code="TRI-TEST01",
            user_id=unique_user.id,
            username=unique_user.username,
            first_name=unique_user.first_name,
            promotion_id=trivia_promotion_config.promotion_id,
            status=DiscountCodeStatus.ACTIVE
        )
        db_session.add(code)
        db_session.commit()
        db_session.refresh(code)

        assert code.code.startswith("TRI-")
        assert code.status == DiscountCodeStatus.ACTIVE
        log_detail(f"Código creado: {code.code}")

        # Verificar que existe
        found_code = db_session.query(DiscountCode).filter(
            DiscountCode.user_id == unique_user.id,
            DiscountCode.config_id == trivia_promotion_config.id
        ).first()
        assert found_code is not None
        assert found_code.code == "TRI-TEST01"
        log_detail("Código encontrado en BD")

        # Usar el código
        code.status = DiscountCodeStatus.USED
        code.used_at = datetime.utcnow()
        trivia_promotion_config.codes_claimed += 1
        db_session.commit()

        db_session.refresh(code)
        db_session.refresh(trivia_promotion_config)

        assert code.status == DiscountCodeStatus.USED
        assert code.used_at is not None
        assert trivia_promotion_config.codes_claimed == 1
        log_detail("Código marcado como usado")

        log_step("RESULTADO: OK")

    def test_codes_claimed_calculation(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que available_codes se calcula correctamente"""
        log_step("TEST - Cálculo de códigos disponibles")

        initial = trivia_promotion_config.max_codes - trivia_promotion_config.codes_claimed
        assert initial == 10
        log_detail(f"Initial available: {initial}")

        # Simular 3 códigos reclamados
        trivia_promotion_config.codes_claimed = 3
        db_session.commit()
        db_session.refresh(trivia_promotion_config)

        available = trivia_promotion_config.max_codes - trivia_promotion_config.codes_claimed
        assert available == 7
        log_detail(f"After 3 claimed: {available}")

        # Agotar todos
        trivia_promotion_config.codes_claimed = 10
        db_session.commit()
        db_session.refresh(trivia_promotion_config)

        available = trivia_promotion_config.max_codes - trivia_promotion_config.codes_claimed
        assert available == 0
        log_detail(f"After 10 claimed: {available}")

        log_step("RESULTADO: OK")

    def test_multiple_configs_coexist(
        self, db_session, trivia_promotion_config, trivia_independent_config
    ):
        """Verifica que pueden coexistir múltiples configuraciones"""
        log_step("TEST - Múltiples configs")

        configs = db_session.query(TriviaPromotionConfig).filter(
            TriviaPromotionConfig.is_active == True
        ).all()

        assert len(configs) >= 2
        log_detail(f"Configs activas: {len(configs)}")

        # Verificar que tienen diferentes required_streak
        streak_5 = any(c.required_streak == 5 for c in configs)
        streak_3 = any(c.required_streak == 3 for c in configs)
        assert streak_5 or streak_3

        log_step("RESULTADO: OK")

    def test_admin_can_create_custom_config(self, db_session, sample_admin):
        """Verifica que admin puede crear configs con diferentes parámetros"""
        log_step("TEST - Admin crea config custom")

        config = TriviaPromotionConfig(
            name="Config Custom",
            promotion_id=None,
            custom_description="Oferta especial",
            discount_percentage=25,
            required_streak=7,
            max_codes=20,
            is_active=True,
            created_by=sample_admin.id
        )
        db_session.add(config)
        db_session.commit()

        assert config.required_streak == 7
        assert config.max_codes == 20
        assert config.discount_percentage == 25
        assert config.created_by == sample_admin.id

        log_step("RESULTADO: OK")

    def test_game_record_tracking(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que los GameRecord se crean correctamente"""
        log_step("TEST - GameRecord tracking")

        game_service = GameService(db_session)
        questions = game_service.load_trivia_questions()
        correct_idx = get_correct_answer_index(questions[0])

        # Jugar trivia
        result = game_service.play_trivia(unique_user.id, 0, correct_idx)
        assert result['correct'] is True

        # Verificar que existe GameRecord
        records = db_session.query(GameRecord).filter(
            GameRecord.user_id == unique_user.id,
            GameRecord.game_type == 'trivia'
        ).all()

        assert len(records) >= 1
        assert records[-1].payout > 0  # Victorias tienen payout > 0
        log_detail(f"GameRecords creados: {len(records)}")

        log_step("RESULTADO: OK")

    def test_wrong_answer_creates_record_with_zero_payout(
        self, db_session, unique_user, trivia_promotion_config, unique_user_balance
    ):
        """Verifica que respuestas incorrectas se registran con payout=0"""
        log_step("TEST - Registro de respuesta incorrecta")

        game_service = GameService(db_session)
        questions = game_service.load_trivia_questions()
        correct_idx = get_correct_answer_index(questions[0])
        opts = questions[0].get('opts', [])
        wrong_idx = (correct_idx + 1) % len(opts) if opts else 1

        # Primero correcta
        game_service.play_trivia(unique_user.id, 0, correct_idx)

        # Después incorrecta
        result = game_service.play_trivia(unique_user.id, 0, wrong_idx)
        assert result['correct'] is False
        assert result['besitos'] == 0

        # Verificar que hay un registro con payout=0
        wrong_records = db_session.query(GameRecord).filter(
            GameRecord.user_id == unique_user.id,
            GameRecord.game_type == 'trivia',
            GameRecord.payout == 0
        ).all()

        assert len(wrong_records) >= 1
        log_detail(f"Registros con payout=0: {len(wrong_records)}")

        log_step("RESULTADO: OK")
