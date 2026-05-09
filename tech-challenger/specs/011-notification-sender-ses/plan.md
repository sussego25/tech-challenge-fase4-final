# Plan: 011 — NotificationSender Real (Amazon SES)

## Objective
Substituir o stub `NotificationSender` (que apenas faz `logger.info()`) por uma implementação real usando Amazon SES para envio de e-mail. Manter fallback gracioso quando SES não está configurado.

## Architecture Decisions
- **SES sobre SNS** — e-mail é o canal mais adequado para relatórios de análise (conteúdo longo); SNS é melhor para notificações curtas
- **Fallback para log** — quando `SES_SENDER_EMAIL` está vazio, sender apenas loga (compatível com dev local sem SES)
- **Sem template HTML** — corpo do e-mail é plain text com `notification.message` (já formatado pelo use case); templates HTML são overengineering para MVP
- **SES client injetado no construtor** — permite mock no teste sem monkey-patch de boto3
- **Não alterar `NotifyAnalysisCompletedUseCase`** — a interface do sender não muda, apenas a implementação

## Flow
```
NotifyAnalysisCompletedUseCase.execute(event)
  │
  ├─ _format_message(event)  →  message string
  ├─ Notification(diagram_id, user_id, message)
  │
  ├─ NotificationSender.send(notification)
  │    ├─ IF SES configurado:
  │    │    └─ ses.send_email(Source, Destination, Message)
  │    └─ ELSE:
  │         └─ logger.warning("SES not configured, logging only")
  │
  ├─ notification.mark_sent()  ── ou ──  notification.mark_failed()
  └─ repo.save(notification)
```

## Module Structure
```
services/notification-service/src/
├── config/settings.py                # MODIFICAR: adicionar SES_SENDER_EMAIL, SES_AWS_REGION
├── infrastructure/
│   └── notification_sender.py        # REESCREVER: implementação SES + fallback
└── main.py                           # MODIFICAR: passar SES config ao sender

deploy/helm/notification-service/
└── values.yaml                       # MODIFICAR: adicionar SES_SENDER_EMAIL, SES_AWS_REGION

tests/unit/notification_service/      # NOVO (se não existir)
└── test_notification_sender.py       # Testes unitários com mock SES
```

## Implementation Steps

### Step 1 — Atualizar `services/notification-service/src/config/settings.py`
- Adicionar `SES_SENDER_EMAIL: str = os.environ.get("SES_SENDER_EMAIL", "")`
- Adicionar `SES_AWS_REGION: str = os.environ.get("SES_AWS_REGION", "us-east-1")`

### Step 2 — Reescrever `services/notification-service/src/infrastructure/notification_sender.py`
- Construtor: recebe `sender_email: str` e `region: str`
- Se `sender_email` não vazio: cria `boto3.client("ses", region_name=region)`
- Se vazio: `self._ses = None`
- `send(notification)`:
  - Se `self._ses is None`: `logger.warning(...)`, return (sem exceção)
  - Senão: `self._ses.send_email(Source=..., Destination={"ToAddresses": [notification.user_id]}, Message={"Subject": {"Data": f"Architecture Diagram Analysis - {notification.diagram_id}"}, "Body": {"Text": {"Data": notification.message}}})`
  - Não capturar exceções aqui — deixar propagar para o use case tratar `mark_failed()`

### Step 3 — Atualizar `services/notification-service/src/main.py`
- Ler `Settings.SES_SENDER_EMAIL` e `Settings.SES_AWS_REGION`
- Instanciar `NotificationSender(sender_email=..., region=...)`

### Step 4 — Atualizar `deploy/helm/notification-service/values.yaml`
- Adicionar `SES_SENDER_EMAIL: ""` e `SES_AWS_REGION: "us-east-1"` na seção `env`

### Step 5 — Testes unitários (se estrutura de testes unitários existir)
- Teste 1: SES configurado + send sucesso → `ses.send_email` chamado com args corretos
- Teste 2: SES configurado + send falha → exceção propaga
- Teste 3: SES não configurado → apenas loga, sem exceção, sem chamada SES

## Dependencies
- `boto3` já está no `requirements.txt` do notification-service
- **Spec 010** — role IRSA com `ses:SendEmail` (sem a permissão, o send retorna AccessDenied)
- SES verificado na conta AWS (pelo menos sandbox mode com endereços de teste)

## Validation
```powershell
# Testes unitários
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\notification-service\src"
python -m pytest tests/unit/notification_service/ -v

# Teste manual SES (sandbox)
python -c "
import boto3
ses = boto3.client('ses', region_name='us-east-1')
ses.send_email(
    Source='verified@example.com',
    Destination={'ToAddresses': ['verified@example.com']},
    Message={'Subject': {'Data': 'Test'}, 'Body': {'Text': {'Data': 'Hello'}}}
)
print('Email sent!')
"
```
