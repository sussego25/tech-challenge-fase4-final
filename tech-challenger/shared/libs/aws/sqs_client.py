import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from libs.aws.exceptions import SQSPublishError, SQSDeleteError


@dataclass
class SQSMessage:
    body: str
    receipt_handle: str

    def parse_body(self) -> dict:
        try:
            return json.loads(self.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in SQS message body: {e}") from e


class SQSClient:
    def __init__(
        self,
        queue_url: str | None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        if not queue_url:
            raise ValueError("queue_url must be a non-empty string")
        self._queue_url = queue_url
        self._client = boto_client or boto3.client(
            "sqs", region_name=region or os.getenv("AWS_REGION")
        )

    def send_message(self, payload: Any) -> None:
        if hasattr(payload, "model_dump_json"):
            body = payload.model_dump_json()
        elif isinstance(payload, dict):
            body = json.dumps(payload)
        else:
            body = str(payload)

        try:
            self._client.send_message(
                QueueUrl=self._queue_url,
                MessageBody=body,
            )
        except ClientError as e:
            raise SQSPublishError(f"Failed to publish message to SQS: {e}") from e

    def receive_messages(self, max_messages: int = 10) -> list[SQSMessage]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20,
        )
        return [
            SQSMessage(body=m["Body"], receipt_handle=m["ReceiptHandle"])
            for m in response.get("Messages", [])
        ]

    def delete_message(self, receipt_handle: str) -> None:
        try:
            self._client.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
            )
        except ClientError as e:
            raise SQSDeleteError(f"Failed to delete message from SQS: {e}") from e
