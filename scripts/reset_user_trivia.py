"""
Reset de Trivia para Usuario Específico

Elimina el progreso de trivia del día actual, besitos ganados y códigos de descuento
de promoción por racha para un usuario.

Uso:
    python scripts/reset_user_trivia.py <user_id>

Ejemplo:
    python scripts/reset_user_trivia.py 6181290784
"""
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.database import SessionLocal
from models.models import GameRecord, BesitoTransaction, TransactionSource, DiscountCode, DiscountCodeStatus


def reset_user_trivia(user_id: int) -> dict:
    """Reset trivia progress, besitos, and discount codes for a user today."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    with SessionLocal() as session:
        # 1. Eliminar registros de trivia de hoy
        trivia_deleted = session.query(GameRecord).filter(
            GameRecord.user_id == user_id,
            GameRecord.game_type.in_(['trivia', 'trivia_vip']),
            GameRecord.played_at >= today
        ).delete(synchronize_session=False)

        # 2. Eliminar besitos ganados en trivia hoy
        besitos_deleted = session.query(BesitoTransaction).filter(
            BesitoTransaction.user_id == user_id,
            BesitoTransaction.source == TransactionSource.TRIVIA,
            BesitoTransaction.created_at >= today
        ).delete(synchronize_session=False)

        # 3. Cancelar códigos de descuento de trivia activos del usuario
        codes_updated = session.query(DiscountCode).filter(
            DiscountCode.user_id == user_id,
            DiscountCode.status == DiscountCodeStatus.ACTIVE,
            DiscountCode.code.like('TRI-%')
        ).update({'status': DiscountCodeStatus.CANCELLED}, synchronize_session=False)

        session.commit()

        return {
            'user_id': user_id,
            'trivia_records_deleted': trivia_deleted,
            'besito_transactions_deleted': besitos_deleted,
            'discount_codes_cancelled': codes_updated
        }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/reset_user_trivia.py <user_id>")
        sys.exit(1)

    user_id = int(sys.argv[1])
    result = reset_user_trivia(user_id)

    print(f"Reset completo para usuario {user_id}:")
    print(f"  - Registros de trivia eliminados: {result['trivia_records_deleted']}")
    print(f"  - Transacciones de besitos de trivia eliminadas: {result['besito_transactions_deleted']}")
    print(f"  - Códigos de descuento de trivia cancelados: {result['discount_codes_cancelled']}")