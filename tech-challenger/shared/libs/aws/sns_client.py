import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from libs.aws.exceptions import SNSPublishError


class SNSClient:
    def __init__(
        self,
        topic_arn: str | None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        if not topic_arn:
            raise ValueError("topic_arn must be a non-empty string")
        self._topic_arn = topic_arn
        self._client = boto_client or boto3.client(
            "sns", region_name=region or os.getenv("AWS_REGION")
        )

    def publish(self, payload: Any) -> None:
        if hasattr(payload, "model_dump_json"):
            message = payload.model_dump_json()
        elif isinstance(payload, dict):
            message = json.dumps(payload, ensure_ascii=False)
        else:
            message = str(payload)

        try:
            self._client.publish(
                TopicArn=self._topic_arn,
                Message=message,
            )
        except ClientError as exc:
            raise SNSPublishError(f"Failed to publish message to SNS: {exc}") from exc
