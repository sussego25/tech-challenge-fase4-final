import tarfile
from pathlib import Path

MODEL_FILE = Path("modelo_arquitetura_fiap3.pt")
INFERENCE_FILE = Path("inference.py")
REQUIREMENTS_FILE = Path("requirements.txt")
OUTPUT_FILE = Path("model.tar.gz")


def package_model() -> None:
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_FILE}")
    if not INFERENCE_FILE.exists():
        raise FileNotFoundError(f"Arquivo de inferência não encontrado: {INFERENCE_FILE}")
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Arquivo de dependências não encontrado: {REQUIREMENTS_FILE}")

    with tarfile.open(OUTPUT_FILE, "w:gz") as tar:
        tar.add(MODEL_FILE, arcname=MODEL_FILE.name)
        tar.add(INFERENCE_FILE, arcname=f"code/{INFERENCE_FILE.name}")
        tar.add(REQUIREMENTS_FILE, arcname=f"code/{REQUIREMENTS_FILE.name}")

    print(f"Pacote criado: {OUTPUT_FILE}")


if __name__ == "__main__":
    package_model()
