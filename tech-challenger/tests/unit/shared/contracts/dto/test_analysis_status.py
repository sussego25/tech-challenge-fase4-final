import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from contracts.dto import AnalysisStatusResponse
from contracts.entities import DiagramStatus


class TestAnalysisStatusResponse:

    def test_create_pending_without_result(self):
        response = AnalysisStatusResponse(
            analysis_id=uuid4(),
            diagram_id=uuid4(),
            status=DiagramStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        assert response.status == DiagramStatus.PENDING
        assert response.result is None

    def test_create_completed_with_result(self):
        response = AnalysisStatusResponse(
            analysis_id=uuid4(),
            diagram_id=uuid4(),
            status=DiagramStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            result="# Architecture Report\n\nEverything looks good.",
        )
        assert response.status == DiagramStatus.COMPLETED
        assert response.result is not None

    def test_missing_analysis_id_raises_error(self):
        with pytest.raises(ValidationError):
            AnalysisStatusResponse(
                diagram_id=uuid4(),
                status=DiagramStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )

    def test_missing_diagram_id_raises_error(self):
        with pytest.raises(ValidationError):
            AnalysisStatusResponse(
                analysis_id=uuid4(),
                status=DiagramStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )

    def test_missing_status_raises_error(self):
        with pytest.raises(ValidationError):
            AnalysisStatusResponse(
                analysis_id=uuid4(),
                diagram_id=uuid4(),
                created_at=datetime.now(timezone.utc),
            )

    def test_json_round_trip(self):
        analysis_id = uuid4()
        diagram_id = uuid4()
        response = AnalysisStatusResponse(
            analysis_id=analysis_id,
            diagram_id=diagram_id,
            status=DiagramStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            result="Report content here.",
        )
        json_str = response.model_dump_json()
        restored = AnalysisStatusResponse.model_validate_json(json_str)
        assert restored.analysis_id == analysis_id
        assert restored.diagram_id == diagram_id
        assert restored.result == "Report content here."
