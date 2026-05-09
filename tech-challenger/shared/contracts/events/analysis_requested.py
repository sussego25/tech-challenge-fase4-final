from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArchitectureAnalysisRequestedEvent(BaseModel):
    diagram_id: UUID = Field(default_factory=uuid4)
    s3_bucket: str
    s3_key: str
    user_id: str | None = None
    requested_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)
