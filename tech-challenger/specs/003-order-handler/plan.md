# Plan: 003 — Order Handler Lambda

## Objective
Implementar a função Lambda `order-handler`, ponto de entrada da API para upload de diagramas de arquitetura.

## Architecture Decisions
- Lambda como entry point HTTP via API Gateway v2
- Body em base64 (padrão API Gateway para conteúdo binário) ou raw string
- `_use_case` como variável de módulo (singleton warm-start) + injetável em testes
- Sem autenticação na Lambda — responsabilidade do API Gateway
- Erros internos retornam `500` genérico sem vazar detalhes (OWASP)

## Flow
```
API Gateway → lambda_handler
  ├─ Validate headers (x-user-id, content-type)
  ├─ Validate + decode body (base64)
  └─ ProcessDiagramUploadUseCase.execute()
       ├─ S3Client.upload_file(image_data, s3_key)
       ├─ SQSClient.send_message(ArchitectureAnalysisRequestedEvent)
       └─ DynamoDBDiagramRepository.save(ArchitectureDiagram)
  → 202 { diagram_id, status: "pending" }
```

## Module Structure
```
services/lambda-functions/order-handler/
├── handler.py       # Lambda entry: lambda_handler(event, context)
├── use_cases.py     # ProcessDiagramUploadUseCase
├── repositories.py  # DynamoDBDiagramRepository + DiagramNotFoundError
├── config.py        # Env var Config
└── requirements.txt
```

## Environment Variables
| Var | Description |
|-----|-------------|
| `S3_BUCKET` | Bucket para imagens |
| `SQS_QUEUE_URL` | URL da fila SQS |
| `DYNAMODB_TABLE` | Tabela DynamoDB |
| `AWS_REGION` | Região (default: `us-east-1`) |

## Dependencies
- `shared/contracts` — `ArchitectureDiagram`, `ArchitectureAnalysisRequestedEvent`
- `shared/libs/aws` — `S3Client`, `SQSClient`

## Test Run
```powershell
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\lambda-functions\order-handler"
python -m pytest tests\unit\lambda_functions\order_handler\ -v --no-cov
```
