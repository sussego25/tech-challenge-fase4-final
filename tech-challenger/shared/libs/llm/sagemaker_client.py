import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from libs.llm.exceptions import LLMInvokeError


class SageMakerClient:
    def __init__(
        self,
        endpoint_name: str | None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        if not endpoint_name:
            raise ValueError("endpoint_name must be a non-empty string")
        self._endpoint_name = endpoint_name
        self._client = boto_client or boto3.client(
            "sagemaker-runtime",
            region_name=region or os.getenv("AWS_REGION"),
        )

    def invoke(self, prompt: str) -> str:
        body = json.dumps({"inputs": prompt}).encode()
        try:
            response = self._client.invoke_endpoint(
                EndpointName=self._endpoint_name,
                ContentType="application/json",
                Body=body,
            )
        except ClientError as e:
            raise LLMInvokeError(f"Failed to invoke SageMaker endpoint '{self._endpoint_name}': {e}") from e

        raw = response["Body"].read()
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "generated_text" in parsed:
                return parsed["generated_text"]
            return text
        except json.JSONDecodeError:
            return text
