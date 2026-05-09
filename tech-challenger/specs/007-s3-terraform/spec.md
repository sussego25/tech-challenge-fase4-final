# Spec 007 — S3 Terraform

## Contexto
O sistema precisa de um bucket S3 para armazenar os diagramas de arquitetura enviados pelos usuários. A Lambda (`order-handler`) faz upload das imagens e o `worker-service` faz download para processamento via SageMaker/YOLO. O bucket ainda não existe como recurso Terraform provisionado.

## Objetivo
Criar o módulo Terraform `infra/s3/terraform/` que provisiona o bucket S3 de diagramas, configura lifecycle, bloqueio de acesso público, e expõe ARN e nome como outputs. Conceder permissões de acesso ao bucket via IAM para Lambda (PutObject, GetObject) e worker-service (GetObject).

## Recursos a Provisionar

### Bucket S3
- **Nome**: `{project_name}-diagrams-{environment}-{account_id}` (inclui account_id para unicidade global)
- **Acesso público**: completamente bloqueado (`block_public_acls = true`, etc.)
- **Versionamento**: habilitado
- **Criptografia**: SSE-S3 (AES256)
- **Lifecycle**: expirar objetos após 90 dias em `dev`, 365 dias em outros environments

### IAM Policies
- Lambda: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` no bucket `diagrams`
- Worker: `s3:GetObject` no bucket `diagrams`

## Estrutura de Arquivos
```
infra/s3/terraform/
├── main.tf        # bucket + versionamento + criptografia + lifecycle + block public access
├── variables.tf   # aws_region, environment, project_name, common_tags, lifecycle_expiration_days
└── outputs.tf     # diagrams_bucket_name, diagrams_bucket_arn
```

## Integração com Root Module
O `infra/terraform/main.tf` adiciona `module "s3"` e passa o ARN para `module "lambda_iam"` e `module "worker_iam"`.

## Critérios de Aceitação
- `terraform validate` sem erros
- `terraform plan -var="environment=dev"` mostra criação do bucket com bloqueio de acesso público
- Lambda IAM role tem policy com `s3:PutObject` e `s3:GetObject`
- Worker IAM role tem policy com `s3:GetObject`
