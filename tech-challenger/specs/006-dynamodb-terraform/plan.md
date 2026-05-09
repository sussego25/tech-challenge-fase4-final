# Plan: 006 — DynamoDB Terraform

## Objective
Provisionar as duas tabelas DynamoDB necessárias ao pipeline via Terraform, integrá-las ao módulo raiz e expandir as IAM roles existentes (Lambda e worker) com permissões de leitura/escrita nas tabelas.

## Architecture Decisions
- `PAY_PER_REQUEST` (on-demand) — sem gestão manual de capacidade, adequado ao volume imprevisível de análises
- Nomes de tabela seguem o padrão `{project_name}-{recurso}-{environment}` já adotado na SQS
- GSIs definidos na criação da tabela (não como recursos separados) para simplificar o Terraform
- `created_at` no GSI `user-diagrams-index` é String ISO 8601 — permite ordenação lexicográfica sem tipo Number
- IAM policies adicionadas inline nos recursos existentes (`aws_iam_role_policy`) para não criar novos recursos desnecessários
- Módulo `dynamodb` separado em `infra/dynamodb/terraform/` seguindo o padrão já adotado pela SQS

## Flow
```
terraform apply (infra/terraform/)
  ├─ module "sqs"        (já existente) → SQS queue + DLQ
  ├─ module "dynamodb"   (novo)
  │    ├─ aws_dynamodb_table "diagrams"
  │    │    └─ GSI: user-diagrams-index (user_id + created_at)
  │    └─ aws_dynamodb_table "notifications"
  │         └─ GSI: diagram-notifications-index (diagram_id)
  ├─ module "lambda_iam" (expandido)
  │    ├─ aws_iam_role_policy sqs_send       (já existe)
  │    └─ aws_iam_role_policy dynamodb_diagrams (nova)
  └─ module "worker_iam" (expandido)
       ├─ aws_iam_role_policy sqs_receive     (já existe)
       └─ aws_iam_role_policy dynamodb_diagrams (nova)
```

## Module Structure
```
infra/dynamodb/terraform/
├── main.tf       # aws_dynamodb_table diagrams + notifications
├── variables.tf  # aws_region, environment, project_name, common_tags
└── outputs.tf    # nomes e ARNs das 2 tabelas

infra/lambda/terraform/iam/
└── iam_role.tf   # adicionar aws_iam_role_policy para DynamoDB

infra/eks/terraform/iam/
└── iam_role.tf   # adicionar aws_iam_role_policy para DynamoDB

infra/terraform/
├── main.tf       # adicionar module "dynamodb" + passar ARNs para IAM modules
├── variables.tf  # sem alteração
└── outputs.tf    # adicionar outputs do módulo dynamodb
```

## Implementation Steps

### Step 1 — `infra/dynamodb/terraform/main.tf`
- `aws_dynamodb_table "diagrams"`: PK `diagram_id` (S), GSI `user-diagrams-index`
- `aws_dynamodb_table "notifications"`: PK `notification_id` (S), GSI `diagram-notifications-index`

### Step 2 — `infra/dynamodb/terraform/variables.tf`
- `aws_region`, `environment`, `project_name`, `common_tags` — padrão igual aos outros módulos

### Step 3 — `infra/dynamodb/terraform/outputs.tf`
- Exportar `diagrams_table_name`, `diagrams_table_arn`, `notifications_table_name`, `notifications_table_arn`

### Step 4 — Expandir `infra/lambda/terraform/iam/iam_role.tf`
- Adicionar variável `dynamodb_diagrams_table_arn`
- Adicionar `aws_iam_role_policy "lambda_dynamodb_policy"` com `PutItem`, `GetItem`, `UpdateItem` na tabela de diagramas

### Step 5 — Expandir `infra/lambda/terraform/iam/variables.tf`
- Adicionar `dynamodb_diagrams_table_arn`

### Step 6 — Expandir `infra/eks/terraform/iam/iam_role.tf`
- Adicionar variável `dynamodb_diagrams_table_arn`
- Adicionar `aws_iam_role_policy "worker_dynamodb_policy"` com `PutItem`, `GetItem`, `UpdateItem`

### Step 7 — Expandir `infra/eks/terraform/iam/variables.tf`
- Adicionar `dynamodb_diagrams_table_arn`

### Step 8 — Atualizar `infra/terraform/main.tf`
- Adicionar `module "dynamodb"` apontando para `../dynamodb/terraform`
- Passar `module.dynamodb.diagrams_table_arn` para `module.lambda_iam` e `module.worker_iam`

### Step 9 — Atualizar `infra/terraform/outputs.tf`
- Adicionar os 4 outputs do módulo dynamodb

## Dependencies
- `infra/sqs/terraform/` — já existente, sem alteração
- `infra/lambda/terraform/iam/` — expandido (Steps 4-5)
- `infra/eks/terraform/iam/` — expandido (Steps 6-7)
- `infra/terraform/main.tf` — ponto central de orquestração (Steps 8-9)

## Validation
```powershell
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate
terraform plan -var="environment=dev"
```

Após apply:
```bash
aws dynamodb list-tables --region us-east-1
aws dynamodb describe-table --table-name tech-challenger-diagrams-dev
aws dynamodb describe-table --table-name tech-challenger-notifications-dev \
  --query "Table.GlobalSecondaryIndexes"
```
