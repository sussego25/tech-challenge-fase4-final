import base64
import io
import json
import os
from typing import Any, Dict
import numpy as np  # Adicione isso no topo
import torch
import os
from PIL import Image
from ultralytics import YOLO

MAX_IMAGE_SIZE = (640, 640)


def model_fn(model_dir: str) -> YOLO:
    model_path = os.path.join(model_dir, "modelo_arquitetura_fiap3.pt")
    model = YOLO(model_path)
    return model


def _prepare_image(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail(MAX_IMAGE_SIZE)
    return image


def input_fn(serialized_input_data: Any, content_type: str) -> Image.Image:
    # Garante que temos bytes para trabalhar, caso venha como string
    if isinstance(serialized_input_data, str):
        serialized_input_data = serialized_input_data.encode("utf-8")

    if content_type == "application/json":
        data = json.loads(serialized_input_data.decode("utf-8"))
        image_b64 = data.get("image_data") or data.get("image")
        if not image_b64:
            raise ValueError("JSON payload deve conter 'image_data' ou 'image'")
        image_bytes = base64.b64decode(image_b64)
        return _prepare_image(Image.open(io.BytesIO(image_bytes)))

    if content_type.startswith("image/"):
        return _prepare_image(Image.open(io.BytesIO(serialized_input_data)))

    raise ValueError(
        f"Content type '{content_type}' não suportado. Use 'image/png', 'image/jpeg' ou 'application/json'."
    )


def predict_fn(input_data: Image.Image, model: YOLO) -> Any:
    results = model.predict(source=input_data, imgsz=640, conf=0.25, save=False)

    output = []
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            class_id = int(box.cls[0])
            label = model.names[class_id]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])

            output.append(
                {
                    "class_id": class_id,
                    "label": label,
                    "confidence": confidence,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                }
            )

    return output


def output_fn(prediction: Any, accept: str = "application/json") -> bytes:
    if accept != "application/json":
        raise ValueError(
            f"Accept '{accept}' não suportado. Apenas 'application/json' está disponível."
        )

    return json.dumps({"predictions": prediction}).encode("utf-8")


# SageMaker script mode usa as funções acima automaticamente.
if __name__ == "__main__":
    print("Arquivo de inferência SageMaker para YOLO está pronto.")
