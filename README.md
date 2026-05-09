# Tech-Challenge-fase-4

![alt text](image.png)

## Visão Geral

O projeto é um **analisador de diagramas de arquitetura** baseado em microsserviços. O usuário faz upload de uma imagem de diagrama diretamente no S3, o evento aciona automaticamente uma Lambda que inicia o pipeline de análise assíncrona dos componentes. A análise retorna um relatório textual com os elementos detectados no diagrama.

> **Nota:** A análise de componentes atualmente retorna dados mockados. A integração com YOLO (detecção visual de componentes) + LLM (descrição textual) está planejada para uma fase futura.

---

## Fluxo Completo de Dados teste




```
[Usuário]
    │  PUT objeto no S3 (prefixo: diagrams/)
    ▼
[S3 Event Notification]
    ▼
[order-handler] ← Lambda AWS (trigger: s3:ObjectCreated:*)
    │  1. Lê bucket e key do evento S3
    │  2. Verifica existência do objeto via head_object
    │  3. Cria ArchitectureDiagram no DynamoDB (status=PENDING)
    │  4. Publica ArchitectureAnalysisRequestedEvent → SQS
    ▼
[SQS Queue]
    ▼
[worker-service] ← Serviço long-running (container/EKS)
    │  1. Consome evento do SQS
    │  2. Atualiza DynamoDB: PENDING → PROCESSING
    │  3. Baixa imagem do S3
    │  4. Executa AnalysisService (mock) → relatório + elementos detectados
    │  5. Atualiza DynamoDB: PROCESSING → COMPLETED (ou FAILED)
    │  6. Publica ArchitectureAnalysisCompletedEvent → Kafka
    │  7. Deleta mensagem do SQS
    ▼
[Kafka Topic: analysis-completed]
    ▼
[notification-service] ← Serviço long-running (container/EKS)
    │  1. Consome evento do Kafka
    │  2. Formata mensagem de notificação
    │  3. Envia notificação (via NotificationSender — logging atualmente)
    │  4. Salva Notification no DynamoDB (status=SENT ou FAILED)
```

---

## Interações entre Recursos AWS

```
S3 (upload do usuário)
    └── S3 Event Notification → order-handler (Lambda)
                                    │
                                    ├── S3          (verifica existência do objeto)
                                    ├── DynamoDB    (cria registro PENDING)
                                    └── SQS         (enfileira evento de análise)

SQS → worker-service (EKS container)
          │
          ├── S3          (baixa imagem)
          ├── DynamoDB    (atualiza status)
          ├── Kafka        (publica resultado)
          └── SQS          (deleta mensagem processada)

Kafka → notification-service (EKS container)
            │
            └── DynamoDB    (salva registro de notificação)
```

---

## Módulos Implementados

### `shared/contracts` — Contratos compartilhados

| Arquivo | Descrição |
|---|---|
| `entities/architecture_diagram.py` | Entidade `ArchitectureDiagram` com máquina de estados (`PENDING → PROCESSING → COMPLETED/FAILED`). Campos: `diagram_id`, `s3_bucket`, `s3_key`, `status`, `created_at`, `updated_at`, `analysis_report`, `elements_detected` |
| `events/analysis_requested.py` | Evento `ArchitectureAnalysisRequestedEvent` — publicado pelo order-handler no SQS. Campos: `diagram_id`, `s3_bucket`, `s3_key`, `requested_at`, `metadata` |
| `events/analysis_completed.py` | Evento `ArchitectureAnalysisCompletedEvent` — publicado pelo worker no Kafka. Campos: `diagram_id`, `status`, `analysis_report`, `elements_detected`, `completed_at`, `error_message` |
| `dto/diagram_upload.py` | DTO `DiagramUploadRequest` — valida content-types aceitos (png, jpeg, jpg, webp) |
| `dto/analysis_status.py` | DTO `AnalysisStatusResponse` — resposta de consulta de status |

### `shared/libs` — Clientes reutilizáveis

| Arquivo | Descrição |
|---|---|
| `aws/s3_client.py` | `S3Client` — upload e download de arquivos no S3 via boto3 |
| `aws/sqs_client.py` | `SQSClient` — send, receive (long polling 20s) e delete de mensagens SQS |
| `llm/sagemaker_client.py` | `LLMClient` — cliente SageMaker (reservado para integração futura YOLO+LLM) |
| `messaging/kafka_producer.py` | `KafkaProducer` — publica mensagens Kafka via `confluent_kafka` |
| `messaging/kafka_consumer.py` | `KafkaConsumer` — consome Kafka em loop infinito com handler callback |

