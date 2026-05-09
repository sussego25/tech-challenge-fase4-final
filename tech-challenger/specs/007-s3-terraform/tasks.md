# Tasks: 007 — S3 Terraform

## Status: ✅ COMPLETE

| # | Task | Status |
|---|------|--------|
| 1 | Criar `spec.md` | ✅ Done |
| 2 | Criar `plan.md` | ✅ Done |
| 3 | Criar `infra/s3/terraform/variables.tf` | ✅ Done |
| 4 | Criar `infra/s3/terraform/main.tf` (bucket + versionamento + criptografia + lifecycle + block public access) | ✅ Done |
| 5 | Criar `infra/s3/terraform/outputs.tf` (diagrams_bucket_name, diagrams_bucket_arn) | ✅ Done |
| 6 | Expandir `infra/lambda/terraform/iam/variables.tf` (adicionar `s3_diagrams_bucket_arn`) | ✅ Done |
| 7 | Expandir `infra/lambda/terraform/iam/iam_role.tf` (adicionar policy S3 PutObject/GetObject/DeleteObject) | ✅ Done |
| 8 | Expandir `infra/eks/terraform/iam/variables.tf` (adicionar `s3_diagrams_bucket_arn`) | ✅ Done |
| 9 | Expandir `infra/eks/terraform/iam/iam_role.tf` (adicionar policy S3 GetObject para worker) | ✅ Done |
| 10 | Atualizar `infra/terraform/main.tf` (adicionar `module "s3"` + passar ARN para IAM modules) | ✅ Done |
| 11 | Atualizar `infra/terraform/outputs.tf` (adicionar 2 outputs do módulo s3) | ✅ Done |
| 12 | Validar com `terraform validate` | ✅ Done |

## Test Results
```
terraform validate → Success! The configuration is valid.
```
