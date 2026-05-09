import json
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from libs.aws.sqs_client import SQSClient, SQSMessage
from libs.aws.exceptions import SQSPublishError, SQSDeleteError


@pytest.fixture
def mock_boto_client():
    return MagicMock()


@pytest.fixture
def sqs(mock_boto_client):
    return SQSClient(queue_url="https://sqs.us-east-1.amazonaws.com/123/test-queue", boto_client=mock_boto_client)


class TestSQSClientInit:
    def test_raises_when_queue_url_is_empty(self):
        with pytest.raises(ValueError, match="queue_url"):
            SQSClient(queue_url="")

    def test_raises_when_queue_url_is_none(self):
        with pytest.raises(ValueError, match="queue_url"):
            SQSClient(queue_url=None)

    def test_creates_boto_client_when_not_injected(self):
        with patch("libs.aws.sqs_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = MagicMock()
            client = SQSClient(queue_url="https://sqs.us-east-1.amazonaws.com/123/q")
            mock_boto3.client.assert_called_once_with("sqs", region_name=None)


class TestSQSClientSendMessage:
    def test_send_message_calls_boto3_with_correct_body(self, sqs, mock_boto_client):
        payload = {"diagram_id": "abc-123", "s3_key": "diagrams/test.png"}
        mock_boto_client.send_message.return_value = {"MessageId": "msg-001"}
        sqs.send_message(payload)
        mock_boto_client.send_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123/test-queue",
            MessageBody=json.dumps(payload),
        )

    def test_send_message_raises_sqs_publish_error_on_client_error(self, sqs, mock_boto_client):
        mock_boto_client.send_message.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Server Error"}}, "SendMessage"
        )
        with pytest.raises(SQSPublishError, match="Failed to publish message"):
            sqs.send_message({"key": "value"})

    def test_send_message_accepts_pydantic_model(self, sqs, mock_boto_client):
        from contracts.events import ArchitectureAnalysisRequestedEvent
        from datetime import datetime, timezone
        mock_boto_client.send_message.return_value = {"MessageId": "msg-002"}
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="bucket", s3_key="key", user_id="u1",
            requested_at=datetime.now(timezone.utc),
        )
        sqs.send_message(event)
        call_args = mock_boto_client.send_message.call_args
        body = json.loads(call_args.kwargs["MessageBody"])
        assert body["s3_bucket"] == "bucket"


class TestSQSClientReceiveMessages:
    def test_receive_returns_list_of_sqs_messages(self, sqs, mock_boto_client):
        mock_boto_client.receive_message.return_value = {
            "Messages": [
                {"Body": '{"key": "val"}', "ReceiptHandle": "rh-001"},
                {"Body": '{"key2": "val2"}', "ReceiptHandle": "rh-002"},
            ]
        }
        messages = sqs.receive_messages(max_messages=5)
        assert len(messages) == 2
        assert isinstance(messages[0], SQSMessage)
        assert messages[0].receipt_handle == "rh-001"

    def test_receive_returns_empty_list_when_no_messages(self, sqs, mock_boto_client):
        mock_boto_client.receive_message.return_value = {}
        messages = sqs.receive_messages()
        assert messages == []

    def test_receive_passes_max_messages(self, sqs, mock_boto_client):
        mock_boto_client.receive_message.return_value = {}
        sqs.receive_messages(max_messages=3)
        mock_boto_client.receive_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123/test-queue",
            MaxNumberOfMessages=3,
            WaitTimeSeconds=20,
        )


class TestSQSClientDeleteMessage:
    def test_delete_message_calls_boto3(self, sqs, mock_boto_client):
        sqs.delete_message("rh-001")
        mock_boto_client.delete_message.assert_called_once_with(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/123/test-queue",
            ReceiptHandle="rh-001",
        )

    def test_delete_raises_sqs_delete_error_on_client_error(self, sqs, mock_boto_client):
        mock_boto_client.delete_message.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "DeleteMessage"
        )
        with pytest.raises(SQSDeleteError, match="Failed to delete message"):
            sqs.delete_message("rh-001")


class TestSQSMessage:
    def test_parse_body_returns_dict(self):
        msg = SQSMessage(body='{"diagram_id": "abc"}', receipt_handle="rh-001")
        assert msg.parse_body() == {"diagram_id": "abc"}

    def test_parse_body_raises_value_error_on_invalid_json(self):
        msg = SQSMessage(body="not-json", receipt_handle="rh-001")
        with pytest.raises(ValueError, match="Invalid JSON"):
            msg.parse_body()
