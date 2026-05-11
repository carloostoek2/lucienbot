#!/usr/bin/env python3
"""
Script para resetear el estado de trivia de un usuario.

Uso:
    python scripts/reset_trivia_user.py <user_id>
    python scripts/reset_trivia_user.py <user_id> --game-type trivia_simple
    python scripts/reset_trivia_user.py <user_id> --list-only
    python scripts/reset_trivia_user.py <user_id> --all-time   # Resetear TODO el historial
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

# Asegurar acceso a models
_script_dir = Path(__file__).parent
if _script_dir.name == 'scripts':
    _project_root = _script_dir.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from sqlalchemy import and_

from models.database import SessionLocal
from models.models import GameRecord, StreakPromotionRedemption


def reset_user_trivia(user_id: int, game_type: str = None, list_only: bool = False, all_time: bool = False) -> dict:
    """
    Resetea el estado de trivia de un usuario.

    Args:
        user_id: ID del usuario
        game_type: Filtrar por tipo ('trivia', 'trivia_simple', 'trivia_vip'). None = todos.
        list_only: Si True, solo muestra lo que se eliminaría sin borrar.
        all_time: Si True, elimina TODO el historial. Si False, solo de hoy.

    Returns:
        dict con 'records_deleted', 'redemptions_deleted', details
    """
    with SessionLocal() as db:
        result = {
            'user_id': user_id,
            'game_type': game_type or 'all',
            'list_only': list_only,
            'all_time': all_time,
            'game_records': [],
            'redemptions': [],
        }

        # 1. Buscar GameRecords de trivia
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        trivia_types = ['trivia', 'trivia_simple', 'trivia_vip']
        if game_type:
            if game_type not in trivia_types:
                print(f"⚠️  Tipo '{game_type}' no válido. Usar: {trivia_types}")
                return result
            trivia_types = [game_type]

        for gt in trivia_types:
            query = db.query(GameRecord).filter(
                and_(
                    GameRecord.user_id == user_id,
                    GameRecord.game_type == gt,
                )
            )
            if not all_time:
                query = query.filter(GameRecord.played_at >= today)

            records = query.all()

            for r in records:
                result['game_records'].append({
                    'id': r.id,
                    'game_type': r.game_type,
                    'result': r.result,
                    'payout': r.payout,
                    'played_at': r.played_at.isoformat() if r.played_at else None,
                })

        # 2. Buscar StreakPromotionRedemptions
        query = db.query(StreakPromotionRedemption).filter(
            StreakPromotionRedemption.user_id == user_id
        )
        if not all_time:
            # Solo redempciones de hoy
            query = query.filter(StreakPromotionRedemption.redeemed_at >= today)

        redemptions = query.all()

        for r in redemptions:
            result['redemptions'].append({
                'id': r.id,
                'promotion_id': r.promotion_id,
                'level_id': r.level_id,
                'code_id': r.code_id,
                'streak_achieved': r.streak_achieved,
                'redeemed_at': r.redeemed_at.isoformat() if r.redeemed_at else None,
            })

        if list_only:
            scope = "histórico" if all_time else "de hoy"
            print(f"\n📋 Usuario {user_id} - ESTADO ACTUAL ({scope}):")
            print(f"\n🎮 GameRecords ({len(result['game_records'])}):")
            if result['game_records']:
                for rec in result['game_records']:
                    print(f"   • {rec['game_type']}: {rec['result']} (+{rec['payout']}) @ {rec['played_at']}")
            else:
                print("   (ninguno)")

            print(f"\n🎁 Códigos canjeados ({len(result['redemptions'])}):")
            if result['redemptions']:
                for red in result['redemptions']:
                    print(f"   • streak={red['streak_achieved']} @ {red['redeemed_at']}")
            else:
                print("   (ninguno)")
            return result

        if not result['game_records'] and not result['redemptions']:
            print(f"\n✅ No hay registros que eliminar para usuario {user_id}")
            return result

        # 3. Eliminar si no es list_only
        print(f"\n🗑️  Eliminando registros...")

        for rec in result['game_records']:
            db.delete(db.query(GameRecord).get(rec['id']))

        for red in result['redemptions']:
            db.delete(db.query(StreakPromotionRedemption).get(red['id']))

        db.commit()

        result['records_deleted'] = len(result['game_records'])
        result['redemptions_deleted'] = len(result['redemptions'])

        print(f"✅ Eliminados:")
        print(f"   • {result['records_deleted']} GameRecords")
        print(f"   • {result['redemptions_deleted']} Códigos de promoción")

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Resetea el estado de trivia de un usuario"
    )
    parser.add_argument('user_id', type=int, help='ID del usuario')
    parser.add_argument(
        '--game-type', '-t',
        choices=['trivia', 'trivia_simple', 'trivia_vip'],
        help='Filtrar por tipo de trivia'
    )
    parser.add_argument(
        '--list-only', '-l',
        action='store_true',
        help='Solo mostrar lo que se eliminaría sin borrar'
    )
    parser.add_argument(
        '--all-time', '-a',
        action='store_true',
        help='Resetear TODO el historial (no solo de hoy)'
    )

    args = parser.parse_args()

    print(f"🔄 Reset deTrivia - Usuario {args.user_id}")
    print(f"   Tipo: {args.game_type or 'todos'}")
    scope = "TODO" if args.all_time else "hoy"
    print(f"   Alcance: {scope}")
    print(f"   Modo: {'VERIFICAR' if args.list_only else 'ELIMINAR'}")

    result = reset_user_trivia(
        user_id=args.user_id,
        game_type=args.game_type,
        list_only=args.list_only,
        all_time=args.all_time
    )

    if args.list_only:
        sys.exit(0 if result.get('game_records') or result.get('redemptions') else 1)
    else:
        total = result.get('records_deleted', 0) + result.get('redemptions_deleted', 0)
        sys.exit(0 if total > 0 else 0)


if __name__ == '__main__':
    main()