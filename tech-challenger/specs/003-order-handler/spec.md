# Spec: 003 — Order Handler Lambda

## Context
O usuário solicita análise de um diagrama de arquitetura via API Gateway. O Lambda `order-handler` é o ponto de entrada: recebe a imagem, persiste no S3, registra o pedido no DynamoDB e publica o evento SQS para processamento assíncrono.

## Problem Statement
Precisamos de uma função Lambda que:
1. Valide a requisição (content-type, user-id, body)
2. Salve a imagem no S3
3. Crie e persista uma entidade `ArchitectureDiagram` no DynamoDB
4. Publique um `ArchitectureAnalysisRequestedEvent` na fila SQS
5. Retorne 202 Accepted com o `diagram_id`

## Acceptance Criteria

### AC-1: Upload de imagem aceito
- POST com body base64 + `Content-Type: image/png|jpeg|jpg|webp` + `x-user-id` header
- Resposta `202` com `{ "diagram_id": "<uuid>", "status": "pending" }`

### AC-2: Validação de content-type
- Content-Type diferente dos aceitos → `400 Bad Request`

### AC-3: Validação de user-id
- Ausência do header `x-user-id` → `400 Bad Request`

### AC-4: Validação de body
- Body nulo ou vazio → `400 Bad Request`

### AC-5: Tratamento de erros internos
- Exceção não tratada no use case → `500 Internal Server Error` (sem vazar stack trace para o cliente)

## Out of Scope
- Autenticação/autorização (responsabilidade do API Gateway)
- Validação de conteúdo da imagem (responsabilidade do worker)

## Technical Design

### Fluxo
```
API Gateway Event
  → lambda_handler (handler.py)
    → validação (content-type, user-id, body)
    → ProcessDiagramUploadUseCase.execute(image_data, content_type, user_id)
      → S3Client.upload_file(image_data, s3_key, content_type)
      → SQSClient.send_message(ArchitectureAnalysisRequestedEvent)
      → DynamoDBDiagramRepository.save(ArchitectureDiagram)
    → return 202 { diagram_id, status }
```

### Module Structure
```
services/lambda-functions/order-handler/
├── handler.py          # Lambda entry point
├── use_cases.py        # ProcessDiagramUploadUseCase
├── repositories.py     # DynamoDBDiagramRepository + DiagramNotFoundError
├── config.py           # Env var config
└── requirements.txt
```

### S3 Key Pattern
`diagrams/{user_id}/{diagram_id}`

### Environment Variables
| Var | Description |
|-----|-------------|
| `S3_BUCKET` | Bucket para armazenar imagens |
| `SQS_QUEUE_URL` | URL da fila SQS de análise |
| `DYNAMODB_TABLE` | Nome da tabela DynamoDB |
| `AWS_REGION` | Região AWS (default: `us-east-1`) |

## Dependencies
- `shared/contracts` — `ArchitectureDiagram`, `ArchitectureAnalysisRequestedEvent`
- `shared/libs` — `S3Client`, `SQSClient`

## Test Command
```powershell
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\lambda-functions\order-handler"
python -m pytest tests\unit\lambda_functions\order_handler\ -v --no-cov -p no:cacheprovider
```
