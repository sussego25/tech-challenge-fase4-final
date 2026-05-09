import json
import logging

from contracts.entities.architecture_diagram import ArchitectureDiagram
from contracts.entities.architecture_diagram import DiagramStatus
from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from domain.analysis_service import AnalysisService
from infrastructure.diagram_repository import DynamoDBDiagramRepository
from infrastructure.yolo_detector import YoloDetector
from libs.aws.s3_client import S3Client
from libs.aws.sns_client import SNSClient

logger = logging.getLogger(__name__)


class DiagramProcessor:
    def __init__(
        self,
        s3_client: S3Client,
        analysis_service: AnalysisService,
        repository: DynamoDBDiagramRepository,
        yolo_detector: YoloDetector | None = None,
        sns_client: SNSClient | None = None,
    ) -> None:
        self._s3 = s3_client
        self._analysis = analysis_service
        self._repo = repository
        self._yolo = yolo_detector
        self._sns = sns_client

    def process(self, event: ArchitectureAnalysisRequestedEvent) -> None:
        logger.info(
            "Processing diagram analysis: diagram_id=%s bucket=%s key=%s",
            event.diagram_id,
            event.s3_bucket,
            event.s3_key,
        )
        diagram: ArchitectureDiagram = self._repo.get(str(event.diagram_id))

        if diagram.status in {DiagramStatus.COMPLETED, DiagramStatus.FAILED}:
            logger.info(
                "Diagram analysis already finished: diagram_id=%s status=%s",
                diagram.diagram_id,
                diagram.status.value,
            )
            if diagram.status == DiagramStatus.COMPLETED:
                self._publish_analysis_report(diagram)
            return

        if diagram.status == DiagramStatus.PENDING:
            diagram.mark_processing()
            self._repo.save(diagram)
        else:
            logger.info(
                "Resuming diagram analysis already in progress: diagram_id=%s",
                diagram.diagram_id,
            )

        try:
            image_data = self._s3.download_file(event.s3_key, bucket=event.s3_bucket)
            yolo_components = self._get_yolo_components(event, image_data)
            logger.info(
                "YOLO detection finished: diagram_id=%s components=%s",
                event.diagram_id,
                yolo_components,
            )
            logger.info("Starting LLM analysis: diagram_id=%s", event.diagram_id)
            report, elements = self._analysis.analyze(
                image_data,
                str(event.diagram_id),
                yolo_components=yolo_components,
            )
            diagram.mark_completed(report, elements or yolo_components)
        except Exception as exc:
            error_msg = str(exc)
            logger.exception(
                "Failed to process diagram analysis: diagram_id=%s bucket=%s key=%s error=%s",
                event.diagram_id,
                event.s3_bucket,
                event.s3_key,
                error_msg,
            )
            diagram.mark_failed(error_msg)

        self._repo.save(diagram)
        if diagram.status == DiagramStatus.COMPLETED:
            self._publish_analysis_report(diagram)
        logger.info(
            "Finished diagram analysis: diagram_id=%s status=%s",
            diagram.diagram_id,
            diagram.status.value,
        )

    def _publish_analysis_report(self, diagram: ArchitectureDiagram) -> None:
        if self._sns is None or not diagram.analysis_report:
            return

        logger.info("Publishing analysis result to SNS: diagram_id=%s", diagram.diagram_id)
        self._sns.publish(
            {
                "analysis_report": diagram.analysis_report,
                "elements_detected": diagram.elements_detected,
            }
        )

    def _get_yolo_components(
        self,
        event: ArchitectureAnalysisRequestedEvent,
        image_data: bytes,
    ) -> list[str]:
        for key in ("COMPONENTES_YOLO", "components_yolo", "yolo_components"):
            raw_components = event.metadata.get(key)
            if raw_components:
                return self._parse_yolo_components(raw_components)

        if self._yolo is None:
            return []

        try:
            logger.info("Starting YOLO detection: diagram_id=%s", event.diagram_id)
            return self._yolo.detect_components(image_data)
        except Exception as exc:
            logger.exception(
                "YOLO detection failed; continuing without detected components: diagram_id=%s error=%s",
                event.diagram_id,
                exc,
            )
            return []

    def _parse_yolo_components(self, raw_components: str) -> list[str]:
        try:
            parsed = json.loads(raw_components)
        except json.JSONDecodeError:
            parsed = raw_components.split(",")

        if isinstance(parsed, dict):
            parsed = parsed.get("predictions", [])

        if isinstance(parsed, list):
            components: list[str] = []
            for item in parsed:
                component = item.get("label", "") if isinstance(item, dict) else item
                component = str(component).strip()
                if component and component not in components:
                    components.append(component)
            return components

        component = str(parsed).strip()
        return [component] if component else []
