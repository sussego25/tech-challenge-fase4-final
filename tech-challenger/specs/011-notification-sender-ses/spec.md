# Spec: 011 — NotificationSender Real (Amazon SES)

**Feature Branch**: `011-notification-sender-ses`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Implementar NotificationSender real (SNS, SES, etc.)

## Context
O `notification-service` possui um `NotificationSender` que atualmente é um **stub** — apenas faz `logger.info()` sem enviar notificação nenhuma. O fluxo do pipeline termina com um log no console ao invés de notificar o usuário. O use case (`NotifyAnalysisCompletedUseCase`) já trata sucesso/falha corretamente, falta apenas a implementação real do sender.

A escolha é **Amazon SES** (Simple Email Service) por ser o canal mais adequado para notificações de relatórios de análise de arquitetura — o usuário recebe um e-mail com o resultado.

## Problem Statement
Precisamos:
1. Implementar `NotificationSender` com envio real via Amazon SES
2. Adicionar variáveis de configuração (e-mail remetente, região SES)
3. Adicionar permissão `ses:SendEmail` na role IRSA do notification-service
4. Manter compatibilidade com a interface existente (o use case não muda)

## User Scenarios & Testing

### User Story 1 - Envio de e-mail ao completar análise (Priority: P1)

Quando a análise de um diagrama é concluída com sucesso, o notification-service envia um e-mail ao usuário com o resultado da análise.

**Why this priority**: É a funcionalidade core que falta para fechar o pipeline end-to-end.

**Independent Test**: Com SES verificado em sandbox, enviar um e-mail para um endereço verificado e confirmar recebimento.

**Acceptance Scenarios**:

1. **Given** evento `AnalysisCompletedEvent(status=COMPLETED)` consumido do Kafka, **When** `NotificationSender.send()` é chamado, **Then** e-mail enviado via SES ao `user_id` (que é o e-mail) com assunto e corpo contendo elementos detectados
2. **Given** evento `AnalysisCompletedEvent(status=FAILED)` consumido do Kafka, **When** `NotificationSender.send()` é chamado, **Then** e-mail enviado com mensagem de falha e `error_message`
3. **Given** SES retorna erro (quota excedida, e-mail não verificado), **When** `send()` falha, **Then** exceção propaga para o use case que marca `mark_failed()` e salva no DynamoDB

---

### User Story 2 - Configuração via variáveis de ambiente (Priority: P1)

O operador configura o remetente e região SES via variáveis de ambiente no Helm chart, sem alterar código.

**Why this priority**: Necessário para deploy em diferentes ambientes (dev/prod).

**Acceptance Scenarios**:

1. **Given** env var `SES_SENDER_EMAIL=noreply@techchallenger.com`, **When** service inicia, **Then** todos os e-mails são enviados com esse remetente
2. **Given** env var `SES_SENDER_EMAIL` não está definida, **When** service inicia, **Then** log de warning e fallback para o comportamento atual (só log)

---

### User Story 3 - Fallback gracioso (Priority: P2)

Se SES não estiver configurado (sandbox, sem verificação), o sender faz fallback para log sem quebrar o serviço.

**Why this priority**: Permite rodar em ambiente local/dev sem SES configurado.

**Acceptance Scenarios**:

1. **Given** `SES_SENDER_EMAIL` está vazio, **When** `send()` é chamado, **Then** apenas loga a notificação (comportamento atual) sem erro

### Edge Cases

- `user_id` não é um e-mail válido → Log de erro, marca notificação como FAILED
- SES em sandbox e destinatário não verificado → SES retorna `MessageRejected` → exceção capturada pelo use case
- Limite de envio SES excedido → `Throttling` error → exceção propagada, notificação marcada FAILED

## Requirements

### Functional Requirements

- **FR-001**: `NotificationSender.send()` DEVE enviar e-mail via `boto3 ses.send_email()`
- **FR-002**: Assunto do e-mail: `"Architecture Diagram Analysis - {diagram_id}"`
- **FR-003**: Corpo do e-mail: `notification.message` (já formatado pelo use case)
- **FR-004**: Remetente configurável via `SES_SENDER_EMAIL` (env var)
- **FR-005**: Se `SES_SENDER_EMAIL` estiver vazio, DEVE fazer fallback para log (sem erro)
- **FR-006**: `settings.py` DEVE incluir `SES_SENDER_EMAIL` e `SES_AWS_REGION`
- **FR-007**: Role IRSA do notification-service DEVE incluir `ses:SendEmail` e `ses:SendRawEmail`
- **FR-008**: Helm chart `values.yaml` DEVE incluir `SES_SENDER_EMAIL` nas env vars

