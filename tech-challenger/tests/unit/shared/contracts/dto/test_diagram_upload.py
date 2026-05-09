import pytest
from pydantic import ValidationError

from contracts.dto import DiagramUploadRequest


class TestDiagramUploadRequest:

    def test_create_with_valid_fields(self):
        dto = DiagramUploadRequest(
            user_id="user-123",
            file_name="architecture.png",
            content_type="image/png",
        )
        assert dto.user_id == "user-123"
        assert dto.file_name == "architecture.png"
        assert dto.content_type == "image/png"

    def test_missing_user_id_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            DiagramUploadRequest(
                file_name="diagram.png",
                content_type="image/png",
            )
        assert "user_id" in str(exc_info.value)

    def test_missing_file_name_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            DiagramUploadRequest(
                user_id="user-123",
                content_type="image/png",
            )
        assert "file_name" in str(exc_info.value)

    def test_invalid_content_type_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            DiagramUploadRequest(
                user_id="user-123",
                file_name="diagram.pdf",
                content_type="application/pdf",
            )
        assert "content_type" in str(exc_info.value)

    def test_accepted_content_types(self):
        for ct in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            dto = DiagramUploadRequest(
                user_id="u1",
                file_name=f"diagram.{ct.split('/')[1]}",
                content_type=ct,
            )
            assert dto.content_type == ct

    def test_json_round_trip(self):
        dto = DiagramUploadRequest(
            user_id="user-789",
            file_name="arch.png",
            content_type="image/png",
        )
        json_str = dto.model_dump_json()
        restored = DiagramUploadRequest.model_validate_json(json_str)
        assert restored.user_id == "user-789"
        assert restored.file_name == "arch.png"
