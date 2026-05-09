# Spec 008 — Lambda Terraform

## Contexto
A Lambda `order-handler` é o entry point do sistema via API Gateway. O módulo IAM (`infra/lambda/terraform/iam/`) já existe com a role e policies (SQS, DynamoDB, S3). Falta provisionar o recurso `aws_lambda_function` em si: código, runtime, variáveis de ambiente, logs e configurações.

## Objetivo
Criar o módulo Terraform `infra/lambda/terraform/` que provisiona a função Lambda `order-handler`, grupo de logs no CloudWatch, e anexa a policy básica de execução (CloudWatch Logs). Também integrar ao módulo raiz.

## Recursos a Provisionar

### Lambda Function
- **Nome**: `{project_name}-order-handler-{environment}`
- **Runtime**: `python3.11`
- **Handler**: `handler.lambda_handler`
- **Timeout**: 30s
- **Memory**: 256 MB
- **Role**: ARN da role criada pelo módulo `lambda_iam`
- **Package**: zip criado via `archive_file` do diretório `services/lambda-functions/order-handler`

### Variáveis de Ambiente da Lambda
- `S3_BUCKET` — nome do bucket de diagramas
- `SQS_QUEUE_URL` — URL da fila SQS
- `DYNAMODB_TABLE` — nome da tabela de diagramas
- `AWS_REGION` — região AWS

### CloudWatch Log Group
- Nome: `/aws/lambda/{function_name}`
- Retenção: 14 dias em `dev`, configurável por variável

### IAM — Basic Execution Policy
- Adicionar `AWSLambdaBasicExecutionRole` managed policy ao IAM role existente (permite escrever logs no CloudWatch)

## Estrutura de Arquivos
```
infra/lambda/terraform/
├── iam/                  # já existe
├── variables.tf          # aws_region, environment, project_name, lambda_role_arn,
│                         # s3_bucket_name, sqs_queue_url, dynamodb_table_name,
│                         # log_retention_days, common_tags
├── main.tf               # archive_file + aws_lambda_function + aws_cloudwatch_log_group
└── outputs.tf            # lambda_function_name, lambda_function_arn, lambda_invoke_arn
```

## Integração com Root Module
O `infra/terraform/main.tf` adiciona `module "lambda"` passando os valores dos módulos `s3`, `sqs`, `dynamodb` e `lambda_iam`.

## Critérios de Aceitação
- `terraform validate` sem erros
- `terraform plan` mostra criação da função Lambda com as variáveis de ambiente corretas
- Log group `/aws/lambda/tech-challenger-order-handler-dev` criado com retenção de 14 dias
