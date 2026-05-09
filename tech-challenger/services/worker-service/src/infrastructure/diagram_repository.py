from datetime import datetime
from uuid import UUID

import boto3




from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus


class DiagramNotFoundError(Exception):
    def __init__(self, diagram_id: str) -> None:
        super().__init__(f"Diagram not found: {diagram_id}")
        self.diagram_id = diagram_id


class DynamoDBDiagramRepository:
    def __init__(self, table=None, table_name: str = "", region: str = "us-east-1") -> None:
        if table is not None:
            self._table = table
        else:
            if not table_name:
                raise ValueError("table_name cannot be empty when table is not provided")
            dynamodb = boto3.resource("dynamodb", region_name=region)
            self._table = dynamodb.Table(table_name)

    def save(self, diagram: ArchitectureDiagram) -> None:
        item: dict = {
            "diagram_id": str(diagram.diagram_id),
            "user_id": diagram.user_id,
            "status": diagram.status.value,
            "s3_key": diagram.s3_key,
            "s3_bucket": diagram.s3_bucket,
            "created_at": diagram.created_at.isoformat(),
            "updated_at": diagram.updated_at.isoformat(),
            "elements_detected": diagram.elements_detected,
        }
        if diagram.analysis_report:
            item["analysis_report"] = diagram.analysis_report
        if diagram.error_message:
            item["error_message"] = diagram.error_message

        self._table.put_item(Item=item)

    def get(self, diagram_id: str) -> ArchitectureDiagram:
        response = self._table.get_item(Key={"diagram_id": diagram_id})
        item = response.get("Item")
        if item is None:
            raise DiagramNotFoundError(diagram_id)

        return ArchitectureDiagram(
            diagram_id=UUID(item["diagram_id"]),
            user_id=item.get("user_id"),
            status=DiagramStatus(item["status"]),
            s3_key=item["s3_key"],
            s3_bucket=item["s3_bucket"],
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            analysis_report=item.get("analysis_report"),
            error_message=item.get("error_message"),
            elements_detected=item.get("elements_detected", []),
        )
