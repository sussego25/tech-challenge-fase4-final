# Tasks: 006 — DynamoDB Terraform

## Status: ✅ COMPLETE

| # | Task | Status |
|---|------|--------|
| 1 | Criar `spec.md` | ✅ Done |
| 2 | Criar `plan.md` | ✅ Done |
| 3 | Criar `infra/dynamodb/terraform/variables.tf` | ✅ Done |
| 4 | Criar `infra/dynamodb/terraform/main.tf` (tabelas diagrams + notifications + GSIs) | ✅ Done |
| 5 | Criar `infra/dynamodb/terraform/outputs.tf` (4 outputs: nomes e ARNs) | ✅ Done |
| 6 | Expandir `infra/lambda/terraform/iam/variables.tf` (adicionar `dynamodb_diagrams_table_arn`) | ✅ Done |
| 7 | Expandir `infra/lambda/terraform/iam/iam_role.tf` (adicionar policy DynamoDB para Lambda) | ✅ Done |
| 8 | Expandir `infra/eks/terraform/iam/variables.tf` (adicionar `dynamodb_diagrams_table_arn`) | ✅ Done |
| 9 | Expandir `infra/eks/terraform/iam/iam_role.tf` (adicionar policy DynamoDB para worker) | ✅ Done |
| 10 | Atualizar `infra/terraform/main.tf` (adicionar `module "dynamodb"` + passar ARNs para IAM modules) | ✅ Done |
| 11 | Atualizar `infra/terraform/outputs.tf` (adicionar 4 outputs do módulo dynamodb) | ✅ Done |
| 12 | Validar com `terraform validate` + `terraform plan -var="environment=dev"` | ✅ Done |

## Test Results
```
terraform validate → Success! The configuration is valid.
```
