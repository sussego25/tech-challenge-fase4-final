"""
===========================================================================
Testes de Infraestrutura com LocalStack — S3 + DynamoDB
===========================================================================

Cenários Gherkin:
---------------------------------------------------------------------------
Feature: Repositório DynamoDB com LocalStack

  Scenario: Salvar e recuperar diagrama no DynamoDB local
    Given uma tabela DynamoDB "test-diagrams" criada no LocalStack
      And um ArchitectureDiagram com status "pending"
    When o DynamoDBDiagramRepository.save() é chamado
      And o DynamoDBDiagramRepository.get() é chamado com o mesmo diagram_id
    Then o diagrama retornado possui os mesmos dados do original
      And o status é "pending"

  Scenario: Atualizar status do diagrama para COMPLETED
    Given um diagrama salvo com status "pending" no DynamoDB local
    When o diagrama é marcado como "processing" e depois "completed" com relatório
      And o DynamoDBDiagramRepository.save() é chamado novamente
      And o DynamoDBDiagramRepository.get() é chamado
    Then o status retornado é "completed"
      And o analysis_report contém o relatório salvo
      And elements_detected contém os elementos salvos

  Scenario: Buscar diagrama inexistente lança DiagramNotFoundError
    Given uma tabela DynamoDB vazia no LocalStack
    When o DynamoDBDiagramRepository.get() é chamado com um id inexistente
    Then DiagramNotFoundError é lançado

Feature: Upload e Download de imagem no S3 com LocalStack

  Scenario: Upload e download de imagem PNG
    Given um bucket S3 "test-diagrams" criado no LocalStack
      And uma imagem PNG de 72 bytes
    When a imagem é enviada via S3Client.upload_file()
      And a imagem é recuperada via S3Client.download_file()
    Then os bytes retornados são idênticos aos enviados

  Scenario: Download de arquivo inexistente lança S3NotFoundError
    Given um bucket S3 vazio no LocalStack
    When S3Client.download_file() é chamado com uma chave inexistente
    Then S3NotFoundError é lançado
---------------------------------------------------------------------------

Pré-requisitos:
  pip install boto3 moto pytest pydantic

Nota: Este módulo usa `moto` para simular LocalStack sem dependência
      de um container Docker rodando. Para testes com LocalStack real,
      substituir o endpoint_url por "http://localhost:4566".
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import boto3
import os
import pytest

from moto import mock_aws

_SHARED_DIR = str(Path(__file__).resolve().parents[2] / "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

_ORDER_HANDLER_DIR = str(
    Path(__file__).resolve().parents[2]
    / "services"
    / "lambda-functions"
    / "order-handler"
)
if _ORDER_HANDLER_DIR not in sys.path:
    sys.path.insert(0, _ORDER_HANDLER_DIR)

from contracts.entities.architecture_diagram import ArchitectureDiagram, DiagramStatus


# ===========================================================================
# Constantes
# ===========================================================================
TABLE_NAME = "test-diagrams"
BUCKET_NAME = "test-diagrams-bucket"
REGION = "us-east-1"


# ===========================================================================
# Helpers
# ===========================================================================
def _create_dynamodb_table():
    """Cria a tabela DynamoDB no moto."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[{"AttributeName": "diagram_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "diagram_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user-diagrams-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        },
    )
    table.wait_until_exists()
    return table


def _create_s3_bucket():
    """Cria o bucket S3 no moto."""
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET_NAME)
    return s3


def _make_diagram():
    return ArchitectureDiagram(
        diagram_id=uuid4(),
        s3_key="diagrams/user-abc-123/test-uuid",
        s3_bucket=BUCKET_NAME,
        user_id="user-abc-123",
    )


