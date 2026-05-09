# Spec: 013 — API Gateway Terraform

**Feature Branch**: `013-api-gateway-terraform`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Criar módulo Terraform de API Gateway para expor a Lambda order-handler via HTTP

## Context
A Lambda `order-handler` já está provisionada via Terraform e tem um `lambda_invoke_arn` exportado. Porém, o diretório `infra/api-gateway/terraform/` está **vazio** — não existe nenhum trigger HTTP para invocar a Lambda. Sem API Gateway, o fluxo não pode ser iniciado por um cliente que faz upload de um diagrama de arquitetura.

O fluxo esperado é:
```
Cliente HTTP (POST /diagrams) → API Gateway → Lambda order-handler → S3 + DynamoDB + SQS
```

## Problem Statement
Precisamos de um módulo Terraform que:
1. Crie um API Gateway REST API com recurso `/diagrams`
2. Configure método `POST /diagrams` integrado com a Lambda order-handler
3. Suporte upload de imagem via body binário (base64 encoded no API Gateway)
4. Configure Binary Media Types para suporte a `image/png`, `image/jpeg`, `image/webp`
5. Faça deploy da API com stage configurável (dev/prod)
6. Exporte a URL de invocação como output

## User Scenarios & Testing

### User Story 1 - Upload de diagrama via HTTP (Priority: P1)

O cliente faz `POST /diagrams` com imagem no body, header `Content-Type: image/png` e `x-user-id`, e recebe resposta 201 com o `diagram_id`.

**Why this priority**: É o ponto de entrada do pipeline — sem ele, nada funciona.

**Independent Test**: `curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/diagrams -H "Content-Type: image/png" -H "x-user-id: user@email.com" --data-binary @diagram.png` retorna 201.

**Acceptance Scenarios**:

1. **Given** API Gateway deployado, **When** `POST /diagrams` com imagem PNG e headers válidos, **Then** Lambda é invocada, retorna 201 com `diagram_id`
2. **Given** API Gateway deployado, **When** `POST /diagrams` sem header `x-user-id`, **Then** Lambda retorna 400
3. **Given** API Gateway deployado, **When** `POST /diagrams` com `Content-Type: application/pdf`, **Then** Lambda retorna 400 (content type inválido)

---

### User Story 2 - Integração no main.tf (Priority: P1)

O módulo API Gateway é adicionado ao `main.tf` raiz, recebendo o `lambda_invoke_arn` e `lambda_function_name` dos outputs do módulo Lambda.

**Why this priority**: Sem integração no main.tf, o API Gateway não é criado com `terraform apply`.

**Acceptance Scenarios**:

1. **Given** módulos lambda e api-gateway no main.tf, **When** `terraform plan`, **Then** API Gateway, recurso `/diagrams`, método POST e integração Lambda são criados
2. **Given** `terraform apply` executado, **When** acessar output `api_gateway_url`, **Then** URL é válida e acessível

---

### User Story 3 - CORS (Priority: P2)

O API Gateway aceita requisições de origens diferentes (frontend web) via CORS headers.

**Why this priority**: Necessário se houver um frontend web, mas não bloqueia testes via curl/Postman.

**Acceptance Scenarios**:

1. **Given** CORS habilitado, **When** `OPTIONS /diagrams`, **Then** response com `Access-Control-Allow-Origin: *` e `Access-Control-Allow-Methods: POST,OPTIONS`

### Edge Cases

- Payload maior que 10MB → API Gateway rejeita com 413 (limite padrão)
- Request sem body → Lambda retorna 400 (tratado pelo handler existente)
- Stage inexistente na URL → API Gateway retorna 403

## Requirements

### Functional Requirements

