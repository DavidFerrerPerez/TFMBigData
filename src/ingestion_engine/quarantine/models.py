from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage


@dataclass
class QuarantineRecord:
    run_id: str
    environment: str
    template_code: str
    stage: FailureStage
    error_code: ErrorCode
    error_message: str
    asset: dict
    source_id: str | None = None
    code_reference: str | None = None
    field_name: str | None = None
    quarantine_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    failed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )