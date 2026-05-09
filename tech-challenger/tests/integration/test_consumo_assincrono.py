"""
===========================================================================
Testes de Integração e Resiliência — Consumo Assíncrono (worker-service)
===========================================================================

Cenários Gherkin:
---------------------------------------------------------------------------
Feature: Consumo Assíncrono e Resiliência do Worker

  Scenario: Happy path — worker processa diagrama com sucesso
    Given um diagrama com status "pending" persistido no DynamoDB
      And a imagem correspondente está salva no S3
      And o SageMaker retorna um relatório válido
    When o worker-service consome a mensagem do SQS
    Then o status do diagrama é atualizado para "completed"
      And o relatório e os elementos detectados são salvos no DynamoDB
      And a mensagem é deletada do SQS

  Scenario: Falha no SageMaker — status FAILED sem perda de mensagem
    Given um diagrama com status "pending" persistido no DynamoDB
      And o SageMaker retorna um erro "InferenceError"
    When o worker-service consome a mensagem do SQS
    Then o status do diagrama é atualizado para "failed"
      And o error_message contém "InferenceError"
      And a mensagem é deletada do SQS (processamento concluído, mesmo com falha)

  Scenario: Mensagem SQS com payload inválido
    Given uma mensagem SQS com JSON malformado
    When o worker-service tenta consumir a mensagem
    Then a mensagem NÃO é deletada (retorna à fila após visibility timeout)
      And o erro é logado sem crash do consumer
---------------------------------------------------------------------------
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

_WORKER_SRC = str(
    Path(__file__).resolve().parents[2] / "services" / "worker-service" / "src"
)
if _WORKER_SRC not in sys.path:
    sys.path.insert(0, _WORKER_SRC)

_SHARED_DIR = str(Path(__file__).resolve().parents[2] / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus
from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from libs.aws.sqs_client import SQSMessage


# ---------------------------------------------------------------------------
# Fixtures específicas do worker
# ---------------------------------------------------------------------------
@pytest.fixture
def pending_diagram(diagram_id, s3_key):
    return ArchitectureDiagram(
        diagram_id=diagram_id,
        s3_key=s3_key,
        s3_bucket="test-diagrams-bucket",
        user_id="user-abc-123",
        status=DiagramStatus.PENDING,
    )


@pytest.fixture
def analysis_requested_event(diagram_id, s3_key):
    return ArchitectureAnalysisRequestedEvent(
        diagram_id=diagram_id,
        s3_bucket="test-diagrams-bucket",
        s3_key=s3_key,
        user_id="user-abc-123",
        requested_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sqs_message_from_event(analysis_requested_event):
    return SQSMessage(
        body=analysis_requested_event.model_dump_json(),
        receipt_handle="test-receipt-handle-001",
    )


# ---------------------------------------------------------------------------
# Testes — Happy Path: SQS -> Process -> COMPLETED -> DynamoDB
# ---------------------------------------------------------------------------
class TestWorkerHappyPath:
    """
    Given: diagrama PENDING + imagem no S3 + SageMaker OK
    When:  worker processa a mensagem
    Then:  DynamoDB=COMPLETED + relatório persistido
    """

    def test_processa_diagrama_com_sucesso(
        self,
        mock_s3_client,
        pending_diagram,
        analysis_requested_event,
        sample_image_bytes,
    ):
        from processors.diagram_processor import DiagramProcessor
        from domain.analysis_service import AnalysisService
        from infrastructure.diagram_repository import DynamoDBDiagramRepository

        # Mock do repositório — captura cópias a cada save (o objeto é mutado in-place)
        saved_snapshots: list[ArchitectureDiagram] = []
        mock_repo = MagicMock(spec=DynamoDBDiagramRepository)
        mock_repo.get.return_value = pending_diagram
        mock_repo.save.side_effect = lambda d: saved_snapshots.append(d.model_copy(deep=True))

        # Mock do analysis service (LLM)
        mock_analysis = MagicMock(spec=AnalysisService)
        mock_analysis.analyze.return_value = (
            "Arquitetura com API Gateway, Lambda e DynamoDB",
            ["api_gateway", "lambda", "dynamodb"],
        )

        # S3 retorna imagem
        mock_s3_client.download_file.return_value = sample_image_bytes

        processor = DiagramProcessor(
            s3_client=mock_s3_client,
            analysis_service=mock_analysis,
            repository=mock_repo,
        )

        # --- Act ---
        processor.process(analysis_requested_event)

        # --- Assert ---
        # DynamoDB: 2 saves (PROCESSING + COMPLETED)
        assert len(saved_snapshots) == 2

        assert saved_snapshots[0].status == DiagramStatus.PROCESSING

        assert saved_snapshots[1].status == DiagramStatus.COMPLETED
        assert saved_snapshots[1].analysis_report is not None
        assert "API Gateway" in saved_snapshots[1].analysis_report
        assert "lambda" in saved_snapshots[1].elements_detected

        # S3: download chamado
        mock_s3_client.download_file.assert_called_once_with(
            analysis_requested_event.s3_key,
            bucket=analysis_requested_event.s3_bucket,
        )


# ---------------------------------------------------------------------------
# Testes — Falha no SageMaker ➜ status FAILED
# ---------------------------------------------------------------------------
class TestWorkerSageMakerFailure:
    """
    Given: diagrama PENDING + SageMaker lança exceção
    When:  worker processa a mensagem
    Then:  DynamoDB=FAILED (mensagem não perdida)
    """

    def test_sagemaker_erro_marca_failed_no_dynamo(
        self,
        mock_s3_client,
        pending_diagram,
        analysis_requested_event,
        sample_image_bytes,
    ):
        from processors.diagram_processor import DiagramProcessor
        from domain.analysis_service import AnalysisService
        from infrastructure.diagram_repository import DynamoDBDiagramRepository

        mock_repo = MagicMock(spec=DynamoDBDiagramRepository)
        mock_repo.get.return_value = pending_diagram

        # SageMaker falha
        mock_analysis = MagicMock(spec=AnalysisService)
        mock_analysis.analyze.side_effect = RuntimeError(
            "InferenceError: Model endpoint unavailable"
        )

        mock_s3_client.download_file.return_value = sample_image_bytes

        processor = DiagramProcessor(
            s3_client=mock_s3_client,
            analysis_service=mock_analysis,
            repository=mock_repo,
        )

        # --- Act ---
        processor.process(analysis_requested_event)

        # --- Assert ---
        # DynamoDB: 2 saves (PROCESSING + FAILED)
        assert mock_repo.save.call_count == 2

        final_save = mock_repo.save.call_args_list[1][0][0]
        assert final_save.status == DiagramStatus.FAILED
        assert final_save.analysis_report is None
        assert final_save.elements_detected == []
        assert "InferenceError" in final_save.error_message

    def test_sqs_consumer_deleta_mensagem_apos_processamento_com_falha(
        self,
        mock_s3_client,
        mock_sqs_client,
        pending_diagram,
        sqs_message_from_event,
        sample_image_bytes,
    ):
        """A mensagem SQS é deletada mesmo quando o processamento falha
        (o erro é tratado internamente pelo processor, não relançado)."""
        from consumers.sqs_consumer import SQSConsumer
        from processors.diagram_processor import DiagramProcessor
        from domain.analysis_service import AnalysisService
        from infrastructure.diagram_repository import DynamoDBDiagramRepository

        mock_repo = MagicMock(spec=DynamoDBDiagramRepository)
        mock_repo.get.return_value = pending_diagram

        mock_analysis = MagicMock(spec=AnalysisService)
        mock_analysis.analyze.side_effect = RuntimeError("SageMaker timeout")

        mock_s3_client.download_file.return_value = sample_image_bytes

        processor = DiagramProcessor(
            s3_client=mock_s3_client,
            analysis_service=mock_analysis,
            repository=mock_repo,
        )

        consumer = SQSConsumer(sqs_client=mock_sqs_client, processor=processor)

        # --- Act ---
        consumer._handle_message(sqs_message_from_event)

        # --- Assert --- mensagem deletada (processamento concluído)
        mock_sqs_client.delete_message.assert_called_once_with(
            sqs_message_from_event.receipt_handle
        )


# ---------------------------------------------------------------------------
# Testes — Payload Inválido no SQS
# ---------------------------------------------------------------------------
class TestWorkerPayloadInvalido:
    """
    Given: mensagem SQS com JSON inválido
    When:  consumer tenta processar
    Then:  NÃO deleta a mensagem + NÃO crash
    """

    def test_json_malformado_nao_deleta_mensagem(self, mock_sqs_client):
        from consumers.sqs_consumer import SQSConsumer
        from processors.diagram_processor import DiagramProcessor

        mock_processor = MagicMock(spec=DiagramProcessor)

        consumer = SQSConsumer(sqs_client=mock_sqs_client, processor=mock_processor)

        bad_message = SQSMessage(
            body="{invalid-json!!!}",
            receipt_handle="bad-receipt-001",
        )

        # --- Act --- não deve lançar exceção
        consumer._handle_message(bad_message)

        # --- Assert ---
        mock_sqs_client.delete_message.assert_not_called()
        mock_processor.process.assert_not_called()

    def test_payload_sem_campos_obrigatorios_nao_deleta(self, mock_sqs_client):
        from consumers.sqs_consumer import SQSConsumer
        from processors.diagram_processor import DiagramProcessor

        mock_processor = MagicMock(spec=DiagramProcessor)

        consumer = SQSConsumer(sqs_client=mock_sqs_client, processor=mock_processor)

        incomplete_message = SQSMessage(
            body=json.dumps({"diagram_id": str(uuid4())}),  # faltam campos
            receipt_handle="bad-receipt-002",
        )

        # --- Act ---
        consumer._handle_message(incomplete_message)

        # --- Assert ---
        mock_sqs_client.delete_message.assert_not_called()
