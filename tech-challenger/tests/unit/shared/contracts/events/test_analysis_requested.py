import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from contracts.events import ArchitectureAnalysisRequestedEvent


class TestArchitectureAnalysisRequestedEvent:

    def test_create_with_all_fields(self):
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="my-bucket",
            s3_key="diagrams/abc.png",
            user_id="user-123",
            requested_at=datetime.now(timezone.utc),
        )
        assert isinstance(event.diagram_id, UUID)
        assert event.s3_bucket == "my-bucket"
        assert event.s3_key == "diagrams/abc.png"
        assert event.user_id == "user-123"
        assert event.metadata == {}

    def test_diagram_id_auto_generated_when_absent(self):
        event1 = ArchitectureAnalysisRequestedEvent(
            s3_bucket="bucket",
            s3_key="key",
            user_id="u1",
            requested_at=datetime.now(timezone.utc),
        )
        event2 = ArchitectureAnalysisRequestedEvent(
            s3_bucket="bucket",
            s3_key="key",
            user_id="u1",
            requested_at=datetime.now(timezone.utc),
        )
        assert event1.diagram_id != event2.diagram_id

    def test_diagram_id_accepted_when_provided(self):
        fixed_id = uuid4()
        event = ArchitectureAnalysisRequestedEvent(
            diagram_id=fixed_id,
            s3_bucket="bucket",
            s3_key="key",
            user_id="u1",
            requested_at=datetime.now(timezone.utc),
        )
        assert event.diagram_id == fixed_id

    def test_missing_s3_bucket_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureAnalysisRequestedEvent(
                s3_key="key",
                user_id="u1",
                requested_at=datetime.now(timezone.utc),
            )
        assert "s3_bucket" in str(exc_info.value)

    def test_missing_s3_key_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureAnalysisRequestedEvent(
                s3_bucket="bucket",
                user_id="u1",
                requested_at=datetime.now(timezone.utc),
            )
        assert "s3_key" in str(exc_info.value)

    def test_missing_user_id_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureAnalysisRequestedEvent(
                s3_bucket="bucket",
                s3_key="key",
                requested_at=datetime.now(timezone.utc),
            )
        assert "user_id" in str(exc_info.value)

    def test_missing_requested_at_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ArchitectureAnalysisRequestedEvent(
                s3_bucket="bucket",
                s3_key="key",
                user_id="u1",
            )

    def test_json_round_trip(self):
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="bucket",
            s3_key="diagrams/test.png",
            user_id="user-456",
            requested_at=datetime.now(timezone.utc),
            metadata={"source": "api-gateway"},
        )
        json_str = event.model_dump_json()
        restored = ArchitectureAnalysisRequestedEvent.model_validate_json(json_str)
        assert restored.diagram_id == event.diagram_id
        assert restored.s3_bucket == event.s3_bucket
        assert restored.user_id == event.user_id
        assert restored.metadata == {"source": "api-gateway"}

    def test_metadata_is_optional(self):
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="bucket",
            s3_key="key",
            user_id="u1",
            requested_at=datetime.now(timezone.utc),
        )
        assert event.metadata == {}

    def test_invalid_diagram_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ArchitectureAnalysisRequestedEvent(
                diagram_id="not-a-uuid",
                s3_bucket="bucket",
                s3_key="key",
                user_id="u1",
                requested_at=datetime.now(timezone.utc),
            )
