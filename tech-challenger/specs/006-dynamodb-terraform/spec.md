# Spec: 006 — DynamoDB Terraform

## Context
O pipeline de análise de diagramas precisa de duas tabelas DynamoDB:
- `ArchitectureDiagram`: usada pelo `order-handler` (Lambda) e pelo `worker-service` para persistir e atualizar o ciclo de vida do diagrama
- `Notification`: usada pelo `notification-service` para persistir o registro de cada notificação enviada ao usuário

Atualmente a pasta `infra/dynamodb/terraform/` está vazia. Sem essas tabelas provisionadas via Terraform, o pipeline não consegue persistir estado em nenhum estágio.

## Problem Statement
Precisamos de módulos Terraform que:
1. Criem a tabela `ArchitectureDiagram` com partition key `diagram_id` e GSI por `user_id`
2. Criem a tabela `Notification` com partition key `notification_id` e GSI por `diagram_id`
3. Integrem ao módulo raiz `infra/terraform/main.tf` como `module "dynamodb"`
4. Exportem os nomes das tabelas como outputs para uso nas variáveis de ambiente dos serviços

## Acceptance Criteria

### AC-1: Tabela ArchitectureDiagram criada
- Partition key: `diagram_id` (String)
- Atributos: `user_id`, `status`, `s3_key`, `s3_bucket`, `created_at`, `updated_at`, `elements_detected`, `analysis_report` (opcional)
- GSI `user-diagrams-index`: partition key `user_id`, sort key `created_at` → permite listar todos os diagramas de um usuário por data
- Billing mode: `PAY_PER_REQUEST`
- Tags com `environment` e `project_name`

### AC-2: Tabela Notification criada
- Partition key: `notification_id` (String)
- Atributos: `diagram_id`, `user_id`, `message`, `status`, `created_at`, `sent_at` (opcional)
- GSI `diagram-notifications-index`: partition key `diagram_id` → permite buscar todas as notificações de um diagrama
- Billing mode: `PAY_PER_REQUEST`
- Tags com `environment` e `project_name`

### AC-3: Outputs exportados
- `diagrams_table_name` → nome da tabela ArchitectureDiagram
- `diagrams_table_arn` → ARN da tabela ArchitectureDiagram
- `notifications_table_name` → nome da tabela Notification
- `notifications_table_arn` → ARN da tabela Notification

### AC-4: Integração no módulo raiz
- `infra/terraform/main.tf` adiciona `module "dynamodb"` chamando `../dynamodb/terraform`
- `infra/terraform/outputs.tf` expõe os 4 outputs do módulo DynamoDB
- IAM role da Lambda (`module.lambda_iam`) recebe permissões `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` na tabela `diagrams`
- IAM role do worker (`module.worker_iam`) recebe permissões `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` na tabela `diagrams`
- IAM role do notification-service recebe permissões `dynamodb:PutItem` na tabela `notifications`

### AC-5: Nomes seguem padrão do projeto
- Tabela de diagramas: `{project_name}-diagrams-{environment}`
- Tabela de notificações: `{project_name}-notifications-{environment}`

## Out of Scope
- Streams DynamoDB
- Backups point-in-time (PITR) — pode ser adicionado como variável opcional futuramente
- Criptografia com CMK (usa KMS gerenciado da AWS por padrão)

## Technical Design

### Estrutura de módulo
```
infra/dynamodb/terraform/
├── main.tf        # aws_dynamodb_table para diagrams e notifications
├── variables.tf   # aws_region, environment, project_name, common_tags
└── outputs.tf     # nomes e ARNs das tabelas
```

### Schema — Tabela ArchitectureDiagram
```
PK: diagram_id (S)

GSI: user-diagrams-index
  PK: user_id (S)
  SK: created_at (S)  ← ISO 8601 permite ordenação lexicográfica
```

### Schema — Tabela Notification
```
PK: notification_id (S)

GSI: diagram-notifications-index
  PK: diagram_id (S)
```

### Integração com IAM existente
Os módulos `lambda_iam` e `worker_iam` já existem em `infra/lambda/terraform/iam` e `infra/eks/terraform/iam`. Ambos precisam receber os ARNs das tabelas DynamoDB como variáveis adicionais para criar as policies corretas.

### Fluxo de dependência no `main.tf` raiz
```
module "dynamodb" (novo)
       ↓ outputs
module "lambda_iam"  ← recebe diagrams_table_arn
module "worker_iam"  ← recebe diagrams_table_arn
(futuro) module "notification_iam" ← recebe notifications_table_arn
```

## Environment Variables geradas
| Serviço | Variável | Valor |
|---|---|---|
| `order-handler` (Lambda) | `DYNAMODB_TABLE` | `tech-challenger-diagrams-prod` |
| `worker-service` | `DYNAMODB_TABLE` | `tech-challenger-diagrams-prod` |
| `notification-service` | `DYNAMODB_TABLE` | `tech-challenger-notifications-prod` |

## Dependencies
- `infra/terraform/main.tf` — ponto de integração do módulo
- `infra/lambda/terraform/iam/iam_role.tf` — precisa receber `dynamodb_table_arn`
- `infra/eks/terraform/iam/iam_role.tf` — precisa receber `dynamodb_table_arn`

## Test / Validação
```powershell
# Validar sintaxe Terraform
cd tech-challenger/infra/terraform
terraform init
terraform validate
terraform plan -var="environment=dev"
```

Após `terraform apply`:
```bash
# Verificar tabelas criadas na AWS
aws dynamodb list-tables --region us-east-1

# Verificar atributos da tabela de diagramas
aws dynamodb describe-table --table-name tech-challenger-diagrams-prod

# Verificar GSI da tabela de notificações
aws dynamodb describe-table --table-name tech-challenger-notifications-prod \
  --query "Table.GlobalSecondaryIndexes"
```
