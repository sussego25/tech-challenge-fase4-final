import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from libs.llm.exceptions import LLMInvokeError


class BedrockClient:
    def __init__(
        self,
        model_id: str | None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        if not model_id:
            raise ValueError("model_id must be a non-empty string")
        self._model_id = model_id
        self._client = boto_client or boto3.client(
            "bedrock-runtime",
            region_name=region or os.getenv("AWS_REGION"),
        )

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": 2048,
                    "temperature": 0.2,
                    "topP": 0.9,
                },
            )
        except ClientError as e:
            raise LLMInvokeError(f"Failed to invoke Bedrock model '{self._model_id}': {e}") from e

        content = (
            response.get("output", {})
            .get("message", {})
            .get("content", [])
        )
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict)
        )
