# Plan 008 — Lambda Terraform

## Abordagem
Criar módulo em `infra/lambda/terraform/` separado do sub-módulo IAM existente. O módulo recebe o ARN da role como input (já provisionado pelo `lambda_iam`). Usar `archive_file` para criar o zip da função a partir do código-fonte.

## Nota sobre Dependências do Pacote
O `boto3` já está incluso no runtime Python do Lambda. O `pydantic>=2.0` precisa ser instalado junto com o código. Em produção/CI-CD, o pipeline deve executar `pip install -r requirements.txt -t .` no diretório da Lambda antes do `terraform apply`. Para o módulo Terraform, o `archive_file` empacota o diretório como está.

## Passos

1. **`infra/lambda/terraform/variables.tf`** — Variáveis:
   - `aws_region`, `environment`, `project_name`, `common_tags`
   - `lambda_role_arn` — ARN da role (vem do `lambda_iam`)
   - `s3_bucket_name` — nome do bucket de diagramas
   - `sqs_queue_url` — URL da fila SQS
   - `dynamodb_table_name` — nome da tabela de diagramas
   - `log_retention_days` — retenção de logs (default 14)

2. **`infra/lambda/terraform/main.tf`** — Recursos:
   - `data "archive_file" "order_handler"` — zip do diretório `order-handler`
   - `aws_cloudwatch_log_group "order_handler"` — `/aws/lambda/{name}`, retenção configurável
   - `aws_lambda_function "order_handler"` — função completa com env vars

3. **`infra/lambda/terraform/outputs.tf`** — Outputs:
   - `lambda_function_name`, `lambda_function_arn`, `lambda_invoke_arn`

4. **`infra/lambda/terraform/iam/iam_role.tf`** — Adicionar `aws_iam_role_policy_attachment` para `AWSLambdaBasicExecutionRole`

5. **`infra/terraform/main.tf`** — Adicionar `module "lambda"` com todos os inputs corretos

6. **`infra/terraform/outputs.tf`** — Adicionar outputs da Lambda

7. **Validar** — `terraform init -upgrade` + `terraform validate`

## Decisões Técnicas
- O zip é criado em `${path.module}/lambda_order_handler.zip` (local ao módulo, fora do git)
- `source_hash` no `aws_lambda_function` garante re-deploy quando o código muda
- `depends_on [aws_cloudwatch_log_group]` evita race condition de logs antes do grupo existir
- A policy `AWSLambdaBasicExecutionRole` é gerenciada pela AWS, não criar inline
