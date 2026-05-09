# Plan 007 — S3 Terraform

## Abordagem
Seguir o mesmo padrão modular do DynamoDB Terraform (spec 006): criar o módulo em `infra/s3/terraform/`, integrá-lo no root module, e expandir os módulos IAM existentes com policies S3.

## Passos

1. **`infra/s3/terraform/variables.tf`** — Variáveis de entrada: `aws_region`, `environment`, `project_name`, `common_tags`, `lifecycle_expiration_days`

2. **`infra/s3/terraform/main.tf`** — Recursos:
   - `data "aws_caller_identity"` para obter `account_id` (nome único global)
   - `aws_s3_bucket "diagrams"` — bucket principal
   - `aws_s3_bucket_versioning` — habilitar versionamento
   - `aws_s3_bucket_server_side_encryption_configuration` — SSE-S3 AES256
   - `aws_s3_bucket_public_access_block` — bloquear todo acesso público
   - `aws_s3_bucket_lifecycle_configuration` — expirar objetos após `var.lifecycle_expiration_days`

3. **`infra/s3/terraform/outputs.tf`** — Outputs:
   - `diagrams_bucket_name`
   - `diagrams_bucket_arn`

4. **`infra/lambda/terraform/iam/variables.tf`** — Adicionar `s3_diagrams_bucket_arn`

5. **`infra/lambda/terraform/iam/iam_role.tf`** — Adicionar policy `lambda_s3_policy` (PutObject, GetObject, DeleteObject)

6. **`infra/eks/terraform/iam/variables.tf`** — Adicionar `s3_diagrams_bucket_arn`

7. **`infra/eks/terraform/iam/iam_role.tf`** — Adicionar policy `worker_s3_policy` (GetObject)

8. **`infra/terraform/main.tf`** — Adicionar `module "s3"` e passar `s3_diagrams_bucket_arn` para os módulos IAM

9. **`infra/terraform/outputs.tf`** — Adicionar `diagrams_bucket_name` e `diagrams_bucket_arn`

10. **Validar** — `terraform validate` + `terraform plan -var="environment=dev"`

## Decisões Técnicas
- Usar `account_id` no nome do bucket para garantir unicidade global (requisito AWS)
- Lifecycle padrão de 90 dias para `dev`, configurável via variável
- Worker precisa apenas de `GetObject` (read-only); Lambda precisa de `PutObject` e `GetObject`