### Key Entities

- **NotificationSender**: Adapter de infraestrutura que envia notificações (driven port)
- **SES**: Amazon Simple Email Service — serviço gerenciado de e-mail transacional

## Success Criteria

- **SC-001**: E-mail recebido na caixa de entrada ao processar diagrama COMPLETED
- **SC-002**: Notificação salva com status SENT no DynamoDB após envio bem-sucedido
- **SC-003**: Notificação salva com status FAILED se SES retornar erro
- **SC-004**: Service funciona sem erro quando `SES_SENDER_EMAIL` está vazio (modo dev)

## Clarifications

### Session 2026-04-18

- **`user_id` vs `user_email`**: `user_id` é UUID, NÃO é o e-mail. Adicionar campo `user_email` nos shared contracts/events. O `NotificationSender` deve usar `notification.user_email` (não `notification.user_id`) como destino SES `ToAddresses`. Lambda handler extrai `user_email` do header `x-user-email` e propaga nos eventos.
- **Encryption**: Sem KMS customizado. SES usa TLS em trânsito por padrão.
- **Observability**: CloudWatch only — JSON structured logs, CloudWatch Alarms para falhas SES. Sem Prometheus/Grafana.

## Assumptions

- O campo `user_email` no evento contém um endereço de e-mail válido (ex: `user@example.com`). `user_id` é UUID e NÃO é usado como destino SES.
- SES estará no modo sandbox inicialmente — será necessário verificar endereços de teste
- Apenas envio de e-mail é implementado nesta spec (SMS, push são out of scope)

## Out of Scope

- Templates de e-mail HTML (corpo é plain text com o `notification.message`)
- Envio de anexos (relatório como PDF)
- SNS, SMS ou push notifications — podem ser adicionados como novos senders
- SES domain verification via Terraform (manual ou spec separada)

## Technical Design

### Mudanças em notification-service

```
services/notification-service/src/
├── config/settings.py          ← adicionar SES_SENDER_EMAIL, SES_AWS_REGION
├── infrastructure/
│   └── notification_sender.py  ← implementar envio via SES
└── main.py                     ← injetar SES config no sender
```

### notification_sender.py (novo)
```python
class NotificationSender:
    def __init__(self, sender_email: str = "", region: str = "us-east-1"):
        self._sender_email = sender_email
        self._ses = boto3.client("ses", region_name=region) if sender_email else None

    def send(self, notification: Notification) -> None:
        if not self._ses:
            logger.warning("SES not configured, logging only: %s", notification.message)
            return

        self._ses.send_email(
            Source=self._sender_email,
            Destination={"ToAddresses": [notification.user_email]},
            Message={
                "Subject": {"Data": f"Architecture Diagram Analysis - {notification.diagram_id}"},
                "Body": {"Text": {"Data": notification.message}},
            },
        )
```

### IAM — Adicionar ao módulo iam-notification (spec 010)
```hcl
resource "aws_iam_role_policy" "notification_ses_policy" {
  name = "${var.project_name}-notification-ses-policy-${var.environment}"
  role = aws_iam_role.notification_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendEmail", "ses:SendRawEmail"]
      Resource = "*"
    }]
  })
}
```

### Helm values.yaml — Adicionar
```yaml
env:
  SES_SENDER_EMAIL: "noreply@techchallenger.com"
  SES_AWS_REGION: "us-east-1"
```

## Dependencies
- **Spec 010** — role IRSA do notification-service (para adicionar permissão SES)
- `services/notification-service/src/infrastructure/notification_sender.py` — arquivo a modificar
- `services/notification-service/src/config/settings.py` — adicionar novas vars
- `deploy/helm/notification-service/values.yaml` — adicionar SES env vars
- Amazon SES verificado na conta (pelo menos em sandbox mode)

## Test / Validação
```powershell
# Unit test com mock do boto3 SES
cd tech-challenger
$env:PYTHONPATH = ".\shared;.\services\notification-service\src"
python -m pytest tests/unit/notification_service/ -v

# Integration test (requer SES sandbox)
# Verificar e-mail recebido no endereço de teste
```
