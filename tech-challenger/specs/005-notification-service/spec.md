# Spec: 005 — Notification Service

## Context
O `notification-service` é o consumidor final do fluxo. Recebe `ArchitectureAnalysisCompletedEvent` via Kafka (publicado pelo worker-service), formata a notificação, envia ao usuário e persiste o registro no DynamoDB.

## Problem Statement
Precisamos de um serviço que:
1. Consuma `ArchitectureAnalysisCompletedEvent` do Kafka
2. Crie uma notificação formatada para o usuário
3. Envie a notificação (logging/SES na fase atual)
4. Persista o registro de notificação no DynamoDB com status `sent` ou `failed`

## Acceptance Criteria

### AC-1: Notificação de análise concluída
- Evento com `status=completed` → notificação com mensagem detalhada e elementos detectados
- Notificação salva com status `sent`

### AC-2: Notificação de análise falha
- Evento com `status=failed` → notificação com mensagem de erro
- Notificação salva com status `sent`

### AC-3: Falha no envio
- Se o `NotificationSender` lança exceção → notificação salva com status `failed`
- Serviço não derruba — continua consumindo

### AC-4: Ciclo de vida da notificação
- Criada com status `pending`
- Após envio: `sent` (com `sent_at` timestamp)
- Após falha de envio: `failed`

## Technical Design

### Hexagonal Architecture
```
messaging/ (driving)         application/           infrastructure/ (driven)
  KafkaAnalysisConsumer        NotifyUseCase           NotificationRepository
        ↓                           ↓                  NotificationSender
                              domain/
                              Notification entity
```

### Module Structure
```
services/notification-service/src/
├── config/settings.py
├── domain/notification.py          # Notification entity + NotificationStatus
├── application/notify_use_case.py  # NotifyAnalysisCompletedUseCase
├── infrastructure/
│   ├── notification_repository.py  # DynamoDB
│   └── notification_sender.py      # Logging-based sender
├── messaging/kafka_consumer.py     # KafkaAnalysisConsumer
└── main.py                         # Entry point
```

## Dependencies
- `shared/contracts` — `ArchitectureAnalysisCompletedEvent`, `AnalysisStatus`
- `shared/libs/messaging` — `KafkaConsumer`

## Test Command
```powershell
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\notification-service\src"
python -m pytest tests\unit\notification_service\ -v --no-cov -p no:cacheprovider
```
