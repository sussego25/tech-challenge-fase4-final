# Spec: 012 — Deploy worker-service e notification-service no EKS

**Feature Branch**: `012-eks-deploy-services`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Deploy do worker-service e notification-service no EKS (Helm charts existem)

## Context
Os Helm charts para `worker-service` e `notification-service` já existem em `deploy/helm/` com templates completos (Deployment, ConfigMap, ServiceAccount, HPA). Porém os `values.yaml` têm valores placeholder (ECR repository `123456789012...`, env vars vazias, role ARN vazio). Além disso, falta:
- Criar repositórios ECR para as imagens Docker
- Pipeline de build & push das imagens
- Preencher os values com outputs do Terraform
- Documentar o processo de deploy

## Problem Statement
Precisamos:
1. Criar repositórios ECR via Terraform para `worker-service` e `notification-service`
2. Documentar/scriptar o build e push das imagens Docker
3. Criar `values-dev.yaml` para cada serviço com valores reais do Terraform
4. Documentar o fluxo de deploy via Helm no cluster EKS
5. Garantir que os ServiceAccounts tenham annotations IRSA corretas

## User Scenarios & Testing

### User Story 1 - Build e push de imagens Docker (Priority: P1)

O desenvolvedor builda as imagens Docker localmente (ou em CI) e faz push para ECR.

**Why this priority**: Sem imagens no ECR, o Helm deploy falha com `ImagePullBackOff`.

**Independent Test**: `docker build` e `docker push` para ECR executam sem erro; imagem aparece no ECR console.

**Acceptance Scenarios**:

1. **Given** Dockerfile do worker-service, **When** `docker build -t worker-service .`, **Then** imagem criada com sucesso
2. **Given** ECR repository existe, **When** `docker push` para ECR, **Then** imagem disponível no repositório
3. **Given** imagem no ECR, **When** Helm install no EKS, **Then** pod faz pull da imagem com sucesso

---

### User Story 2 - Deploy via Helm com values reais (Priority: P1)

O operador executa `helm install` com `values-dev.yaml` contendo outputs do Terraform e os serviços sobem no EKS.

**Why this priority**: É o passo final para ter os serviços rodando na AWS.

**Acceptance Scenarios**:

1. **Given** cluster EKS ativo e kubeconfig configurado, **When** `helm install worker deploy/helm/worker-service -f values-dev.yaml`, **Then** pod `worker-service` entra em status Running
2. **Given** pod worker-service Running, **When** mensagem SQS é enviada, **Then** worker processa e publica no Kafka
3. **Given** cluster EKS ativo, **When** `helm install notification deploy/helm/notification-service -f values-dev.yaml`, **Then** pod `notification-service` entra em status Running

---

### User Story 3 - IRSA funciona corretamente (Priority: P1)

Os pods assumem roles IAM via IRSA (IAM Roles for Service Accounts) sem precisar de credenciais hardcoded.

**Why this priority**: Sem IRSA, os pods não têm permissão para acessar SQS, DynamoDB, S3, SageMaker.

**Acceptance Scenarios**:

1. **Given** ServiceAccount com annotation `eks.amazonaws.com/role-arn`, **When** pod inicia, **Then** AWS SDK assume a role automaticamente
2. **Given** role do worker com permissões SQS+DynamoDB+S3+SageMaker, **When** worker processa mensagem, **Then** todas as chamadas AWS succedem sem `AccessDenied`

### Edge Cases

- ECR repository vazio → Pod fica em `ImagePullBackOff`; Helm rollback automático se `--wait`
- IRSA annotation incorreta → Pod roda mas recebe `AccessDenied` nas chamadas AWS
- MSK não acessível da subnet → Pod conecta mas Kafka producer/consumer timeout

## Requirements

### Functional Requirements

- **FR-001**: DEVE existir repositório ECR `tech-challenger/worker-service` criado via Terraform
- **FR-002**: DEVE existir repositório ECR `tech-challenger/notification-service` criado via Terraform
- **FR-003**: DEVE existir script ou documentação para build & push das imagens Docker
- **FR-004**: DEVE existir `values-dev.yaml` para cada serviço com valores do ambiente dev
- **FR-005**: `values-dev.yaml` DEVE conter URIs de ECR, ARNs das roles IRSA, e todas as env vars preenchidas
- **FR-006**: ServiceAccount annotations DEVEM referenciar ARN da role IRSA correta
- **FR-007**: DEVE existir documentação do fluxo completo de deploy (ECR login → build → push → helm install)

### Key Entities

- **ECR Repository**: Repositório de imagens Docker na AWS
- **Helm Release**: Instância de um Helm chart no cluster
- **ServiceAccount**: Identidade Kubernetes com annotation IRSA
- **values-dev.yaml**: Override de valores do Helm para ambiente dev

## Success Criteria

- **SC-001**: `helm install` de ambos os serviços resulta em pods Running
- **SC-002**: Pods conseguem acessar AWS services via IRSA sem credenciais explícitas
- **SC-003**: Worker consome SQS, processa e publica no Kafka
- **SC-004**: Notification-service consome Kafka e salva no DynamoDB

## Clarifications

### Session 2026-04-18

