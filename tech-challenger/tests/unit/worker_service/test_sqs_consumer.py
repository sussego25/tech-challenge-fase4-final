import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from consumers.sqs_consumer import SQSConsumer
from libs.aws.sqs_client import SQSMessage


DIAGRAM_ID = str(uuid4())

VALID_BODY = json.dumps({
    "diagram_id": DIAGRAM_ID,
    "s3_bucket": "test-bucket",
    "s3_key": f"diagrams/user-1/{DIAGRAM_ID}",
    "user_id": "user-1",
    "requested_at": datetime.now(timezone.utc).isoformat(),
})


@pytest.fixture
def mock_sqs():
    mock = MagicMock()
    mock.receive_messages.return_value = []
    return mock


@pytest.fixture
def mock_processor():
    return MagicMock()


@pytest.fixture
def consumer(mock_sqs, mock_processor):
    return SQSConsumer(sqs_client=mock_sqs, processor=mock_processor)


class TestSQSConsumerBatch:
    def test_calls_receive_messages(self, consumer, mock_sqs):
        consumer._process_batch()
        mock_sqs.receive_messages.assert_called_once()

    def test_does_nothing_when_no_messages(self, consumer, mock_processor):
        consumer._process_batch()
        mock_processor.process.assert_not_called()

    def test_processes_valid_message(self, consumer, mock_sqs, mock_processor):
        msg = SQSMessage(body=VALID_BODY, receipt_handle="handle-1")
        mock_sqs.receive_messages.return_value = [msg]
        consumer._process_batch()
        mock_processor.process.assert_called_once()

    def test_deletes_message_after_processing(self, consumer, mock_sqs):
        msg = SQSMessage(body=VALID_BODY, receipt_handle="handle-abc")
        mock_sqs.receive_messages.return_value = [msg]
        consumer._process_batch()
        mock_sqs.delete_message.assert_called_once_with("handle-abc")

    def test_processes_multiple_messages(self, consumer, mock_sqs, mock_processor):
        messages = [
            SQSMessage(body=VALID_BODY, receipt_handle=f"handle-{i}")
            for i in range(3)
        ]
        mock_sqs.receive_messages.return_value = messages
        consumer._process_batch()
        assert mock_processor.process.call_count == 3


class TestSQSConsumerErrorHandling:
    def test_skips_message_with_invalid_json(self, consumer, mock_sqs, mock_processor):
        msg = SQSMessage(body="not-valid-json", receipt_handle="bad-handle")
        mock_sqs.receive_messages.return_value = [msg]
        consumer._process_batch()  # should NOT raise
        mock_processor.process.assert_not_called()

    def test_does_not_delete_invalid_message(self, consumer, mock_sqs):
        msg = SQSMessage(body="not-valid-json", receipt_handle="bad-handle")
        mock_sqs.receive_messages.return_value = [msg]
        consumer._process_batch()
        mock_sqs.delete_message.assert_not_called()

    def test_continues_processing_after_bad_message(self, consumer, mock_sqs, mock_processor):
        bad_msg = SQSMessage(body="bad json", receipt_handle="bad")
        good_msg = SQSMessage(body=VALID_BODY, receipt_handle="good")
        mock_sqs.receive_messages.return_value = [bad_msg, good_msg]
        consumer._process_batch()
        mock_processor.process.assert_called_once()
