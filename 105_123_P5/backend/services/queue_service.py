"""SQLite-backed waiting and correction queues."""

from datetime import datetime, timezone

from app.extensions import db
from app.models import QueueEntry


WaitingQueueEntry = QueueEntry


class QueueService:
    """Queue operations used by dispatch transactions."""

    def enqueue(
        self,
        report_id: str,
        priority: str,
        priority_rank: int,
        reason: str,
        submission_timestamp: datetime | None = None,
        *,
        status: str = "waiting",
    ) -> WaitingQueueEntry:
        entry = QueueEntry(
            report_id=report_id,
            priority=priority,
            priority_rank=priority_rank,
            submission_timestamp=submission_timestamp or datetime.now(timezone.utc).replace(tzinfo=None),
            status=status,
            reason=reason,
        )
        db.session.add(entry)
        return entry

    def pending(self) -> list[WaitingQueueEntry]:
        return (
            WaitingQueueEntry.query.filter(
                WaitingQueueEntry.status.in_(("waiting", "correction_queue"))
            )
            .order_by(
                WaitingQueueEntry.priority_rank,
                WaitingQueueEntry.submission_timestamp,
                WaitingQueueEntry.id,
            )
            .all()
        )
