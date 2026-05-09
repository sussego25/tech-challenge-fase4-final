"""
Fixtures compartilhadas para testes de integração.
Configura mocks de boto3 e LocalStack.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Constantes reutilizáveis
# ---------------------------------------------------------------------------
TEST_BUCKET = "test-diagrams-bucket"
TEST_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
TEST_TABLE_NAME = "test-diagrams-table"
TEST_SAGEMAKER_ENDPOINT = "test-sagemaker-endpoint"
TEST_USER_ID = "user-abc-123"
TEST_REGION = "us-east-1"


# ---------------------------------------------------------------------------
# Diagram factory
# ---------------------------------------------------------------------------
@pytest.fixture
def diagram_id():
    return uuid4()


@pytest.fixture
def s3_key(diagram_id):
    return f"diagrams/{TEST_USER_ID}/{diagram_id}"


@pytest.fixture
def sample_image_bytes():
    """PNG header mínimo (8 bytes) seguido de payload fictício."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# ---------------------------------------------------------------------------
# Mocks boto3 (S3 / SQS / DynamoDB)
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    client.upload_file = MagicMock(return_value=None)
    client.download_file = MagicMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    return client


@pytest.fixture
def mock_sqs_client():
    client = MagicMock()
    client.send_message = MagicMock(return_value=None)
    client.receive_messages = MagicMock(return_value=[])
    client.delete_message = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_dynamodb_table():
    table = MagicMock()
    table.put_item = MagicMock(return_value=None)
    table.get_item = MagicMock(return_value={"Item": None})
    return table


# ---------------------------------------------------------------------------
# Mock SageMaker / LLM
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_sagemaker_runtime():
    client = MagicMock()
    client.invoke_endpoint = MagicMock(
        return_value={
            "Body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps(
                        [{"generated_text": "Arquitetura com API Gateway, Lambda e DynamoDB"}]
                    ).encode()
                )
            )
        }
    )
    return client


# ---------------------------------------------------------------------------
# Environment variables padrão
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", TEST_BUCKET)
    monkeypatch.setenv("SQS_QUEUE_URL", TEST_QUEUE_URL)
    monkeypatch.setenv("DYNAMODB_TABLE", TEST_TABLE_NAME)
    monkeypatch.setenv("AWS_REGION", TEST_REGION)
    monkeypatch.setenv("AWS_DEFAULT_REGION", TEST_REGION)
    monkeypatch.setenv("SAGEMAKER_ENDPOINT", TEST_SAGEMAKER_ENDPOINT)
