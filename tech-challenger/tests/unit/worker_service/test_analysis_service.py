import pytest
from unittest.mock import MagicMock

from domain.analysis_service import AnalysisService
from libs.llm.exceptions import LLMInvokeError


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.invoke.return_value = "The architecture has a service, database, and api gateway."
    return mock


class TestAnalysisServiceReport:
    def test_returns_report_from_llm(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        report, _ = svc.analyze(b"image", "diag-1")
        assert report == "The architecture has a service, database, and api gateway."

    def test_calls_llm_invoke_once(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        svc.analyze(b"image", "diag-1")
        mock_llm.invoke.assert_called_once()

    def test_prompt_includes_diagram_id(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        svc.analyze(b"image-bytes", "my-diagram-42")
        prompt = mock_llm.invoke.call_args[0][0]
        assert "my-diagram-42" in prompt

    def test_prompt_includes_json_schema_and_yolo_placeholder(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        svc.analyze(b"image-bytes", "my-diagram-42")
        prompt = mock_llm.invoke.call_args[0][0]
        assert "analise_componentes" in prompt
        assert "riscos_identificados" in prompt
        assert "recomendacoes_melhoria" in prompt
        assert "Componentes identificados pelo YOLO" in prompt

    def test_prompt_includes_actual_yolo_components_list(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        yolo_components = ["api_gateway", "lambda", "dynamodb"]
        svc.analyze(b"image-bytes", "my-diagram-42", yolo_components=yolo_components)
        prompt = mock_llm.invoke.call_args[0][0]
        assert '["api_gateway", "lambda", "dynamodb"]' in prompt
        assert "Componentes identificados pelo YOLO" in prompt

    def test_prompt_includes_well_architected_instructions(self, mock_llm):
        svc = AnalysisService(llm_client=mock_llm)
        svc.analyze(b"image-bytes", "my-diagram-42", yolo_components=["s3"])
        prompt = mock_llm.invoke.call_args[0][0]
        assert "AWS Well-Architected Framework" in prompt
        assert "Não invente serviços" in prompt
        assert '"analise_componentes": ["s3"]' in prompt


class TestAnalysisServiceElements:
    def test_extracts_service_keyword(self, mock_llm):
        mock_llm.invoke.return_value = "There is a service here."
        svc = AnalysisService(llm_client=mock_llm)
        _, elements = svc.analyze(b"img", "d")
        assert "service" in elements

    def test_extracts_multiple_elements(self, mock_llm):
        mock_llm.invoke.return_value = "service connects to database via api"
        svc = AnalysisService(llm_client=mock_llm)
        _, elements = svc.analyze(b"img", "d")
        assert "service" in elements
        assert "database" in elements
        assert "api" in elements

    def test_no_duplicate_elements(self, mock_llm):
        mock_llm.invoke.return_value = "service and service and service"
        svc = AnalysisService(llm_client=mock_llm)
        _, elements = svc.analyze(b"img", "d")
        assert elements.count("service") == 1

    def test_returns_empty_list_when_no_known_elements(self, mock_llm):
        mock_llm.invoke.return_value = "no known components mentioned here"
        svc = AnalysisService(llm_client=mock_llm)
        _, elements = svc.analyze(b"img", "d")
        assert isinstance(elements, list)


class TestAnalysisServiceErrors:
    def test_propagates_llm_invoke_error(self, mock_llm):
        mock_llm.invoke.side_effect = LLMInvokeError("endpoint unavailable")
        svc = AnalysisService(llm_client=mock_llm)
        with pytest.raises(LLMInvokeError):
            svc.analyze(b"img", "d")
