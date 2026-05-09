from datetime import datetime, timezone
from uuid import uuid4

from contracts.entities.architecture_diagram import ArchitectureDiagram
from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from libs.aws.sqs_client import SQSClient
from repositories import DynamoDBDiagramRepository


class ProcessDiagramUploadUseCase:
    def __init__(
        self,
        sqs_client: SQSClient,
        repository: DynamoDBDiagramRepository,
    ) -> None:
        self._sqs = sqs_client
        self._repo = repository

    def execute(self, s3_bucket: str, s3_key: str) -> ArchitectureDiagram:
        diagram_id = uuid4()

        diagram = ArchitectureDiagram(
            diagram_id=diagram_id,
            s3_key=s3_key,
            s3_bucket=s3_bucket,
        )

        event = ArchitectureAnalysisRequestedEvent(
            diagram_id=diagram_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            requested_at=datetime.now(timezone.utc),
        )
        self._repo.save(diagram)
        self._sqs.send_message(event)

        return diagram
