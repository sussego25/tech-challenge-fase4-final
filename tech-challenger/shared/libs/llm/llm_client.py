from typing import Any

from libs.llm.bedrock_client import BedrockClient
from libs.llm.sagemaker_client import SageMakerClient


class LLMClient:
    def __init__(
        self,
        provider: str = "sagemaker",
        endpoint_name: str | None = None,
        model_id: str | None = None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        provider = (provider or "sagemaker").strip().lower()

        if provider == "sagemaker":
            self._client = SageMakerClient(
                endpoint_name=endpoint_name,
                region=region,
                boto_client=boto_client,
            )
        elif provider == "bedrock":
            self._client = BedrockClient(
                model_id=model_id,
                region=region,
                boto_client=boto_client,
            )
        else:
            raise ValueError("LLM provider must be either 'sagemaker' or 'bedrock'")

    def invoke(self, prompt: str) -> str:
        return self._client.invoke(prompt)