- **EKS Node Group**: Usar **spot instances** `t3.medium` (2 vCPU, 4GB) para dev. HPA com min=1, max=2 replicas, CPU target 70%. Reduz custo em ~70%.
- **SageMaker Failures**: Worker usa SQS visibility timeout + DLQ com max 3 retries. Após 3 falhas, mensagem vai para DLQ. Adicionar env var `SQS_DLQ_URL` no values-dev.yaml do worker.
- **`user_email` field**: `user_id` é UUID. Adicionar `user_email` nos eventos/contracts. notification-service values-dev.yaml não precisa de mudanças (campo vem do evento Kafka).
- **Encryption**: Sem KMS customizado. EKS secrets encryption via AWS-managed keys.
- **Observability**: CloudWatch only — JSON structured logs via Fluent Bit DaemonSet, CloudWatch Alarms. Sem Prometheus/Grafana. Adicionar Fluent Bit Helm chart como dependência do deploy.

## Assumptions

- Cluster EKS já está ativo (spec 009 + 010)
- MSK (Kafka) já está ativo e acessível das subnets privadas
- SageMaker endpoint já está ativo (spec 014)
- `kubectl` e `helm` estão instalados e configurados localmente
- AWS CLI está autenticado com permissões ECR

## Out of Scope

- CI/CD pipeline automatizado (GitHub Actions, CodePipeline) — pode ser spec separada
- Ingress/Load Balancer para exposição externa dos serviços (são consumers internos)
- Monitoramento e alerting (Prometheus, Grafana) — spec separada

## Technical Design

### ECR Terraform (novo módulo)
```
infra/ecr/terraform/
├── main.tf        # aws_ecr_repository para worker e notification
├── variables.tf   # project_name, environment
└── outputs.tf     # repository_urls
```

### values-dev.yaml (worker-service)
```yaml
image:
  repository: <account-id>.dkr.ecr.us-east-1.amazonaws.com/tech-challenger/worker-service
  tag: "1.0.0"

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::<account-id>:role/tech-challenger-worker-service-role-dev"

env:
  AWS_REGION: "us-east-1"
  SQS_QUEUE_URL: "https://sqs.us-east-1.amazonaws.com/<account-id>/tech-challenger-architecture-analysis-dev"
  S3_BUCKET: "tech-challenger-diagrams-dev"
  DYNAMODB_TABLE: "tech-challenger-diagrams-dev"
  KAFKA_BOOTSTRAP_SERVERS: "<msk-broker-1>:9092,<msk-broker-2>:9092"
  KAFKA_TOPIC_ANALYSIS_COMPLETED: "analysis-completed"
  SAGEMAKER_ENDPOINT: "tech-challenger-llm-dev"
```

### values-dev.yaml (notification-service)
```yaml
image:
  repository: <account-id>.dkr.ecr.us-east-1.amazonaws.com/tech-challenger/notification-service
  tag: "1.0.0"

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::<account-id>:role/tech-challenger-notification-service-role-dev"

env:
  AWS_REGION: "us-east-1"
  KAFKA_BOOTSTRAP_SERVERS: "<msk-broker-1>:9092,<msk-broker-2>:9092"
  KAFKA_TOPIC_ANALYSIS_COMPLETED: "analysis-completed"
  KAFKA_GROUP_ID: "notification-service"
  DYNAMODB_TABLE: "tech-challenger-notifications-dev"
  SES_SENDER_EMAIL: "noreply@techchallenger.com"
```

### Script de deploy
```bash
#!/bin/bash
# deploy.sh — Build, push e deploy dos serviços

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# ECR login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build e push worker-service
docker build -t worker-service services/worker-service/
docker tag worker-service $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tech-challenger/worker-service:1.0.0
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tech-challenger/worker-service:1.0.0

# Build e push notification-service
docker build -t notification-service services/notification-service/
docker tag notification-service $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tech-challenger/notification-service:1.0.0
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tech-challenger/notification-service:1.0.0

# Helm deploy
aws eks update-kubeconfig --name tech-challenger-dev --region $REGION
helm upgrade --install worker deploy/helm/worker-service -f deploy/helm/worker-service/values-dev.yaml --wait
helm upgrade --install notification deploy/helm/notification-service -f deploy/helm/notification-service/values-dev.yaml --wait
```

## Dependencies
- **Spec 009** — VPC/Networking para o EKS
- **Spec 010** — EKS cluster ativo, IRSA roles criadas
- **Spec 011** — NotificationSender com SES (para notification-service funcionar end-to-end)
- `deploy/helm/worker-service/` — Helm chart existente
- `deploy/helm/notification-service/` — Helm chart existente
- `services/worker-service/Dockerfile` — já existe
- `services/notification-service/Dockerfile` — já existe

## Test / Validação
```bash
# Verificar pods
kubectl get pods -l app.kubernetes.io/name=worker-service
kubectl get pods -l app.kubernetes.io/name=notification-service

# Verificar logs
kubectl logs -l app.kubernetes.io/name=worker-service --tail=50
kubectl logs -l app.kubernetes.io/name=notification-service --tail=50

# Teste end-to-end: enviar mensagem SQS manualmente
aws sqs send-message --queue-url $SQS_URL --message-body '{"diagram_id":"...","s3_key":"...","user_id":"test@email.com"}'
# Verificar DynamoDB, Kafka e e-mail recebido
```
