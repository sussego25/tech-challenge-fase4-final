# Plan: 012 — EKS Deploy (ECR + Docker + Helm)

## Objective
Criar repositórios ECR via Terraform, script Docker build/push, valores Helm com outputs reais do Terraform e documentação de deploy. Cobrir worker-service e notification-service.

## Architecture Decisions
- **ECR via Terraform** — repositórios gerenciados como IaC, lifecycle policy de 30 imagens para controle de custo
- **Script `build-and-push.sh`** — único script para ambos os serviços, aceita `--service` e `--tag`; evita CI/CD complexo para MVP
- **`values-dev.yaml`** como overlay Helm** — sobrescreve apenas image.repository, env vars, e serviceAccount.annotations; herda tudo do values.yaml
- **IRSA annotation no service account** — referencia ARN da role criada no spec 010
- **Tag `latest` + SHA** — push duplo para rollback fácil

## Flow
```
[1] terraform apply → ECR repos criados (worker-ecr, notification-ecr)
                        │
[2] build-and-push.sh --service worker-service --tag v1.0.0
      ├─ docker build -t <ecr-url>:v1.0.0 -t <ecr-url>:latest
      ├─ aws ecr get-login-password | docker login
      └─ docker push <ecr-url>:v1.0.0
                        │
[3] helm upgrade --install worker-service deploy/helm/worker-service/ -f values-dev.yaml
      ├─ Deployment → Pod (image: <ecr-url>:v1.0.0)
      ├─ ServiceAccount (annotation: eks.amazonaws.com/role-arn)
      ├─ ConfigMap (env vars: SQS_QUEUE_URL, S3_BUCKET, ...)
      └─ HPA (min=1, max=3)
```

## Module Structure
```
infra/ecr/                             # NOVO
├── terraform/
│   ├── main.tf        # 2 ECR repos + lifecycle policy
│   ├── variables.tf   # environment, project_name, services list
│   └── outputs.tf     # repo URLs map

deploy/
├── scripts/
│   └── build-and-push.sh              # NOVO — Docker build + ECR push
├── helm/
│   ├── worker-service/
│   │   └── values-dev.yaml            # NOVO — overlay com valores reais
│   └── notification-service/
│       └── values-dev.yaml            # NOVO — overlay com valores reais

infra/terraform/
├── main.tf            # MODIFICAR — adicionar module "ecr"
├── variables.tf       # MODIFICAR — serviços ECR
└── outputs.tf         # MODIFICAR — ECR repo URLs

docs/deployment/
└── deploy-eks.md                      # NOVO — guia passo a passo
```

## Implementation Steps

### Step 1 — Criar `infra/ecr/terraform/variables.tf`
- `environment`, `project_name`, `common_tags`
- `services` (list, default `["worker-service", "notification-service"]`)
- `max_image_count` (number, default `30`)

### Step 2 — Criar `infra/ecr/terraform/main.tf`
- `aws_ecr_repository` (for_each sobre var.services):
  - `name = "${var.project_name}-${var.environment}-${each.value}"`
  - `image_tag_mutability = "MUTABLE"` (permite overwrite de `latest`)
  - `image_scanning_configuration { scan_on_push = true }`
- `aws_ecr_lifecycle_policy` (for_each):
  - Manter apenas `var.max_image_count` imagens mais recentes

### Step 3 — Criar `infra/ecr/terraform/outputs.tf`
- `repository_urls` (map: service_name → URL)
- `repository_arns` (map: service_name → ARN)

### Step 4 — Atualizar `infra/terraform/main.tf`
- Adicionar `module "ecr"` com source `"../ecr/terraform"`
- Sem `count` — ECR é sempre necessário quando se faz deploy

### Step 5 — Atualizar `infra/terraform/outputs.tf`
- Adicionar `ecr_repository_urls` e `ecr_repository_arns`

### Step 6 — Criar `deploy/scripts/build-and-push.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
# Parâmetros: --service <name> --tag <tag> --region <region> --account-id <id>
# Passos:
#   1. cd services/<service>/
#   2. docker build -t <ecr-url>:<tag> -t <ecr-url>:latest .
#   3. aws ecr get-login-password | docker login --stdin
#   4. docker push <ecr-url>:<tag>
#   5. docker push <ecr-url>:latest
```
- Validar que `aws`, `docker` estão no PATH
- Usar `ACCOUNT_ID` e `REGION` de argumento ou de `aws sts get-caller-identity`

### Step 7 — Criar `deploy/helm/worker-service/values-dev.yaml`
- `image.repository: <ECR_URL_PLACEHOLDER>`
- `image.tag: latest`
- `serviceAccount.annotations."eks.amazonaws.com/role-arn": <WORKER_ROLE_ARN_PLACEHOLDER>`
- `env`:
  - `SQS_QUEUE_URL: <terraform output sqs_queue_url>`
  - `S3_BUCKET: <terraform output s3_bucket_name>`
  - `DYNAMODB_TABLE: <terraform output dynamodb_table_name>`
  - `KAFKA_BOOTSTRAP_SERVERS: <terraform output kafka_bootstrap_brokers>`
  - `KAFKA_TOPIC_ANALYSIS_COMPLETED: "analysis-completed"`
  - `SAGEMAKER_ENDPOINT: <terraform output sagemaker_endpoint_name>`
  - `AWS_REGION: "us-east-1"`

### Step 8 — Criar `deploy/helm/notification-service/values-dev.yaml`
- Mesma estrutura do Step 7, adaptada:
  - `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_ANALYSIS_COMPLETED`, `KAFKA_GROUP_ID: "notification-group"`
  - `DYNAMODB_TABLE: <terraform output dynamodb_notifications_table_name>`
  - `SES_SENDER_EMAIL: ""` (a definir conforme verificação SES)
  - `SES_AWS_REGION: "us-east-1"`
  - `serviceAccount.annotations."eks.amazonaws.com/role-arn": <NOTIFICATION_ROLE_ARN_PLACEHOLDER>`

### Step 9 — Criar `docs/deployment/deploy-eks.md`
- Pré-requisitos: Terraform aplicado, kubeconfig configurado, Docker instalado
- Seção 1: Build e push das imagens
- Seção 2: Gerar values-dev.yaml a partir de terraform output (exemplo de comando)
- Seção 3: `helm upgrade --install` para cada serviço
- Seção 4: Verificação (`kubectl get pods`, `kubectl logs`)
- Seção 5: Troubleshooting comum (ImagePullBackOff, IAM permission denied)

## Dependencies
- **Spec 009** — VPC/subnets (EKS precisa deles, mas ECR não)
- **Spec 010** — IRSA roles (worker + notification) para annotations
- **Spec 011** — SES_SENDER_EMAIL env var para notification values-dev.yaml
- Dockerfiles já existem em `services/worker-service/Dockerfile` e `services/notification-service/Dockerfile`
- Helm charts já existem em `deploy/helm/`

## Validation
```powershell
# Terraform
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate
terraform plan -var="environment=dev"

# Helm lint (sem deploy real)
cd tech-challenger/deploy/helm
helm lint worker-service/ -f worker-service/values-dev.yaml
helm lint notification-service/ -f notification-service/values-dev.yaml

# Script syntax check
bash -n deploy/scripts/build-and-push.sh
```
