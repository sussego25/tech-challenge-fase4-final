from unittest.mock import MagicMock

import pytest

from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus
from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from use_cases import ProcessDiagramUploadUseCase


S3_BUCKET = "test-bucket"
S3_KEY = "diagrams/sample.png"


@pytest.fixture
def mock_sqs():
    return MagicMock()


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def use_case(mock_sqs, mock_repo):
    return ProcessDiagramUploadUseCase(
        sqs_client=mock_sqs,
        repository=mock_repo,
    )


class TestProcessDiagramUploadUseCaseOutput:
    def test_returns_architecture_diagram(self, use_case):
        result = use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        assert isinstance(result, ArchitectureDiagram)

    def test_returned_diagram_starts_pending(self, use_case):
        result = use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        assert result.status == DiagramStatus.PENDING

    def test_returned_diagram_has_s3_location(self, use_case):
        result = use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        assert result.s3_bucket == S3_BUCKET
        assert result.s3_key == S3_KEY


class TestProcessDiagramUploadUseCaseSideEffects:
    def test_saves_diagram_to_repository(self, use_case, mock_repo):
        use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        mock_repo.save.assert_called_once()

    def test_repository_save_receives_architecture_diagram(self, use_case, mock_repo):
        use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        saved = mock_repo.save.call_args[0][0]
        assert isinstance(saved, ArchitectureDiagram)

    def test_publishes_event_to_sqs(self, use_case, mock_sqs):
        use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        mock_sqs.send_message.assert_called_once()

    def test_sqs_event_has_same_diagram_and_s3_location(self, use_case, mock_sqs):
        diagram = use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)
        event = mock_sqs.send_message.call_args[0][0]
        assert isinstance(event, ArchitectureAnalysisRequestedEvent)
        assert event.diagram_id == diagram.diagram_id
        assert event.s3_bucket == S3_BUCKET
        assert event.s3_key == S3_KEY

    def test_saves_before_publishing_to_sqs(self, mock_sqs, mock_repo):
        calls: list[str] = []
        mock_repo.save.side_effect = lambda diagram: calls.append("save")
        mock_sqs.send_message.side_effect = lambda event: calls.append("send")

        use_case = ProcessDiagramUploadUseCase(
            sqs_client=mock_sqs,
            repository=mock_repo,
        )
        use_case.execute(s3_bucket=S3_BUCKET, s3_key=S3_KEY)

        assert calls == ["save", "send"]
