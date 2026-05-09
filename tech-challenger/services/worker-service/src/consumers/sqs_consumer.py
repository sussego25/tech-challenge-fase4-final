import logging
import time

from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from libs.aws.sqs_client import SQSClient, SQSMessage
from processors.diagram_processor import DiagramProcessor

logger = logging.getLogger(__name__)

_POLL_ERROR_BACKOFF_SECONDS = 5


class SQSConsumer:
    def __init__(self, sqs_client: SQSClient, processor: DiagramProcessor) -> None:
        self._sqs = sqs_client
        self._processor = processor

    def run(self) -> None:
        logger.info("Worker started. Polling SQS...")
        while True:
            try:
                self._process_batch()
            except Exception as exc:
                logger.exception(
                    "Error polling SQS, retrying in %ds: %s",
                    _POLL_ERROR_BACKOFF_SECONDS,
                    exc,
                )
                time.sleep(_POLL_ERROR_BACKOFF_SECONDS)

    def _process_batch(self) -> None:
        messages: list[SQSMessage] = self._sqs.receive_messages(max_messages=10)
        for msg in messages:
            self._handle_message(msg)

    def _handle_message(self, msg: SQSMessage) -> None:
        try:
            payload = msg.parse_body()
            event = ArchitectureAnalysisRequestedEvent(**payload)
            self._processor.process(event)
            self._sqs.delete_message(msg.receipt_handle)
        except (ValueError, KeyError) as exc:
            logger.error("Invalid message payload, skipping: %s", exc)
        except Exception as exc:
            logger.exception("Unexpected error processing message: %s", exc)
