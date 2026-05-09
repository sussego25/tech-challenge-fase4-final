# Plan: 013 — API Gateway Terraform

## Objective
Criar REST API no API Gateway com rota `POST /diagrams`, integração AWS_PROXY com Lambda order-handler, suporte a Binary Media Types para upload de imagens e deployment no stage `dev`.

## Architecture Decisions
- **REST API (v1) sobre HTTP API (v2)** — REST API suporta `AWS_PROXY` com Lambda, Binary Media Types nativo, e request validation; HTTP API é mais simples mas limita controle
- **Binary Media Types** — `multipart/form-data` e `application/octet-stream` para aceitar uploads de diagramas diretamente (até 10 MB, limite Lambda payload)
- **CORS habilitado** — preflight `OPTIONS` automático via mock integration; permite consumo de front-end futuro
- **Stage único `dev`** — auto-deploy; stages adicionais (staging, prod) são expansão futura
- **Lambda permission explícita** — `aws_lambda_permission` para que API Gateway invoque a função Lambda

## Flow
```
Client
  │
  ├─ POST /diagrams (multipart/form-data)
  │    Content-Type: multipart/form-data; boundary=...
  │    Body: arquivo de imagem do diagrama
  │
  └─→ API Gateway (REST)
       ├─ Resource: /diagrams
       ├─ Method: POST (AWS_PROXY)
       ├─ Binary Media Types: multipart/form-data, application/octet-stream
       ├─ Integration: Lambda (order-handler)
       │    └─ event["body"] = base64-encoded payload
       └─ Stage: dev
            └─ URL: https://{api-id}.execute-api.{region}.amazonaws.com/dev/diagrams
```

## Module Structure
```
infra/api-gateway/terraform/          # PREENCHER (atualmente vazio)
├── main.tf        # REST API, resource, methods, integration, deployment, stage
├── variables.tf   # lambda_function_name, lambda_invoke_arn, environment, project_name
└── outputs.tf     # api_url, api_id, stage_name

infra/terraform/                       # MODIFICAR
├── main.tf        # adicionar module "api_gateway"
├── variables.tf   # (sem alterações — lambda já existe)
└── outputs.tf     # adicionar api_gateway_url
```

## Implementation Steps

### Step 1 — Criar `infra/api-gateway/terraform/variables.tf`
- `environment`, `project_name`, `common_tags`
- `lambda_function_name` (string) — nome da Lambda para permission
- `lambda_invoke_arn` (string) — ARN de invocação da Lambda
- `lambda_function_arn` (string) — ARN da função para `aws_lambda_permission`

### Step 2 — Criar `infra/api-gateway/terraform/main.tf`
Recursos na ordem:
1. `aws_api_gateway_rest_api "main"` — nome, description, `binary_media_types = ["multipart/form-data", "application/octet-stream"]`
2. `aws_api_gateway_resource "diagrams"` — path_part `"diagrams"`, parent = rest_api root
3. `aws_api_gateway_method "post_diagrams"` — `POST`, `authorization = "NONE"` (para MVP; autenticação é expansão futura)
4. `aws_api_gateway_integration "lambda"` — `type = "AWS_PROXY"`, `integration_http_method = "POST"`, `uri = var.lambda_invoke_arn`
5. `aws_api_gateway_method "options_diagrams"` — OPTIONS para CORS
6. `aws_api_gateway_integration "options_mock"` — `type = "MOCK"`, `request_templates = {"application/json" = "{\"statusCode\": 200}"}`
7. `aws_api_gateway_method_response "options_200"` — headers CORS (`Access-Control-Allow-*`)
8. `aws_api_gateway_integration_response "options"` — response_parameters com headers CORS
9. `aws_api_gateway_deployment "main"` — `depends_on` nos métodos e integrações
10. `aws_api_gateway_stage "dev"` — `stage_name = var.environment`
11. `aws_lambda_permission "api_gateway"` — `action = "lambda:InvokeFunction"`, `principal = "apigateway.amazonaws.com"`, `source_arn = "${rest_api.execution_arn}/*/*"`

### Step 3 — Criar `infra/api-gateway/terraform/outputs.tf`
- `api_id` — ID do REST API
- `api_url` — `"https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.dev.stage_name}"`
- `api_execution_arn` — para referência em policies

### Step 4 — Atualizar `infra/terraform/main.tf`
- Adicionar `module "api_gateway"` com source `"../api-gateway/terraform"`
- Passar `lambda_function_name = module.lambda.function_name`, `lambda_invoke_arn = module.lambda.invoke_arn`, `lambda_function_arn = module.lambda.function_arn`
- Sem `count` — API Gateway é sempre necessário

### Step 5 — Atualizar `infra/terraform/outputs.tf`
- Adicionar `api_gateway_url` e `api_gateway_id`

## Dependencies
- **Spec 008** (Lambda) — precisa de `function_name`, `invoke_arn`, `function_arn` do Lambda
- `infra/lambda/terraform/outputs.tf` deve expor os 3 valores acima (verificar se já expõe)
- Não depende de VPC/networking — API Gateway é regional e público

## Validation
```powershell
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate
terraform plan -var="environment=dev"
```

Após apply:
```bash
# Testar endpoint
curl -X POST \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/diagrams" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-diagram.png" \
  -F "user_email=test@example.com"

# Verificar CORS
curl -X OPTIONS \
  "https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/diagrams" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep "Access-Control"
```