### `services/lambda-functions/order-handler` — Ponto de entrada

Arquitetura: **Lambda AWS acionada por evento S3**

| Arquivo | Descrição |
|---|---|
| `handler.py` | Entry point Lambda. Lê `bucket` e `key` do evento S3 (`event["Records"]`), verifica o objeto via `head_object`, aciona o use case |
| `use_cases.py` | `ProcessDiagramUploadUseCase` — cria `ArchitectureDiagram`, publica no SQS e salva no DynamoDB |
| `repositories.py` | `DynamoDBDiagramRepository` — persiste e recupera `ArchitectureDiagram` do DynamoDB |
| `config.py` | Lê `S3_BUCKET`, `SQS_QUEUE_URL`, `DYNAMODB_TABLE`, `AWS_REGION` de variáveis de ambiente |

### `services/worker-service` — Processador assíncrono

Arquitetura: **Hexagonal**, serviço long-running em container

| Arquivo | Descrição |
|---|---|
| `consumers/sqs_consumer.py` | `SQSConsumer` — loop infinito, busca batches de 10 msgs, deleta após sucesso |
| `processors/diagram_processor.py` | `DiagramProcessor` — orquestra: get repo → mark_processing → download S3 → análise → mark_completed/failed → save → publicar Kafka |
| `domain/analysis_service.py` | `AnalysisService` — **mock**: retorna relatório e elementos detectados fixos. TODO: integrar YOLO + LLM |
| `infrastructure/diagram_repository.py` | DynamoDB para `ArchitectureDiagram` |
| `infrastructure/kafka_publisher.py` | `KafkaPublisher` — publica `ArchitectureAnalysisCompletedEvent` no tópico Kafka |
| `jobs/worker.py` | `main()` — instancia dependências e inicia o `SQSConsumer` |

### `services/notification-service` — Notificador

Arquitetura: **Hexagonal**, serviço long-running em container

| Arquivo | Descrição |
|---|---|
| `messaging/kafka_consumer.py` | `KafkaAnalysisConsumer` — consome tópico `analysis-completed`, valida payload, delega ao use case |
| `application/notify_use_case.py` | `NotifyAnalysisCompletedUseCase` — formata mensagem para `completed` vs `failed`, chama sender, salva no DynamoDB |
| `domain/notification.py` | Entidade `Notification` com estados `PENDING → SENT/FAILED` |
| `infrastructure/notification_repository.py` | DynamoDB para `Notification` |
| `infrastructure/notification_sender.py` | Sender atual baseado em logging (SES/email a integrar) |
| `main.py` | Entry point do serviço |

---

## Cobertura de Testes

Testes unitários cobrindo:

- `shared/contracts` — entidades, eventos e DTOs
- `shared/libs` — S3, SQS, Kafka e SageMaker clients
- `order-handler` — handler, use cases e repositório
- `worker-service` — SQS consumer, diagram processor, analysis service, Kafka publisher e repositório
- `notification-service` — Kafka consumer, use case, entidade Notification e repositório

### Comandos para rodar os testes

```powershell
# Shared contracts e libs
cd tech-challenger
$env:PYTHONPATH = ".\shared"
python -m pytest tests\unit\shared\ -v

# Order Handler (Lambda)
$env:PYTHONPATH = ".\shared;.\services\lambda-functions\order-handler"
python -m pytest tests\unit\lambda_functions\ -v

# Worker Service
$env:PYTHONPATH = ".\shared;.\services\worker-service\src"
python -m pytest tests\unit\worker_service\ -v

# Notification Service
$env:PYTHONPATH = ".\shared;.\services\notification-service\src"
python -m pytest tests\unit\notification_service\ -v
```

---

## Infraestrutura AWS (Terraform)

Todos os recursos são gerenciados via Terraform com backend remoto no S3 (`tech-challenger-tfstate-325066546876`), região `us-east-1`, ambiente `prod`.

### Recursos provisionados