- **FR-001**: Módulo DEVE criar `aws_api_gateway_rest_api` com nome `{project_name}-api-{environment}`
- **FR-002**: Módulo DEVE criar recurso `/diagrams` com método `POST`
- **FR-003**: Integração DEVE ser do tipo `AWS_PROXY` apontando para a Lambda order-handler
- **FR-004**: `Binary Media Types` DEVE incluir `image/png`, `image/jpeg`, `image/jpg`, `image/webp`
- **FR-005**: Módulo DEVE criar `aws_lambda_permission` para o API Gateway invocar a Lambda
- **FR-006**: Módulo DEVE criar `aws_api_gateway_deployment` e `aws_api_gateway_stage` com nome do environment
- **FR-007**: Módulo DEVE exportar `api_gateway_url` (invoke URL completa com stage)
- **FR-008**: Módulo DEVE exportar `api_gateway_id` e `api_gateway_stage_name`
- **FR-009**: Todos os recursos DEVEM receber tags `environment`, `project_name` e `common_tags`

### Key Entities

- **REST API**: O API Gateway em si
- **Resource**: Path `/diagrams`
- **Method**: `POST` no resource
- **Integration**: `AWS_PROXY` → Lambda
- **Stage**: Ambiente de deploy (dev, prod)

## Success Criteria

- **SC-001**: `terraform validate` e `terraform plan` passam sem erros
- **SC-002**: Após `apply`, `curl POST` na URL retorna resposta da Lambda
- **SC-003**: Upload de imagem binária chega na Lambda corretamente (base64 decoded)
- **SC-004**: URL de invocação exportada como output do Terraform

## Clarifications

### Session 2026-04-18

- **`user_id` vs `user_email`**: `user_id` é UUID. O header HTTP deve ser `x-user-email` (não `x-user-id`) para que a Lambda extraia o e-mail do cliente. Lambda gera `user_id` (UUID) internamente e propaga `user_email` nos eventos.
- **Encryption**: API Gateway usa TLS em trânsito por padrão. Sem KMS customizado.
- **Observability**: CloudWatch only — API Gateway access logs habilitados para CloudWatch Logs. Sem WAF ou custom metrics.

## Assumptions

- API Gateway REST API (v1) é suficiente — HTTP API (v2) é mais barato mas tem menos features
- Autenticação será adicionada em spec futura (API Key, Cognito, etc.) — sem auth por agora
- Throttling usa defaults do API Gateway (10.000 req/s burst)

## Out of Scope

- Autenticação/autorização (Cognito, API Key)
- Custom domain name (Route53 + ACM)
- WAF (Web Application Firewall)
- Endpoint `GET /diagrams/{id}` para consultar status — pode ser spec futura
- Rate limiting customizado

## Technical Design

### Estrutura de módulo
```
infra/api-gateway/terraform/
├── main.tf        # REST API, resource, method, integration, deployment, stage
├── variables.tf   # lambda_invoke_arn, lambda_function_name, environment, etc.
└── outputs.tf     # api_gateway_url, api_gateway_id
```

### Integração no main.tf raiz
```hcl
module "api_gateway" {
  source = "../api-gateway/terraform"

  environment          = var.environment
  project_name         = var.project_name
  common_tags          = var.common_tags
  lambda_invoke_arn    = module.lambda.lambda_invoke_arn
  lambda_function_name = module.lambda.lambda_function_name
}
```

### Fluxo de dependência
```
module "lambda" (existente)
       ↓ outputs (invoke_arn, function_name)
module "api_gateway" (novo)
       ↓ outputs (api_url)
```

### Outputs a adicionar no main.tf raiz
```hcl
output "api_gateway_url" {
  description = "URL de invocacao do API Gateway"
  value       = module.api_gateway.api_gateway_url
}
```

## Dependencies
- `infra/lambda/terraform/` — outputs `lambda_invoke_arn` e `lambda_function_name`
- `infra/terraform/main.tf` — ponto de integração
- `infra/terraform/outputs.tf` — expor URL do API Gateway

## Test / Validação
```powershell
# Terraform
cd tech-challenger/infra/terraform
terraform init
terraform validate
terraform plan -var="environment=dev"

# Após apply — teste funcional
$API_URL = terraform output -raw api_gateway_url
curl -X POST "$API_URL/diagrams" `
  -H "Content-Type: image/png" `
  -H "x-user-id: test@email.com" `
  --data-binary "@test-diagram.png"
```
