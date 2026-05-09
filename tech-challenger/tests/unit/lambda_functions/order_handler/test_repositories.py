import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from repositories import DynamoDBDiagramRepository, DiagramNotFoundError
from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus


def _make_diagram(**kwargs) -> ArchitectureDiagram:
    defaults = {
        "s3_key": "diagrams/user-1/abc",
        "s3_bucket": "test-bucket",
        "user_id": "user-1",
    }
    return ArchitectureDiagram(**{**defaults, **kwargs})


def _diagram_to_item(diagram: ArchitectureDiagram) -> dict:
    return {
        "diagram_id": str(diagram.diagram_id),
        "user_id": diagram.user_id,
        "status": diagram.status.value,
        "s3_key": diagram.s3_key,
        "s3_bucket": diagram.s3_bucket,
        "created_at": diagram.created_at.isoformat(),
        "updated_at": diagram.updated_at.isoformat(),
        "elements_detected": diagram.elements_detected,
    }


class TestDynamoDBDiagramRepositorySave:
    def test_save_calls_put_item(self):
        mock_table = MagicMock()
        repo = DynamoDBDiagramRepository(table=mock_table)
        repo.save(_make_diagram())
        mock_table.put_item.assert_called_once()

    def test_save_includes_diagram_id_in_item(self):
        mock_table = MagicMock()
        repo = DynamoDBDiagramRepository(table=mock_table)
        diagram = _make_diagram()
        repo.save(diagram)
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["diagram_id"] == str(diagram.diagram_id)

    def test_save_includes_all_required_fields(self):
        mock_table = MagicMock()
        repo = DynamoDBDiagramRepository(table=mock_table)
        repo.save(_make_diagram())
        item = mock_table.put_item.call_args.kwargs["Item"]
        for field in ("diagram_id", "user_id", "status", "s3_key", "s3_bucket", "created_at", "updated_at"):
            assert field in item, f"Missing field: {field}"

    def test_save_status_is_string_value(self):
        mock_table = MagicMock()
        repo = DynamoDBDiagramRepository(table=mock_table)
        repo.save(_make_diagram())
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["status"] == DiagramStatus.PENDING.value


class TestDynamoDBDiagramRepositoryGet:
    def test_get_returns_architecture_diagram(self):
        diagram = _make_diagram()
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": _diagram_to_item(diagram)}

        repo = DynamoDBDiagramRepository(table=mock_table)
        result = repo.get(str(diagram.diagram_id))

        assert isinstance(result, ArchitectureDiagram)
        assert result.diagram_id == diagram.diagram_id

    def test_get_restores_correct_user_id(self):
        diagram = _make_diagram(user_id="restored-user")
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": _diagram_to_item(diagram)}

        repo = DynamoDBDiagramRepository(table=mock_table)
        result = repo.get(str(diagram.diagram_id))

        assert result.user_id == "restored-user"

    def test_get_calls_dynamodb_with_diagram_id_key(self):
        diagram = _make_diagram()
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": _diagram_to_item(diagram)}

        repo = DynamoDBDiagramRepository(table=mock_table)
        repo.get(str(diagram.diagram_id))

        mock_table.get_item.assert_called_once_with(Key={"diagram_id": str(diagram.diagram_id)})

    def test_get_raises_diagram_not_found_when_item_missing(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}

        repo = DynamoDBDiagramRepository(table=mock_table)

        with pytest.raises(DiagramNotFoundError):
            repo.get("nonexistent-id")

    def test_diagram_not_found_error_contains_diagram_id(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        repo = DynamoDBDiagramRepository(table=mock_table)

        with pytest.raises(DiagramNotFoundError) as exc_info:
            repo.get("missing-id-123")

        assert "missing-id-123" in str(exc_info.value)
