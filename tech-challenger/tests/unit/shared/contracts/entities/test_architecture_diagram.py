import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from contracts.entities import ArchitectureDiagram, DiagramStatus


class TestArchitectureDiagram:

    def test_create_with_minimum_fields(self):
        diagram = ArchitectureDiagram(
            s3_key="diagrams/abc.png",
            s3_bucket="my-bucket",
            user_id="user-123",
        )
        assert isinstance(diagram.diagram_id, UUID)
        assert diagram.status == DiagramStatus.PENDING
        assert diagram.analysis_report is None
        assert diagram.elements_detected == []
        assert isinstance(diagram.created_at, datetime)
        assert isinstance(diagram.updated_at, datetime)

    def test_diagram_id_auto_generated(self):
        d1 = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        d2 = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        assert d1.diagram_id != d2.diagram_id

    def test_missing_s3_key_raises_error(self):
        with pytest.raises(ValidationError):
            ArchitectureDiagram(s3_bucket="b", user_id="u")

    def test_missing_s3_bucket_raises_error(self):
        with pytest.raises(ValidationError):
            ArchitectureDiagram(s3_key="k", user_id="u")

    def test_missing_user_id_raises_error(self):
        with pytest.raises(ValidationError):
            ArchitectureDiagram(s3_key="k", s3_bucket="b")

    def test_mark_processing(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        original_updated_at = diagram.updated_at
        diagram.mark_processing()
        assert diagram.status == DiagramStatus.PROCESSING
        assert diagram.updated_at >= original_updated_at

    def test_mark_processing_from_invalid_state_raises_error(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        diagram.mark_processing()
        diagram.mark_completed("Report text.", ["EC2", "S3"])
        with pytest.raises(ValueError):
            diagram.mark_processing()

    def test_mark_completed(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        diagram.mark_processing()
        diagram.mark_completed("# Architecture Report", ["Lambda", "SQS"])
        assert diagram.status == DiagramStatus.COMPLETED
        assert diagram.analysis_report == "# Architecture Report"
        assert diagram.elements_detected == ["Lambda", "SQS"]

    def test_mark_completed_from_pending_raises_error(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        with pytest.raises(ValueError):
            diagram.mark_completed("Report.", [])

    def test_mark_completed_without_report_raises_error(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        diagram.mark_processing()
        with pytest.raises(ValueError):
            diagram.mark_completed("", [])

    def test_mark_failed(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        diagram.mark_processing()
        diagram.mark_failed("SageMaker timeout")
        assert diagram.status == DiagramStatus.FAILED

    def test_mark_failed_from_pending_raises_error(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        with pytest.raises(ValueError):
            diagram.mark_failed("error")

    def test_json_round_trip(self):
        diagram = ArchitectureDiagram(s3_key="k", s3_bucket="b", user_id="u")
        diagram.mark_processing()
        diagram.mark_completed("Report.", ["EC2"])
        json_str = diagram.model_dump_json()
        restored = ArchitectureDiagram.model_validate_json(json_str)
        assert restored.diagram_id == diagram.diagram_id
        assert restored.status == DiagramStatus.COMPLETED
        assert restored.elements_detected == ["EC2"]
