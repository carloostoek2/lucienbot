"""
Trivia Stats Service - Estadísticas de Promociones y Usuarios de Trivia

Proporciona métricas detalladas para promociones de trivia y usuarios.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import (
    TriviaPromotionConfig,
    DiscountCode,
    DiscountCodeStatus,
    GameRecord,
    QuestionSet,
    User
)
from models.database import SessionLocal

logger = logging.getLogger(__name__)


class TriviaStatsService:
    """Servicio para estadísticas de promociones y usuarios de trivia"""

    def __init__(self, db: Session = None):
        """Inicializa el servicio con sesión opcional"""
        self._db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene o crea sesión de base de datos"""
        if self._db is not None:
            return self._db
        return SessionLocal()

    def close(self):
        """Cierra la sesión si el servicio la posee"""
        if self._owns_session and self._db is not None:
            self._db.close()
            self._db = None

    def get_promotion_stats(self, config_id: int) -> dict:
        """Obtiene métricas para UNA promoción"""
        db = self._get_db()
        try:
            config = db.query(TriviaPromotionConfig).filter(
                TriviaPromotionConfig.id == config_id
            ).first()

            if not config:
                logger.info(f"trivia_stats_service - get_promotion_stats - {config_id} - not found")
                return {}

            # Contar códigos por status
            codes_by_status = {}
            for status in DiscountCodeStatus:
                count = db.query(DiscountCode).filter(
                    DiscountCode.config_id == config_id,
                    DiscountCode.status == status
                ).count()
                codes_by_status[status.value] = count

            total_codes = sum(codes_by_status.values())

            # Nombre de la promoción
            promo_name = config.promotion.name if config.promotion else config.custom_description or config.name

            # Question set name
            question_set_name = None
            if config.question_set_id:
                question_set = db.query(QuestionSet).filter(
                    QuestionSet.id == config.question_set_id
                ).first()
                if question_set:
                    question_set_name = question_set.name

            # Parse discount tiers
            tiers = []
            if config.discount_tiers:
                try:
                    tiers = json.loads(config.discount_tiers)
                except json.JSONDecodeError:
                    # Fallback to legacy fields
                    tiers = []
            elif config.required_streak and config.discount_percentage:
                # Legacy fallback
                tiers = [{
                    "streak": config.required_streak,
                    "discount": config.discount_percentage
                }]

            # Duration remaining
            duration_remaining = None
            if config.duration_minutes:
                from services.trivia_discount_service import TriviaDiscountService
                discount_service = TriviaDiscountService()
                try:
                    duration_remaining = discount_service.get_time_remaining_formatted(config_id)
                finally:
                    discount_service.close()

            # Formatear fechas
            start_date_str = None
            end_date_str = None
            if config.start_date:
                start_date_str = config.start_date.isoformat()
            if config.end_date:
                end_date_str = config.end_date.isoformat()

            # Calcular porcentaje usado
            used_percentage = 0.0
            if config.max_codes > 0:
                used_codes = codes_by_status.get(DiscountCodeStatus.USED.value, 0)
                used_percentage = round((used_codes / config.max_codes * 100), 1)

            result = {
                "id": config.id,
                "name": promo_name,
                "status": config.status,
                "total_codes": total_codes,
                "codes_by_status": codes_by_status,
                "claimed": config.codes_claimed,
                "available": max(0, config.max_codes - config.codes_claimed),
                "max_codes": config.max_codes,
                "used_percentage": used_percentage,
                "tiers": tiers,
                "question_set": question_set_name,
                "duration_remaining": duration_remaining,
                "start_date": start_date_str,
                "end_date": end_date_str
            }

            logger.info(f"trivia_stats_service - get_promotion_stats - {config_id} - found: {total_codes} codes")
            return result
        except Exception as e:
            logger.error(f"trivia_stats_service - get_promotion_stats - {config_id} - error: {e}")
            return {}

    def get_all_promotions_stats(self) -> List[dict]:
        """Obtiene métricas para TODAS las promociones ordenadas por created_at DESC"""
        db = self._get_db()
        try:
            configs = db.query(TriviaPromotionConfig).order_by(
                TriviaPromotionConfig.created_at.desc()
            ).all()

            results = []
            for config in configs:
                stats = self.get_promotion_stats(config.id)
                if stats:
                    results.append(stats)

            logger.info(f"trivia_stats_service - get_all_promotions_stats - total: {len(results)} promotions")
            return results
        except Exception as e:
            logger.error(f"trivia_stats_service - get_all_promotions_stats - error: {e}")
            return []

    def get_user_trivia_stats(self, user_id: int) -> dict:
        """Obtiene métricas de trivia para UN usuario"""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.info(f"trivia_stats_service - get_user_trivia_stats - {user_id} - user not found")
                return {}

            username = user.username
            first_name = user.first_name

            result = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'stats': {}
            }

            for game_type in ['trivia', 'trivia_vip']:
                records = db.query(GameRecord).filter(
                    GameRecord.user_id == user_id,
                    GameRecord.game_type == game_type
                ).all()

                total_plays = len(records)
                correct_answers = sum(1 for r in records if r.payout > 0)
                incorrect_answers = total_plays - correct_answers
                correctness_rate = round(correct_answers / total_plays * 100, 1) if total_plays > 0 else 0.0
                besitos_earned = sum(r.payout for r in records if r.payout > 0)

                # Current streak (today only)
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_records = db.query(GameRecord).filter(
                    GameRecord.user_id == user_id,
                    GameRecord.game_type == game_type,
                    GameRecord.played_at >= today
                ).order_by(GameRecord.played_at.desc()).all()

                current_streak = 0
                for record in today_records:
                    if record.payout > 0:
                        current_streak += 1
                    else:
                        break

                # Calculate max_streak inline from already-loaded records
                max_streak = 0
                streak = 0
                for record in records:
                    if record.payout > 0:
                        streak += 1
                        max_streak = max(max_streak, streak)
                    else:
                        streak = 0

                # Count codes
                codes_earned = db.query(DiscountCode).filter(
                    DiscountCode.user_id == user_id,
                    DiscountCode.status == DiscountCodeStatus.ACTIVE
                ).count()

                codes_used = db.query(DiscountCode).filter(
                    DiscountCode.user_id == user_id,
                    DiscountCode.status == DiscountCodeStatus.USED
                ).count()

                result['stats'][game_type] = {
                    'total_plays': total_plays,
                    'correct_answers': correct_answers,
                    'incorrect_answers': incorrect_answers,
                    'correctness_rate': correctness_rate,
                    'besitos_earned': besitos_earned,
                    'current_streak': current_streak,
                    'max_streak': max_streak,
                    'codes_earned': codes_earned,
                    'codes_used': codes_used
                }

            logger.info(f"trivia_stats_service - get_user_trivia_stats - {user_id} - found")
            return result
        except Exception as e:
            logger.error(f"trivia_stats_service - get_user_trivia_stats - {user_id} - error: {e}")
            return {}
        finally:
            if self._owns_session:
                db.close()

    # ─── Ranking Methods ───────────────────────────────────────────────────────

    def _build_user_rank_entry(self, user_id: int, value: float) -> dict:
        """Build a ranking entry dict with user info."""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return {
                'user_id': user_id,
                'username': user.username if user else None,
                'first_name': user.first_name if user else None,
                'value': value
            }
        finally:
            if self._owns_session:
                db.close()

    def _calc_max_streak_for_user(self, user_id: int) -> int:
        """Calculate max streak for a user across trivia and trivia_vip."""
        db = self._get_db()
        try:
            max_streak = 0
            for game_type in ['trivia', 'trivia_vip']:
                records = db.query(GameRecord).filter(
                    GameRecord.user_id == user_id,
                    GameRecord.game_type == game_type
                ).order_by(GameRecord.played_at.asc()).all()
                current = 0
                for record in records:
                    if record.payout > 0:
                        current += 1
                        max_streak = max(max_streak, current)
                    else:
                        current = 0
            return max_streak
        finally:
            if self._owns_session:
                db.close()

    def get_top_scorers(self, limit: int = 10) -> list[dict]:
        """Top users by total correct answers (trivia + trivia_vip combined)."""
        db = self._get_db()
        try:
            rows = db.query(
                GameRecord.user_id,
                func.count(GameRecord.id).label('correct_count')
            ).filter(
                GameRecord.game_type.in_(['trivia', 'trivia_vip']),
                GameRecord.payout > 0
            ).group_by(
                GameRecord.user_id
            ).order_by(
                func.count(GameRecord.id).desc()
            ).limit(limit).all()

            results = []
            for rank, row in enumerate(rows, start=1):
                entry = self._build_user_rank_entry(row.user_id, row.correct_count)
                entry['rank'] = rank
                results.append(entry)

            logger.info(f"trivia_stats_service - get_top_scorers - returned {len(results)} entries")
            return results
        except Exception as e:
            logger.error(f"trivia_stats_service - get_top_scorers - error: {e}")
            return []
        finally:
            if self._owns_session:
                db.close()

    def get_top_streaks(self, limit: int = 10) -> list[dict]:
        """Top users by max streak (trivia + trivia_vip combined)."""
        db = self._get_db()
        try:
            # Get all unique user_ids who played trivia/trivia_vip
            user_ids = db.query(GameRecord.user_id).filter(
                GameRecord.game_type.in_(['trivia', 'trivia_vip'])
            ).distinct().all()
            user_ids = [uid[0] for uid in user_ids]

            # Calculate max streak for each user
            streak_data = []
            for user_id in user_ids:
                max_s = self._calc_max_streak_for_user(user_id)
                streak_data.append((user_id, max_s))

            # Sort by max_streak DESC
            streak_data.sort(key=lambda x: x[1], reverse=True)
            streak_data = streak_data[:limit]

            results = []
            for rank, (user_id, max_s) in enumerate(streak_data, start=1):
                entry = self._build_user_rank_entry(user_id, max_s)
                entry['rank'] = rank
                results.append(entry)

            logger.info(f"trivia_stats_service - get_top_streaks - returned {len(results)} entries")
            return results
        except Exception as e:
            logger.error(f"trivia_stats_service - get_top_streaks - error: {e}")
            return []
        finally:
            if self._owns_session:
                db.close()

    def get_top_codes_redeemed(self, limit: int = 10) -> list[dict]:
        """Top users by used discount codes."""
        db = self._get_db()
        try:
            rows = db.query(
                DiscountCode.user_id,
                func.count(DiscountCode.id).label('codes_count')
            ).filter(
                DiscountCode.status == DiscountCodeStatus.USED
            ).group_by(
                DiscountCode.user_id
            ).order_by(
                func.count(DiscountCode.id).desc()
            ).limit(limit).all()

            results = []
            for rank, row in enumerate(rows, start=1):
                entry = self._build_user_rank_entry(row.user_id, row.codes_count)
                entry['rank'] = rank
                results.append(entry)

            logger.info(f"trivia_stats_service - get_top_codes_redeemed - returned {len(results)} entries")
            return results
        except Exception as e:
            logger.error(f"trivia_stats_service - get_top_codes_redeemed - error: {e}")
            return []
        finally:
            if self._owns_session:
                db.close()
