"""
NurtureService - Lucien Bot

Domain owner for Nurture sequences (admin-configurable timed post-VIP / free content deliveries).
Reuses PackageService.deliver_package_to_user for rich content.
Schedules persistent one-shot jobs via SchedulerService (DateTrigger).
Event-driven enrollment from VIP activation (no global batch scans).
Persistent per-user progress for dignity/granularity and idempotency.

Strict adherence: funcs <=50 LOC, verb+context+result naming, logging "nurture_service | action | ...",
owns_session hygiene like PackageService, no duplication, delegates delivery, audience granularity.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import NurtureAudience, NurtureSequence, NurtureStep, UserNurtureProgress
from services.scheduler_service import get_scheduler

# get_service imported inside on_vip_activated to avoid circular at services.__init__ import time.

logger = logging.getLogger(__name__)


class NurtureService:
    """Servicio dueño del dominio Nurture / User Content Lifecycle."""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()

    def close(self):
        """Cierra la sesión si el service la posee (higiene estándar)."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== CRUD SECUENCIAS ====================

    def create_sequence(
        self,
        name: str,
        description: str = None,
        audience: NurtureAudience = NurtureAudience.VIP,
        created_by: int = None,
    ) -> NurtureSequence:
        """Crea secuencia nurture. Log + commit."""
        seq = NurtureSequence(
            name=name,
            description=description,
            audience=audience,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(seq)
        self.db.commit()
        self.db.refresh(seq)
        logger.info(
            f"nurture_service | create_sequence | seq_id={seq.id} | name={name} | audience={audience.value} | result=created"
        )
        return seq

    def get_sequence(self, sequence_id: int) -> NurtureSequence | None:
        """Obtiene secuencia por ID (lazy query; enrichment for admin UI via get_steps_with_package_info / get_step_with_package_info delegates)."""
        return self.db.query(NurtureSequence).filter(NurtureSequence.id == sequence_id).first()

    def get_all_sequences(
        self, active_only: bool = True, audience: NurtureAudience = None
    ) -> list[NurtureSequence]:
        """Lista secuencias (filtro audience/actividad para admin UI)."""
        q = self.db.query(NurtureSequence)
        if active_only:
            q = q.filter(NurtureSequence.is_active.is_(True))
        if audience:
            q = q.filter(NurtureSequence.audience == audience)
        return q.order_by(NurtureSequence.created_at.desc()).all()

    def update_sequence(self, sequence_id: int, **kwargs) -> bool:
        """Actualiza campos permitidos de secuencia."""
        seq = self.get_sequence(sequence_id)
        if not seq:
            return False
        allowed = {"name", "description", "audience", "is_active"}
        changed = False
        for k, v in kwargs.items():
            if k in allowed and hasattr(seq, k):
                setattr(seq, k, v)
                changed = True
        if changed:
            self.db.commit()
            logger.info(
                f"nurture_service | update_sequence | seq_id={sequence_id} | result=updated"
            )
        return changed

    def deactivate_sequence(self, sequence_id: int) -> bool:
        """Desactiva secuencia (soft; no borra progress ni jobs pendientes)."""
        return self.update_sequence(sequence_id, is_active=False)

    # ==================== CRUD STEPS ====================

    def create_step(
        self,
        sequence_id: int,
        step_order: int,
        delay_hours: int = 24,
        package_id: int = None,
        fallback_text: str = None,
    ) -> NurtureStep | None:
        """Crea step dentro de secuencia (valida orden único via constraint)."""
        seq = self.get_sequence(sequence_id)
        if not seq:
            logger.warning(
                f"nurture_service | create_step | seq_id={sequence_id} | result=seq_not_found"
            )
            return None
        if not package_id and not (fallback_text and str(fallback_text).strip()):
            logger.warning(
                f"nurture_service | create_step | seq_id={sequence_id} | result=validation_failed_no_pkg_or_fallback"
            )
            return None
        step = NurtureStep(
            sequence_id=sequence_id,
            step_order=step_order,
            delay_hours=delay_hours,
            package_id=package_id,
            fallback_text=fallback_text,
            is_active=True,
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        logger.info(
            f"nurture_service | create_step | seq_id={sequence_id} | step_id={step.id} | order={step_order} | delay={delay_hours} | result=created"
        )
        return step

    def get_step(self, step_id: int) -> NurtureStep | None:
        """Obtiene step por ID."""
        return self.db.query(NurtureStep).filter(NurtureStep.id == step_id).first()

    def get_steps_for_sequence(
        self, sequence_id: int, active_only: bool = True
    ) -> list[NurtureStep]:
        """Steps ordenados de una secuencia."""
        q = self.db.query(NurtureStep).filter(NurtureStep.sequence_id == sequence_id)
        if active_only:
            q = q.filter(NurtureStep.is_active.is_(True))
        return q.order_by(NurtureStep.step_order).all()

    # ==================== DELEGATES FOR HANDLERS (1-service rule) ====================

    def get_available_packages_for_steps(self) -> list:
        """Thin delegate: returns packages for step wizard select. Handler uses only NurtureService.
        Hygiene: PackageService closed after use (try/finally).
        """
        from services.package_service import PackageService

        pkg_svc = PackageService(db=self.db)
        try:
            return pkg_svc.get_all_packages(active_only=True)
        finally:
            if hasattr(pkg_svc, "close"):
                pkg_svc.close()

    def get_steps_with_package_info(self, sequence_id: int, active_only: bool = True) -> list[dict]:
        """Enriched steps (with pkg_name) so detail UI in handler needs no PackageService call.
        Hygiene: PackageService instances closed after use (try/finally, _owns=False since db passed).
        """
        steps = self.get_steps_for_sequence(sequence_id, active_only=active_only)
        enriched = []
        for s in steps:
            pkg_name = None
            if s.package_id:
                from services.package_service import PackageService

                pkg_svc = PackageService(db=self.db)
                try:
                    pkg = pkg_svc.get_package(s.package_id)
                    pkg_name = pkg.name if pkg else str(s.package_id)
                finally:
                    if hasattr(pkg_svc, "close"):
                        pkg_svc.close()
            enriched.append(
                {
                    "step": s,
                    "pkg_name": pkg_name,
                    "has_fallback": bool(s.fallback_text and str(s.fallback_text).strip()),
                }
            )
        return enriched

    def get_step_with_package_info(self, step_id: int) -> dict | None:
        """Thin delegate for nurture_step_detail (single step + pkg info). Enables exactly 1 NurtureService per handler.
        Hygiene: PackageService closed after use.
        """
        step = self.get_step(step_id)
        if not step:
            return None
        pkg_name = None
        if step.package_id:
            from services.package_service import PackageService

            pkg_svc = PackageService(db=self.db)
            try:
                pkg = pkg_svc.get_package(step.package_id)
                pkg_name = pkg.name if pkg else str(step.package_id)
            finally:
                if hasattr(pkg_svc, "close"):
                    pkg_svc.close()
        return {
            "step": step,
            "pkg_name": pkg_name,
            "has_fallback": bool(step.fallback_text and str(step.fallback_text).strip()),
        }

    async def deliver_test_package(
        self, bot, admin_telegram_id: int, package_id: int
    ) -> tuple[bool, str]:
        """Delegate for admin test send (reuses Package.deliver). Handler calls only Nurture.
        Hygiene: PackageService closed.
        """
        from services.package_service import PackageService

        pkg_svc = PackageService(db=self.db)
        try:
            return await pkg_svc.deliver_package_to_user(bot, admin_telegram_id, package_id)
        finally:
            if hasattr(pkg_svc, "close"):
                pkg_svc.close()

    def update_step(self, step_id: int, **kwargs) -> bool:
        """Actualiza step (delay, package, fallback, active). Conditional commit like update_sequence."""
        step = self.get_step(step_id)
        if not step:
            return False
        allowed = {"step_order", "delay_hours", "package_id", "fallback_text", "is_active"}
        changed = False
        for k, v in kwargs.items():
            if k in allowed and hasattr(step, k):
                setattr(step, k, v)
                changed = True
        if changed:
            self.db.commit()
            logger.info(f"nurture_service | update_step | step_id={step_id} | result=updated")
        return changed

    def deactivate_step(self, step_id: int) -> bool:
        """Desactiva step individual."""
        return self.update_step(step_id, is_active=False)

    # ==================== PROGRESO Y ENROLLMENT ====================

    def get_or_create_progress(
        self, user_telegram_id: int, sequence_id: int
    ) -> UserNurtureProgress:
        """Obtiene o crea el registro de progreso (idempotente por unique)."""
        prog = (
            self.db.query(UserNurtureProgress)
            .filter(
                UserNurtureProgress.user_telegram_id == user_telegram_id,
                UserNurtureProgress.sequence_id == sequence_id,
            )
            .first()
        )
        if prog:
            return prog
        prog = UserNurtureProgress(
            user_telegram_id=user_telegram_id,
            sequence_id=sequence_id,
            last_step_order_delivered=0,
            status="active",
        )
        self.db.add(prog)
        self.db.commit()
        self.db.refresh(prog)
        logger.info(
            f"nurture_service | get_or_create_progress | user_id={user_telegram_id} | seq_id={sequence_id} | result=created"
        )
        return prog

    def get_active_sequences_for_audience(self, audience: str = "vip") -> list[NurtureSequence]:
        """Secuencias activas que aplican al audience (vip/all o free/all)."""
        key = (audience or "vip").upper()
        try:
            aud = NurtureAudience[key]
        except Exception:
            aud = NurtureAudience.VIP
        q = self.db.query(NurtureSequence).filter(NurtureSequence.is_active.is_(True))
        if aud == NurtureAudience.VIP:
            q = q.filter(NurtureSequence.audience.in_([NurtureAudience.VIP, NurtureAudience.ALL]))
        elif aud == NurtureAudience.FREE:
            q = q.filter(NurtureSequence.audience.in_([NurtureAudience.FREE, NurtureAudience.ALL]))
        else:
            q = q.filter(NurtureSequence.audience == NurtureAudience.ALL)
        return q.order_by(NurtureSequence.created_at).all()

    def start_sequences_for_user(self, user_telegram_id: int, audience_filter: str = "vip") -> int:
        """
        Enrola usuario en secuencias matching audience. Crea progress y agenda steps pendientes via scheduler.
        Retorna total de steps/jobs programados (por-step reality for one-shots).
        PII: user_telegram_id + seq/step details in logs + scheduled jobs; protected same as other scheduler jobs (jobstore + logs). Volume = #steps in active matching seqs (admin controlled).
        """
        sequences = self.get_active_sequences_for_audience(audience_filter)
        scheduled_count = 0
        scheduler = get_scheduler()
        if not scheduler:
            logger.warning(
                f"nurture_service | start_sequences_for_user | user_id={user_telegram_id} | result=no_scheduler"
            )
            return 0

        now = datetime.now(UTC)
        for seq in sequences:
            prog = self.get_or_create_progress(user_telegram_id, seq.id)
            if prog.status != "active":
                continue
            steps = self.get_steps_for_sequence(seq.id, active_only=True)
            for step in steps:
                if step.step_order <= prog.last_step_order_delivered:
                    continue
                run_date = now + timedelta(hours=step.delay_hours)
                scheduler.schedule_nurture_step(user_telegram_id, step.id, run_date)
                scheduled_count += 1
            logger.info(
                f"nurture_service | start_sequences_for_user | user_id={user_telegram_id} | seq_id={seq.id} | steps_scheduled={len([s for s in steps if s.step_order > prog.last_step_order_delivered])} | result=enrolled"
            )
        logger.info(
            f"nurture_service | start_sequences_for_user | user_id={user_telegram_id} | audience={audience_filter} | steps_scheduled={scheduled_count} | result=done"
        )
        return scheduled_count

    # ==================== UTIL PARA DELIVERY / ADMIN ====================

    def get_progress(self, user_telegram_id: int, sequence_id: int) -> UserNurtureProgress | None:
        """Progreso actual para un user+seq (para checks en job)."""
        return (
            self.db.query(UserNurtureProgress)
            .filter(
                UserNurtureProgress.user_telegram_id == user_telegram_id,
                UserNurtureProgress.sequence_id == sequence_id,
            )
            .first()
        )

    def update_progress_last_delivered(
        self, user_telegram_id: int, sequence_id: int, step_order: int
    ) -> bool:
        """Actualiza el último paso (conditional update as gate to reduce TOCTOU on concurrent fires).
        PII: user_telegram_id in progress rows + logs; same DB protections as VIP subs / daily claims (no special jobstore here but main DB ACLs apply).
        """
        from models.models import UserNurtureProgress

        # conditional to act as gate: only rows where current last < order get updated
        res = (
            self.db.query(UserNurtureProgress)
            .filter(
                UserNurtureProgress.user_telegram_id == user_telegram_id,
                UserNurtureProgress.sequence_id == sequence_id,
                (UserNurtureProgress.last_step_order_delivered.is_(None))
                | (UserNurtureProgress.last_step_order_delivered < step_order),
            )
            .update(
                {UserNurtureProgress.last_step_order_delivered: step_order},
                synchronize_session=False,
            )
        )
        if res:
            prog = self.get_progress(user_telegram_id, sequence_id)
            if prog and all(
                s.step_order <= step_order for s in self.get_steps_for_sequence(sequence_id)
            ):
                prog.status = "completed"
            self.db.commit()
            logger.info(
                f"nurture_service | update_progress_last_delivered | user_id={user_telegram_id} | seq_id={sequence_id} | step_order={step_order} | result=advanced"
            )
            return True
        return False

    def remove_jobs_for_user_sequence(self, user_telegram_id: int, sequence_id: int) -> None:
        """Remueve jobs programados para una secuencia de un usuario (usado en cancel/pause/expiry). Calls only public scheduler API.
        PII: user_telegram_id used to prefix jobs in scheduler remove; same jobstore protections.
        """
        scheduler = get_scheduler()
        if not scheduler:
            return
        steps = self.get_steps_for_sequence(sequence_id, active_only=False)
        step_ids = [s.id for s in steps]
        scheduler.remove_nurture_jobs(user_telegram_id, step_ids=step_ids)
        logger.info(
            f"nurture_service | remove_jobs_for_user_sequence | user_id={user_telegram_id} | seq_id={sequence_id} | result=jobs_removed"
        )

    def pause_progress(self, user_telegram_id: int, sequence_id: int) -> bool:
        """Pausa progreso (no cancela jobs ya disparados, pero previene en handler)."""
        prog = self.get_progress(user_telegram_id, sequence_id)
        if prog:
            prog.status = "paused"
            self.db.commit()
            self.remove_jobs_for_user_sequence(user_telegram_id, sequence_id)
            logger.info(
                f"nurture_service | pause_progress | user_id={user_telegram_id} | seq_id={sequence_id} | result=paused"
            )
            return True
        return False


# --- Cross-domain listener (registered centrally in bot.py, like besitos_awarded observers) ---
# MUST NOT mutate VIP state. Best-effort. Owns its session via get_service.
async def on_vip_activated(payload: dict) -> None:
    """
    Listener for EVENT_VIP_ACTIVATED.
    Starts matching active VIP/ALL nurture sequences for the user (persistent scheduling; returns steps_scheduled total).
    Best-effort: errors logged, no impact on VIP redeem atomicity.
    DESIRED CONTRACT: purely observational + enrollment trigger; no re-entrancy into redeem.
    PII: user_id from payload (telegram) logged; protected as other listeners (best-effort, no extra storage beyond progress which is main DB).
    """
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        logger.debug("nurture_service | on_vip_activated | result=missing_user_id")
        return
    try:
        from services import (
            get_service,
        )  # inside to prevent circular init when services.__init__ imports us

        with get_service(NurtureService) as nurture_svc:
            count = nurture_svc.start_sequences_for_user(int(user_id), audience_filter="vip")
        logger.info(
            f"nurture_service | on_vip_activated | user_id={user_id} | steps_scheduled={count} | result=handled"
        )
    except Exception as e:
        logger.warning(
            f"nurture_service | on_vip_activated | user_id={user_id} | error={e} | result=swallowed_best_effort"
        )
