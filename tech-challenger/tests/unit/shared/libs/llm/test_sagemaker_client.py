import json
import pytest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from libs.llm import LLMClient
from libs.llm.exceptions import LLMInvokeError


@pytest.fixture
def mock_boto_client():
    return MagicMock()


@pytest.fixture
def sagemaker_llm(mock_boto_client):
    return LLMClient(
        provider="sagemaker",
        endpoint_name="my-endpoint",
        boto_client=mock_boto_client,
    )


@pytest.fixture
def bedrock_llm(mock_boto_client):
    return LLMClient(
        provider="bedrock",
        model_id="my-bedrock-model",
        boto_client=mock_boto_client,
    )


class TestLLMClientInit:
    def test_raises_when_sagemaker_endpoint_name_empty(self):
        with pytest.raises(ValueError, match="endpoint_name"):
            LLMClient(provider="sagemaker", endpoint_name="")

    def test_raises_when_bedrock_model_id_empty(self):
        with pytest.raises(ValueError, match="model_id"):
            LLMClient(provider="bedrock", model_id="")

    def test_raises_when_provider_invalid(self):
        with pytest.raises(ValueError, match="provider"):
            LLMClient(provider="unknown", endpoint_name="ignored")


class TestLLMClientInvoke:
    def test_sagemaker_invoke_returns_generated_text(self, sagemaker_llm, mock_boto_client):
        response_body = json.dumps({"generated_text": "# Architecture Report\n\nLooks great."})
        mock_boto_client.invoke_endpoint.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=response_body.encode()))
        }
        result = sagemaker_llm.invoke("Analyze this diagram with elements: EC2, RDS")
        assert result == "# Architecture Report\n\nLooks great."

    def test_bedrock_invoke_returns_generated_text(self, bedrock_llm, mock_boto_client):
        mock_boto_client.converse.return_value = {
            "output": {
                "message": {
                    "content": [{"text": "# Architecture Report\n\nLooks great."}]
                }
            }
        }
        result = bedrock_llm.invoke("Analyze this diagram with elements: EC2, RDS")
        assert result == "# Architecture Report\n\nLooks great."

    def test_sagemaker_invoke_calls_endpoint_with_correct_params(self, sagemaker_llm, mock_boto_client):
        mock_boto_client.invoke_endpoint.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"report"))
        }
        sagemaker_llm.invoke("my prompt")
        mock_boto_client.invoke_endpoint.assert_called_once_with(
            EndpointName="my-endpoint",
            ContentType="application/json",
            Body=json.dumps({"inputs": "my prompt"}).encode(),
        )

    def test_bedrock_invoke_calls_model_with_correct_params(self, bedrock_llm, mock_boto_client):
        mock_boto_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "report"}]}}
        }
        bedrock_llm.invoke("my prompt")
        mock_boto_client.converse.assert_called_once_with(
            modelId="my-bedrock-model",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "my prompt"}],
                }
            ],
            inferenceConfig={
                "maxTokens": 2048,
                "temperature": 0.2,
                "topP": 0.9,
            },
        )

    def test_invoke_accepts_plain_text_response(self, sagemaker_llm, mock_boto_client):
        mock_boto_client.invoke_endpoint.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"Plain report text."))
        }
        result = sagemaker_llm.invoke("prompt")
        assert result == "Plain report text."

    def test_invoke_raises_llm_invoke_error_on_client_error(self, sagemaker_llm, mock_boto_client):
        mock_boto_client.invoke_endpoint.side_effect = ClientError(
            {"Error": {"Code": "ModelError", "Message": "Model failed"}}, "InvokeEndpoint"
        )
        with pytest.raises(LLMInvokeError, match="Failed to invoke"):
            sagemaker_llm.invoke("prompt")

    def test_invoke_falls_back_to_plain_text_on_bad_json(self, sagemaker_llm, mock_boto_client):
        mock_boto_client.invoke_endpoint.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"{invalid json}"))
        }
        result = sagemaker_llm.invoke("prompt")
        assert result == "{invalid json}"
