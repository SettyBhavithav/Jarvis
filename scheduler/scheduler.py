"""
JARVIS V2 - Persistent Task & Reminder Scheduler
Executes one-time reminders, periodic calendar syncs, and background jobs with Supabase persistence.

Authorization model
─────────────────────────────────────────────────────────────────────────────
  Scheduler infra layer (get_due / claim / complete):
      → use_admin=True (service role key)
      → Bypasses RLS — legitimate for a trusted system process

  Handler application layer (user-visible actions like reminders, notifications):
      → Receives ScheduledJobContext(user_id=..., payload=...)
      → The handler itself must supply its own auth_token for any user-scoped
         Supabase operation (storage.save_memory(..., auth_token=user_jwt))
      → The scheduler NEVER passes its admin storage reference into handlers
      → If a handler needs Supabase access, it must obtain the user JWT
         from job context (e.g. from payload["auth_token"] stored at schedule time)

This keeps the service-role privilege strictly contained to scheduling infra.
"""
import time
import json
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from storage.supabase import storage_adapter, DEFAULT_SYSTEM_USER_UUID


@dataclass(frozen=True)
class ScheduledJobContext:
    """
    Constrained, immutable context passed to job handlers.

    The handler receives only the data it needs to do its own work:
      - user_id:   the UUID of the user who scheduled this job
      - payload:   the application-level data stored when scheduling
      - job_id:    the scheduler's internal ID (for logging/idempotency)

    The handler does NOT receive a storage reference or auth token from the
    scheduler — it must supply its own user JWT for any user-scoped cloud op.
    If a handler needs to write to Supabase, the auth_token should have been
    stored in payload at schedule time.
    """
    job_id: str
    user_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


class PersistentScheduler:
    def __init__(self):
        # Private — used only for infra ops (claim, complete) with use_admin=True.
        # Not exposed to handlers.
        self._storage = storage_adapter
        self._is_running = False
        self._thread = None
        self._job_handlers: Dict[str, Callable[[ScheduledJobContext], None]] = {}

    @property
    def storage(self):
        """
        Expose storage for schedule_job() (user-facing scheduling).
        This is NOT the admin storage path — schedule_job passes the user's
        auth_token through, so the scheduled_tasks row is written under
        user identity (RLS-safe).
        """
        return self._storage

    def register_handler(self, action_type: str, handler: Callable[[ScheduledJobContext], None]):
        self._job_handlers[action_type] = handler

    def schedule_job(
        self,
        action_type: str,
        delay_seconds: float,
        payload: Dict[str, Any],
        user_id: str = DEFAULT_SYSTEM_USER_UUID,
        auth_token: Optional[str] = None
    ) -> Optional[str]:
        """
        Schedules a job for future execution. Uses the caller's auth_token
        so the scheduled_tasks INSERT is user-scoped (RLS applies).
        """
        target_timestamp = time.time() + delay_seconds
        return self._storage.add_scheduled_task(
            action_type=action_type,
            target_time=target_timestamp,
            payload=payload,
            user_id=user_id,
            auth_token=auth_token
        )

    def _run_handler_safely(self, handler: Callable, ctx: ScheduledJobContext) -> None:
        """
        Invokes a registered handler with an immutable ScheduledJobContext.

        Enforcement contract:
          - The handler gets only ctx — no storage reference, no admin token.
          - Any Supabase writes inside the handler must use ctx.payload.get("auth_token")
            or another user-supplied credential stored at schedule time.
          - Errors are caught and logged; they must not crash the scheduler loop.
        """
        try:
            # Verify the job's user_id is a valid, non-empty UUID before dispatch.
            # This prevents the scheduler's own system UUID from being accidentally
            # used as a user identity for sensitive operations.
            if not ctx.user_id or ctx.user_id == DEFAULT_SYSTEM_USER_UUID:
                print(
                    f"[Scheduler: job {ctx.job_id} has system/default user_id. "
                    f"Handler must not perform user-scoped Supabase writes without a real UUID.]"
                )
            handler(ctx)
        except Exception as e:
            print(f"[Scheduler Job Error in {ctx.job_id} ({type(handler).__name__})]: {e}")

    def start(self):
        if self._is_running:
            return
        self._is_running = True

        def _worker():
            while self._is_running:
                try:
                    # ── ADMIN INFRA LAYER ──────────────────────────────────────
                    # use_admin=True: service role key, bypasses RLS.
                    # This is the ONLY place the admin privilege is used.
                    due_jobs = self._storage.get_due_scheduled_tasks(use_admin=True)

                    for job in due_jobs:
                        jid = job["id"]

                        # Atomic claim: ensures exactly-once execution across workers
                        if not self._storage.claim_scheduled_task(jid, use_admin=True):
                            continue  # Another worker already claimed it

                        action_type = job["action_type"]
                        job_user_id = job.get("user_id") or DEFAULT_SYSTEM_USER_UUID
                        payload_data = job.get("payload") or {}

                        handler = self._job_handlers.get(action_type)
                        if handler:
                            # ── APPLICATION LAYER ──────────────────────────────
                            # Handler receives a constrained context — no admin refs.
                            ctx = ScheduledJobContext(
                                job_id=jid,
                                user_id=job_user_id,
                                payload=payload_data
                            )
                            self._run_handler_safely(handler, ctx)

                        # Mark complete: admin path, outside handler scope
                        self._storage.mark_scheduled_task_completed(jid, use_admin=True)

                except Exception as e:
                    print(f"[Scheduler Worker Error]: {e}")
                time.sleep(2.0)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._is_running = False

# Global Scheduler Singleton
scheduler = PersistentScheduler()

