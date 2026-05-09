from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DiagramStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_VALID_TRANSITIONS: dict[DiagramStatus, set[DiagramStatus]] = {
    DiagramStatus.PENDING: {DiagramStatus.PROCESSING},
    DiagramStatus.PROCESSING: {DiagramStatus.COMPLETED, DiagramStatus.FAILED},
    DiagramStatus.COMPLETED: set(),
    DiagramStatus.FAILED: set(),
}


class ArchitectureDiagram(BaseModel):
    diagram_id: UUID = Field(default_factory=uuid4)
    s3_key: str
    s3_bucket: str
    user_id: str | None = None
    status: DiagramStatus = DiagramStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_report: str | None = None
    error_message: str | None = None
    elements_detected: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    def _transition_to(self, target: DiagramStatus) -> None:
        if target not in _VALID_TRANSITIONS[self.status]:
            raise ValueError(
                f"Invalid status transition: {self.status.value} → {target.value}"
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def mark_processing(self) -> None:
        self._transition_to(DiagramStatus.PROCESSING)

    def mark_completed(self, report: str, elements: list[str]) -> None:
        if not report:
            raise ValueError("analysis_report cannot be empty when marking as completed")
        self._transition_to(DiagramStatus.COMPLETED)
        self.analysis_report = report
        self.error_message = None
        self.elements_detected = elements

    def mark_failed(self, error: str) -> None:
        self._transition_to(DiagramStatus.FAILED)
        self.analysis_report = None
        self.error_message = error
        self.elements_detected = []
