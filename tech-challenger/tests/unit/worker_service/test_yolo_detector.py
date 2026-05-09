import json
from unittest.mock import MagicMock

from infrastructure.yolo_detector import YoloDetector


def test_invokes_sagemaker_endpoint_with_image_data():
    boto_client = MagicMock()
    boto_client.invoke_endpoint.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b'{"predictions": []}'))
    }
    detector = YoloDetector(endpoint_name="yolo-endpoint", boto_client=boto_client)

    detector.detect_components(b"image-bytes")

    call_kwargs = boto_client.invoke_endpoint.call_args.kwargs
    assert call_kwargs["EndpointName"] == "yolo-endpoint"
    assert call_kwargs["ContentType"] == "application/json"
    assert call_kwargs["Accept"] == "application/json"
    payload = json.loads(call_kwargs["Body"].decode("utf-8"))
    assert "image_data" in payload


def test_returns_unique_prediction_labels_in_order():
    boto_client = MagicMock()
    body = {
        "predictions": [
            {"label": "lambda", "confidence": 0.91},
            {"label": "s3", "confidence": 0.88},
            {"label": "lambda", "confidence": 0.82},
        ]
    }
    boto_client.invoke_endpoint.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=json.dumps(body).encode("utf-8")))
    }
    detector = YoloDetector(endpoint_name="yolo-endpoint", boto_client=boto_client)

    assert detector.detect_components(b"image-bytes") == ["lambda", "s3"]
