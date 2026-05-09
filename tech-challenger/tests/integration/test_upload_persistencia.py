"""
===========================================================================
Testes de Integração e Resiliência — Upload & Persistência (order-handler)
===========================================================================

Cenários Gherkin:
---------------------------------------------------------------------------
Feature: Upload e Persistência de Diagrama

  Scenario: Happy path — upload válido persiste PENDING e enfileira no SQS
    Given um usuário autenticado com user_id "user-abc-123"
      And uma imagem PNG válida de 72 bytes codificada em base64
    When o order-handler recebe a requisição de upload
    Then o diagrama é salvo no S3 com a chave "diagrams/user-abc-123/<uuid>"
      And o status do diagrama no DynamoDB é "pending"
      And uma mensagem ArchitectureAnalysisRequestedEvent é enviada ao SQS

  Scenario: Upload com content-type inválido retorna 400
    Given um usuário autenticado com user_id "user-abc-123"
      And uma imagem com content-type "application/pdf"
    When o order-handler recebe a requisição de upload
    Then a resposta HTTP é 400 com erro "Unsupported content type"

  Scenario: Upload sem header x-user-id retorna 400
    Given uma requisição sem o header "x-user-id"
    When o order-handler recebe a requisição de upload
    Then a resposta HTTP é 400 com erro "Missing required header: x-user-id"

  Scenario: Falha no S3 gera 500 sem vazar stack trace
    Given um usuário autenticado com user_id "user-abc-123"
      And o S3 retorna um erro de conexão
    When o order-handler recebe a requisição de upload
    Then a resposta HTTP é 500 com corpo {"error": "Internal server error"}
      And o stack trace NÃO aparece no corpo da resposta
---------------------------------------------------------------------------
"""

import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from uuid import UUID, uuid4

import pytest

# Ajuste de sys.path para importar o handler do Lambda
_ORDER_HANDLER_DIR = str(
    Path(__file__).resolve().parents[2]
    / "services"
    / "lambda-functions"
    / "order-handler"
)
if _ORDER_HANDLER_DIR not in sys.path:
    sys.path.insert(0, _ORDER_HANDLER_DIR)

_SHARED_DIR = str(Path(__file__).resolve().parents[2] / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_api_event(
    body: bytes | str | None = None,
    content_type: str = "image/png",
    user_id: str = "user-abc-123",
    is_base64: bool = True,
) -> dict:
    """Cria um evento API Gateway v1/v2 simulado."""
    headers = {"content-type": content_type}
    if user_id:
        headers["x-user-id"] = user_id

    encoded_body = base64.b64encode(body).decode() if isinstance(body, bytes) and is_base64 else body

    return {
        "headers": headers,
        "body": encoded_body,
        "isBase64Encoded": is_base64,
    }


# ---------------------------------------------------------------------------
# Testes — Happy Path: Upload ➜ DynamoDB (PENDING) ➜ SQS
# ---------------------------------------------------------------------------
class TestUploadPersistenciaHappyPath:
    """
    Given: usuário autenticado + imagem válida
    When:  order-handler processa o upload
    Then:  S3 upload + DynamoDB save (PENDING) + SQS send_message
    """

    @patch("handler._use_case", None)  # força re-init para cada teste
    def test_upload_persiste_pending_e_envia_sqs(
        self,
        mock_s3_client,
        mock_sqs_client,
        mock_dynamodb_table,
        sample_image_bytes,
    ):
        from contracts.entities.architecture_diagram import DiagramStatus

        # Patch das dependências externas
        with (
            patch("handler.S3Client", return_value=mock_s3_client),
            patch("handler.SQSClient", return_value=mock_sqs_client),
            patch("handler.boto3") as mock_boto3,
        ):
            mock_boto3.resource.return_value.Table.return_value = mock_dynamodb_table

            import handler

            handler._use_case = None  # garante re-init

            event = _make_api_event(body=sample_image_bytes)
            response = handler.lambda_handler(event, None)

        # --- Assertions ---
        assert response["statusCode"] == 202

        body = json.loads(response["body"])
        assert "diagram_id" in body
        assert body["status"] == DiagramStatus.PENDING.value

        # S3 recebeu o upload
        mock_s3_client.upload_file.assert_called_once()
        s3_args = mock_s3_client.upload_file.call_args
        assert s3_args[0][0] == sample_image_bytes  # image_data
        assert "diagrams/user-abc-123/" in s3_args[0][1]  # s3_key
        assert s3_args[1]["content_type"] == "image/png"

        # SQS recebeu a mensagem (ArchitectureAnalysisRequestedEvent)
        mock_sqs_client.send_message.assert_called_once()
        sqs_payload = mock_sqs_client.send_message.call_args[0][0]
        assert hasattr(sqs_payload, "diagram_id")
        assert sqs_payload.user_id == "user-abc-123"

        # DynamoDB persistiu o diagrama
        mock_dynamodb_table.put_item.assert_called_once()
        dynamo_item = mock_dynamodb_table.put_item.call_args[1]["Item"]
        assert dynamo_item["status"] == "pending"
        assert dynamo_item["user_id"] == "user-abc-123"


# ---------------------------------------------------------------------------
# Testes — Validação de Entrada
# ---------------------------------------------------------------------------
class TestUploadValidacao:
    """Cenários de rejeição (400)."""

    @patch("handler._use_case", None)
    def test_content_type_invalido_retorna_400(self, sample_image_bytes):
        with (
            patch("handler.S3Client"),
            patch("handler.SQSClient"),
            patch("handler.boto3"),
        ):
            import handler

            handler._use_case = None

            event = _make_api_event(
                body=sample_image_bytes, content_type="application/pdf"
            )
            response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Unsupported content type" in body["error"]

    @patch("handler._use_case", None)
    def test_sem_user_id_retorna_400(self, sample_image_bytes):
        with (
            patch("handler.S3Client"),
            patch("handler.SQSClient"),
            patch("handler.boto3"),
        ):
            import handler

            handler._use_case = None

            event = _make_api_event(body=sample_image_bytes, user_id="")
            response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "x-user-id" in body["error"]

    @patch("handler._use_case", None)
    def test_body_vazio_retorna_400(self):
        with (
            patch("handler.S3Client"),
            patch("handler.SQSClient"),
            patch("handler.boto3"),
        ):
            import handler

            handler._use_case = None

            event = _make_api_event(body=None, is_base64=False)
            response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "body" in body["error"].lower()


# ---------------------------------------------------------------------------
# Testes — Resiliência: falha no S3 ➜ 500 sem leak
# ---------------------------------------------------------------------------
class TestUploadResiliencia:
    """
    Given: S3 retorna exceção
    When:  order-handler processa o upload
    Then:  500 + mensagem genérica (sem stack trace)
    """

    @patch("handler._use_case", None)
    def test_falha_s3_retorna_500_sem_stack_trace(
        self, mock_sqs_client, mock_dynamodb_table, sample_image_bytes
    ):
        mock_s3_broken = MagicMock()
        mock_s3_broken.upload_file.side_effect = Exception("Connection refused")

        with (
            patch("handler.S3Client", return_value=mock_s3_broken),
            patch("handler.SQSClient", return_value=mock_sqs_client),
            patch("handler.boto3") as mock_boto3,
        ):
            mock_boto3.resource.return_value.Table.return_value = mock_dynamodb_table

            import handler

            handler._use_case = None

            event = _make_api_event(body=sample_image_bytes)
            response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "Internal server error"
        assert "Connection refused" not in body["error"]
        assert "Traceback" not in json.dumps(body)
