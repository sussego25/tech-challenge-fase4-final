"""
===========================================================================
Testes de Contrato (Pacto) — Validação de DTOs em shared/contracts
===========================================================================

Cenários Gherkin:
---------------------------------------------------------------------------
Feature: Validação de Contratos — DiagramUploadRequest

  Scenario: Aceita content_type image/png
    Given um DiagramUploadRequest com content_type "image/png"
    When o modelo é instanciado
    Then nenhuma exceção é lançada
      And content_type é "image/png"

  Scenario: Aceita content_type image/jpeg
    Given um DiagramUploadRequest com content_type "image/jpeg"
    When o modelo é instanciado
    Then nenhuma exceção é lançada

  Scenario: Aceita content_type image/webp
    Given um DiagramUploadRequest com content_type "image/webp"
    When o modelo é instanciado
    Then nenhuma exceção é lançada

  Scenario: Rejeita content_type application/pdf
    Given um DiagramUploadRequest com content_type "application/pdf"
    When o modelo é instanciado
    Then uma ValidationError é lançada com mensagem contendo "content_type must be one of"

  Scenario: Rejeita content_type text/plain
    Given um DiagramUploadRequest com content_type "text/plain"
    When o modelo é instanciado
    Then uma ValidationError é lançada

  Scenario: Rejeita content_type image/gif (não suportado)
    Given um DiagramUploadRequest com content_type "image/gif"
    When o modelo é instanciado
    Then uma ValidationError é lançada

Feature: Validação de Contratos — ArchitectureDiagram (Entity)

  Scenario: Transição válida PENDING → PROCESSING
    Given um diagrama com status "pending"
    When mark_processing() é chamado
    Then o status muda para "processing"

  Scenario: Transição inválida PENDING → COMPLETED é rejeitada
    Given um diagrama com status "pending"
    When mark_completed() é chamado diretamente
    Then uma ValueError é lançada com "Invalid status transition"

  Scenario: mark_completed sem report é rejeitado
    Given um diagrama com status "processing"
    When mark_completed(report="", elements=[]) é chamado
    Then uma ValueError é lançada com "analysis_report cannot be empty"
---------------------------------------------------------------------------
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

_SHARED_DIR = str(Path(__file__).resolve().parents[2] / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

from contracts.dto.diagram_upload import DiagramUploadRequest, ACCEPTED_CONTENT_TYPES
from contracts.events.analysis_requested import ArchitectureAnalysisRequestedEvent
from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus


# ===========================================================================
# DiagramUploadRequest — Validação de content_type
# ===========================================================================
class TestDiagramUploadRequestContentType:
    """Testes de contrato para validação de tipos MIME aceitos."""

    @pytest.mark.parametrize(
        "content_type",
        ["image/png", "image/jpeg", "image/jpg", "image/webp"],
        ids=["png", "jpeg", "jpg", "webp"],
    )
    def test_aceita_content_types_validos(self, content_type):
        """
        Given: content_type válido ({content_type})
        When:  DiagramUploadRequest é instanciado
        Then:  nenhuma exceção
        """
        dto = DiagramUploadRequest(
            user_id="user-abc-123",
            file_name="architecture.png",
            content_type=content_type,
        )
        assert dto.content_type == content_type

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/pdf",
            "text/plain",
            "image/gif",
            "image/svg+xml",
            "image/bmp",
            "application/octet-stream",
            "",
        ],
        ids=["pdf", "text", "gif", "svg", "bmp", "octet-stream", "empty"],
    )
    def test_rejeita_content_types_invalidos(self, content_type):
        """
        Given: content_type inválido ({content_type})
        When:  DiagramUploadRequest é instanciado
        Then:  ValidationError com mensagem explicativa
        """
        with pytest.raises(ValidationError) as exc_info:
            DiagramUploadRequest(
                user_id="user-abc-123",
                file_name="architecture.gif",
                content_type=content_type,
            )
        assert "content_type must be one of" in str(exc_info.value)

    def test_conjunto_completo_de_tipos_aceitos(self):
        """Garante que a constante ACCEPTED_CONTENT_TYPES é exatamente o esperado."""
        expected = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
        assert ACCEPTED_CONTENT_TYPES == expected

    def test_user_id_obrigatorio(self):
        """user_id não pode ser omitido."""
        with pytest.raises(ValidationError):
            DiagramUploadRequest(
                file_name="test.png",
                content_type="image/png",
            )

    def test_file_name_obrigatorio(self):
        """file_name não pode ser omitido."""
        with pytest.raises(ValidationError):
            DiagramUploadRequest(
                user_id="user-abc-123",
                content_type="image/png",
            )


# ===========================================================================
# ArchitectureAnalysisRequestedEvent — Contrato do evento SQS
# ===========================================================================
class TestAnalysisRequestedEventContrato:
    """Contrato do evento publicado pelo order-handler no SQS."""

    def test_campos_obrigatorios(self):
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="my-bucket",
            s3_key="diagrams/user/uuid",
            user_id="user-abc-123",
            requested_at=datetime.now(timezone.utc),
        )
        assert event.diagram_id is not None  # auto-gerado
        assert event.metadata == {}

    def test_metadata_opcional(self):
        event = ArchitectureAnalysisRequestedEvent(
            s3_bucket="my-bucket",
            s3_key="diagrams/user/uuid",
            user_id="user-abc-123",
            requested_at=datetime.now(timezone.utc),
            metadata={"source": "api-gateway"},
        )
        assert event.metadata["source"] == "api-gateway"

    def test_serializacao_json_round_trip(self):
        original = ArchitectureAnalysisRequestedEvent(
            s3_bucket="my-bucket",
            s3_key="diagrams/user/uuid",
            user_id="user-abc-123",
            requested_at=datetime.now(timezone.utc),
        )
        json_str = original.model_dump_json()
        restored = ArchitectureAnalysisRequestedEvent.model_validate_json(json_str)
        assert restored.diagram_id == original.diagram_id
        assert restored.s3_bucket == original.s3_bucket


# ===========================================================================
# ArchitectureDiagram — Máquina de estados (transições válidas)
# ===========================================================================
class TestArchitectureDiagramTransicoes:
    """Testes de contrato para a máquina de estados da entidade."""

    def _make_diagram(self, status: DiagramStatus = DiagramStatus.PENDING):
        d = ArchitectureDiagram(
            s3_key="diagrams/user/uuid",
            s3_bucket="bucket",
            user_id="user-abc-123",
        )
        if status == DiagramStatus.PROCESSING:
            d.mark_processing()
        return d

    def test_pending_para_processing_valido(self):
        d = self._make_diagram(DiagramStatus.PENDING)
        d.mark_processing()
        assert d.status == DiagramStatus.PROCESSING

    def test_processing_para_completed_valido(self):
        d = self._make_diagram(DiagramStatus.PROCESSING)
        d.mark_completed("report", ["lambda"])
        assert d.status == DiagramStatus.COMPLETED

    def test_processing_para_failed_valido(self):
        d = self._make_diagram(DiagramStatus.PROCESSING)
        d.mark_failed("erro qualquer")
        assert d.status == DiagramStatus.FAILED

    def test_pending_para_completed_invalido(self):
        d = self._make_diagram(DiagramStatus.PENDING)
        with pytest.raises(ValueError, match="Invalid status transition"):
            d.mark_completed("report", ["lambda"])

    def test_pending_para_failed_invalido(self):
        d = self._make_diagram(DiagramStatus.PENDING)
        with pytest.raises(ValueError, match="Invalid status transition"):
            d.mark_failed("erro")

    def test_completed_para_processing_invalido(self):
        d = self._make_diagram(DiagramStatus.PROCESSING)
        d.mark_completed("report", ["lambda"])
        with pytest.raises(ValueError, match="Invalid status transition"):
            d.mark_processing()

    def test_completed_sem_report_invalido(self):
        d = self._make_diagram(DiagramStatus.PROCESSING)
        with pytest.raises(ValueError, match="analysis_report cannot be empty"):
            d.mark_completed("", ["lambda"])

    def test_mark_failed_limpa_report_e_elements(self):
        d = self._make_diagram(DiagramStatus.PROCESSING)
        d.mark_failed("timeout")
        assert d.analysis_report is None
        assert d.elements_detected == []
