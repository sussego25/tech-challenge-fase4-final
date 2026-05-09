# Spec: 004 — Worker Service

## Context
O `worker-service` é o núcleo de processamento assíncrono. Consome eventos SQS do `order-handler`, executa a análise do diagrama via LLM (SageMaker), atualiza o DynamoDB e publica o resultado no Kafka para o `notification-service`.

## Problem Statement
Precisamos de um serviço long-running que:
1. Consumir `ArchitectureAnalysisRequestedEvent` do SQS
2. Baixar a imagem do S3
3. Invocar análise via LLM (SageMaker)
4. Atualizar o status do `ArchitectureDiagram` no DynamoDB
5. Publicar `ArchitectureAnalysisCompletedEvent` no Kafka
6. Deletar a mensagem processada do SQS

## Acceptance Criteria

### AC-1: Processamento bem-sucedido
- Diagrama no DynamoDB atualizado para `completed`
- `ArchitectureAnalysisCompletedEvent(status=completed, analysis_report=..., elements_detected=[...])` publicado no Kafka
- Mensagem deletada do SQS

### AC-2: Falha de análise (LLM indisponível)
- Diagrama no DynamoDB atualizado para `failed`
- `ArchitectureAnalysisCompletedEvent(status=failed, error_message=...)` publicado no Kafka
- Mensagem deletada do SQS (não re-processar)

### AC-3: Mensagem inválida no SQS
- Mensagem com JSON inválido → log de erro, sem crash, mensagem NÃO deletada

### AC-4: Ciclo de vida do diagrama
- Estado PENDING → PROCESSING antes da análise
- Estado PROCESSING → COMPLETED ou FAILED após análise

## Technical Design

### Hexagonal Architecture
```
consumers/ (driving)         domain/                infrastructure/ (driven)
  SQSConsumer                  AnalysisService          DiagramRepository
       ↓                           ↓                     KafkaPublisher
  processors/
  DiagramProcessor
```

### Flow
```
SQSConsumer._process_batch()
  → parse ArchitectureAnalysisRequestedEvent
  → DiagramProcessor.process(event)
    → DiagramRepository.get(diagram_id)
    → diagram.mark_processing() → DiagramRepository.save()
    → S3Client.download_file(s3_key)
    → AnalysisService.analyze(image_data, diagram_id) → (report, elements)
    → diagram.mark_completed(report, elements) OR mark_failed(error)
    → DiagramRepository.save()
    → KafkaPublisher.publish_analysis_completed(event)
  → SQSClient.delete_message(receipt_handle)
```

### Module Structure
```
services/worker-service/src/
├── config/settings.py
├── consumers/sqs_consumer.py
├── domain/
│   ├── analysis_service.py
│   └── exceptions.py
├── infrastructure/
│   ├── diagram_repository.py
│   └── kafka_publisher.py
├── jobs/worker.py
└── processors/diagram_processor.py
```

## Dependencies
- `shared/contracts` — all events + `ArchitectureDiagram`
- `shared/libs/aws` — `S3Client`, `SQSClient`
- `shared/libs/messaging` — `KafkaProducer`
- `shared/libs/llm` — `LLMClient`

## Test Command
```powershell
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\worker-service\src"
python -m pytest tests\unit\worker_service\ -v --no-cov -p no:cacheprovider
```