SAMPLE_IMAGE = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# ===========================================================================
# Testes — DynamoDBDiagramRepository com LocalStack/Moto
# ===========================================================================
@pytest.fixture(autouse=True)
def _fake_aws_creds(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


class TestDynamoDBDiagramRepositoryLocalStack:

    @mock_aws
    def test_salvar_e_recuperar_diagrama(self):
        """
        Given: tabela DynamoDB criada + diagrama PENDING
        When:  save() + get()
        Then:  dados recuperados são idênticos
        """
        from repositories import DynamoDBDiagramRepository

        table = _create_dynamodb_table()
        repo = DynamoDBDiagramRepository(table=table)
        diagram = _make_diagram()

        repo.save(diagram)
        recovered = repo.get(str(diagram.diagram_id))

        assert recovered.diagram_id == diagram.diagram_id
        assert recovered.user_id == diagram.user_id
        assert recovered.status == DiagramStatus.PENDING
        assert recovered.s3_key == diagram.s3_key
        assert recovered.s3_bucket == diagram.s3_bucket
        assert recovered.elements_detected == []
        assert recovered.analysis_report is None

    @mock_aws
    def test_atualizar_status_para_completed(self):
        """
        Given: diagrama PENDING salvo
        When:  mark_processing → mark_completed → save → get
        Then:  status=COMPLETED + report + elements
        """
        from repositories import DynamoDBDiagramRepository

        table = _create_dynamodb_table()
        repo = DynamoDBDiagramRepository(table=table)
        diagram = _make_diagram()
        repo.save(diagram)

        diagram.mark_processing()
        diagram.mark_completed(
            report="API Gateway, Lambda e DynamoDB detectados",
            elements=["api_gateway", "lambda", "dynamodb"],
        )
        repo.save(diagram)

        recovered = repo.get(str(diagram.diagram_id))

        assert recovered.status == DiagramStatus.COMPLETED
        assert "API Gateway" in recovered.analysis_report
        assert "lambda" in recovered.elements_detected
        assert len(recovered.elements_detected) == 3

    @mock_aws
    def test_diagrama_inexistente_lanca_not_found(self):
        """
        Given: tabela vazia
        When:  get() com id inexistente
        Then:  DiagramNotFoundError
        """
        from repositories import DynamoDBDiagramRepository, DiagramNotFoundError

        table = _create_dynamodb_table()
        repo = DynamoDBDiagramRepository(table=table)

        with pytest.raises(DiagramNotFoundError):
            repo.get(str(uuid4()))

    @mock_aws
    def test_multiplos_diagramas_isolados(self):
        """
        Given: dois diagramas de usuários distintos
        When:  save ambos + get individual
        Then:  cada um retorna dados corretos
        """
        from repositories import DynamoDBDiagramRepository

        table = _create_dynamodb_table()
        repo = DynamoDBDiagramRepository(table=table)

        d1 = ArchitectureDiagram(
            s3_key="diagrams/user1/uuid1",
            s3_bucket=BUCKET_NAME,
            user_id="user-1",
        )
        d2 = ArchitectureDiagram(
            s3_key="diagrams/user2/uuid2",
            s3_bucket=BUCKET_NAME,
            user_id="user-2",
        )

        repo.save(d1)
        repo.save(d2)

        r1 = repo.get(str(d1.diagram_id))
        r2 = repo.get(str(d2.diagram_id))

        assert r1.user_id == "user-1"
        assert r2.user_id == "user-2"
        assert r1.diagram_id != r2.diagram_id


# ===========================================================================
# Testes — S3 com LocalStack/Moto
# ===========================================================================
class TestS3LocalStack:

    @mock_aws
    def test_upload_e_download_imagem(self):
        """
        Given: bucket S3 criado
        When:  upload PNG → download
        Then:  bytes idênticos
        """
        s3 = _create_s3_bucket()
        s3_key = "diagrams/user-abc-123/test-uuid"

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=SAMPLE_IMAGE,
            ContentType="image/png",
        )

        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        downloaded = response["Body"].read()

        assert downloaded == SAMPLE_IMAGE
        assert response["ContentType"] == "image/png"

    @mock_aws
    def test_download_inexistente_lanca_erro(self):
        """
        Given: bucket vazio
        When:  get_object com chave inexistente
        Then:  ClientError (NoSuchKey)
        """
        from botocore.exceptions import ClientError

        s3 = _create_s3_bucket()

        with pytest.raises(ClientError) as exc_info:
            s3.get_object(Bucket=BUCKET_NAME, Key="nonexistent/key.png")
        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    @mock_aws
    def test_upload_diferentes_content_types(self):
        """Testa upload com cada content_type aceito."""
        s3 = _create_s3_bucket()

        for ct in ["image/png", "image/jpeg", "image/webp"]:
            key = f"diagrams/user/test-{ct.replace('/', '-')}"
            s3.put_object(
                Bucket=BUCKET_NAME, Key=key, Body=SAMPLE_IMAGE, ContentType=ct
            )
            resp = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            assert resp["ContentType"] == ct
