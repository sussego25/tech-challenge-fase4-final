from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from contracts.entities.architecture_diagram import DiagramStatus


class AnalysisStatusResponse(BaseModel):
    analysis_id: UUID
    diagram_id: UUID
    status: DiagramStatus
    created_at: datetime
    result: str | None = None
