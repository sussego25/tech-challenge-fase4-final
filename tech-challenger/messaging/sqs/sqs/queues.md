# SQS Queues

## Visão Geral

O projeto utiliza Amazon SQS (Simple Queue Service) para processamento assíncrono de mensagens entre serviços.

## Filas Implementadas

### 1. Architecture Analysis Queue
- **Nome**: `tech-challenger-architecture-analysis-queue-{environment}`
- **Propósito**: Receber requisições de análise de diagramas (Yolo + LLM)
- **Produtores**: Lambda (API Gateway) → Order Service
- **Consumidores**: Worker Service
- **DLQ**: `tech-challenger-architecture-analysis-dlq-{environment}`
- **Retry**: 3 tentativas antes de enviar para DLQ
- **Timeout**: 5 minutos
- **Retenção**: 14 dias

## Fluxo de Mensagens

```
API Gateway (Diagrama)
  ↓
Lambda Publisher
  ↓
architecture-analysis-queue
  ↓
Worker Service Consumer
  ↓
Processamento (Yolo + LLM)
  ↓
DynamoDB (status, elementos e relatório)
```

## Dead Letter Queues (DLQ)

- Mensagens que falham após 3 tentativas são movidas automaticamente para DLQ
- Use DLQ para monitoramento e debugging de falhas
- CloudWatch alarms devem ser configuradas para DLQs não vazias
