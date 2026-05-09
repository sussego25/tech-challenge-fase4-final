import base64
import json

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

import handler as h
from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus


def _make_event(
    body: bytes = b"fake-image-data",
    content_type: str = "image/png",
    user_id: str = "user-123",
    is_base64: bool = True,
) -> dict:
    return {
        "httpMethod": "POST",
        "isBase64Encoded": is_base64,
        "body": base64.b64encode(body).decode() if is_base64 else body.decode(),
        "headers": {
            "content-type": content_type,
            "x-user-id": user_id,
        },
    }


@pytest.fixture(autouse=True)
def reset_use_case():
    original = h._use_case
    yield
    h._use_case = original


class TestHandlerSuccess:
    def test_returns_202_with_diagram_id_on_success(self):
        diagram = ArchitectureDiagram(
            s3_key="diagrams/user-123/abc",
            s3_bucket="my-bucket",
            user_id="user-123",
        )
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = diagram
        h._use_case = mock_use_case

        response = h.lambda_handler(_make_event(), None)

        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["diagram_id"] == str(diagram.diagram_id)
        assert body["status"] == DiagramStatus.PENDING.value

    def test_use_case_called_with_correct_args(self):
        diagram = ArchitectureDiagram(
            s3_key="diagrams/user-123/abc",
            s3_bucket="my-bucket",
            user_id="user-123",
        )
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = diagram
        h._use_case = mock_use_case

        h.lambda_handler(_make_event(body=b"imgdata", content_type="image/jpeg", user_id="u-99"), None)

        mock_use_case.execute.assert_called_once_with(b"imgdata", "image/jpeg", "u-99")


class TestHandlerValidation:
    def test_returns_400_when_body_is_missing(self):
        event = _make_event()
        event["body"] = None
        response = h.lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_returns_400_when_body_is_empty_string(self):
        event = _make_event()
        event["body"] = ""
        response = h.lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_returns_400_when_content_type_not_accepted(self):
        response = h.lambda_handler(_make_event(content_type="application/pdf"), None)
        assert response["statusCode"] == 400

    def test_returns_400_when_content_type_is_missing(self):
        event = _make_event()
        del event["headers"]["content-type"]
        response = h.lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_returns_400_when_user_id_header_missing(self):
        event = _make_event()
        del event["headers"]["x-user-id"]
        response = h.lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_returns_400_when_user_id_header_is_empty(self):
        response = h.lambda_handler(_make_event(user_id="  "), None)
        assert response["statusCode"] == 400


class TestHandlerErrors:
    def test_returns_500_when_use_case_raises(self):
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = RuntimeError("unexpected error")
        h._use_case = mock_use_case

        response = h.lambda_handler(_make_event(), None)

        assert response["statusCode"] == 500

    def test_error_response_does_not_leak_internal_message(self):
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("db connection refused at 10.0.0.1:5432")
        h._use_case = mock_use_case

        response = h.lambda_handler(_make_event(), None)
        body = json.loads(response["body"])

        assert "10.0.0.1" not in body.get("error", "")
        assert response["statusCode"] == 500