| Módulo | Recurso | Status |
|---|---|---|
| `s3` | Bucket `tech-challenger-diagrams-prod-*` | ✅ Ativo |
| `dynamodb` | Tabela `diagrams` (hash_key: `diagram_id`) | ✅ Ativo |
| `dynamodb` | Tabela `notifications` (GSI: `diagram-notifications-index`) | ✅ Ativo |
| `sqs` | Fila `architecture-analysis-queue-prod` + DLQ | ✅ Ativo |
| `lambda` | Função `tech-challenger-order-handler-prod` | ✅ Ativo |
| `lambda` | Permission para S3 invocar a Lambda | ✅ Ativo |
| `s3` | S3 Bucket Notification → Lambda (prefixo: `diagrams/`) | ✅ Ativo |
| `networking` | VPC, subnets públicas/privadas, NAT Gateway | ✅ Ativo |
| `eks` | Cluster EKS + node group `t3.small` (desired=1) | ✅ Ativo |
| `kafka` | MSK 2x `kafka.t3.small` | ✅ Ativo |
| `sagemaker` | Endpoint SageMaker | ❌ Desabilitado |

### Comandos Terraform

```powershell
cd tech-challenger\infra\terraform
terraform init
terraform plan
terraform apply
# Para destruir tudo:
terraform destroy
```

---

## Variáveis de Ambiente

### order-handler (Lambda)

| Variável | Descrição |
|---|---|
| `S3_BUCKET` | Nome do bucket S3 para armazenar imagens |
| `SQS_QUEUE_URL` | URL da fila SQS de análise |
| `DYNAMODB_TABLE` | Nome da tabela DynamoDB de diagramas |
| `AWS_REGION` | Região AWS (padrão: `us-east-1`) |

### worker-service

| Variável | Descrição |
|---|---|
| `S3_BUCKET` | Nome do bucket S3 |
| `SQS_QUEUE_URL` | URL da fila SQS |
| `DYNAMODB_TABLE` | Nome da tabela DynamoDB de diagramas |
| `KAFKA_BOOTSTRAP_SERVERS` | Endereço dos brokers Kafka/MSK |
| `KAFKA_TOPIC_ANALYSIS_COMPLETED` | Tópico Kafka de resultados (padrão: `analysis-completed`) |
| `LLM_PROVIDER` | Provedor de LLM: `sagemaker` ou `bedrock` |
| `SAGEMAKER_ENDPOINT` | Nome do endpoint SageMaker (usado com `LLM_PROVIDER=sagemaker`) |
| `BEDROCK_MODEL_ID` | Modelo Bedrock (usado com `LLM_PROVIDER=bedrock`) |
| `AWS_REGION` | Região AWS (padrão: `us-east-1`) |

### Destruição segura da infraestrutura

O repo já contém um workflow para destruir tudo: `.github/workflows/destroy.yml`.

Esse workflow exige dois inputs:
- `destroy: true`
- `confirmation: DESTRUIR`

No GitHub Actions UI, escolha o workflow `Destroy Infrastructure (DESTRUIR TUDO)` e defina:
- `destroy` = `true`
- `confirmation` = `DESTRUIR`

Se preferir rodar localmente, use o script na raiz:

```powershell
.\destroy-all.ps1
```

Ele faz:
- confirmação manual (`DESTRUIR`)
- `terraform init`
- `terraform destroy -auto-approve -var="environment=prod"`

> Mantenha qualquer bucket de estado remoto fora da destruição automática para não perder o histórico de estado se quiser redeploy depois.

### notification-service

| Variável | Descrição |
|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | Endereço dos brokers Kafka/MSK |
| `KAFKA_TOPIC_ANALYSIS_COMPLETED` | Tópico Kafka consumido (padrão: `analysis-completed`) |
| `KAFKA_GROUP_ID` | Consumer group ID (padrão: `notification-service`) |
| `DYNAMODB_TABLE` | Nome da tabela DynamoDB de notificações |
| `AWS_REGION` | Região AWS (padrão: `us-east-1`) |

---

## Pendências / Trabalho Futuro

- `AnalysisService` — integrar YOLO (detecção visual de componentes) + LLM (descrição textual) via SageMaker
- `NotificationSender` — integração com SES/e-mail pendente
- `lambda-functions/notification-handler/` e `sagemaker-handler/` — não implementados
