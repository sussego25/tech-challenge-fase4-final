# Spec: 014 — SageMaker Model Setup e Configuração do Endpoint

**Feature Branch**: `014-sagemaker-model-setup`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Criar modelo no SageMaker (Mistral-7B ou outro LLM para análise de diagramas) e configurar env vars

## Context
O módulo Terraform do SageMaker já existe (`infra/sagemaker/terraform/`) e cria Model + Endpoint Config + Endpoint. Porém, para funcionar é necessário:
- Definir a imagem de container correta (HuggingFace TGI no ECR da AWS)
- Configurar o modelo LLM adequado para análise de diagramas de arquitetura
- Garantir que a variável `sagemaker_model_container_image` tenha o valor correto para a região
- Documentar o custo e o processo de warm-up do endpoint
- Configurar todas as variáveis de ambiente nos serviços que consomem o SageMaker

## Problem Statement
Precisamos:
1. Definir a imagem de container HuggingFace TGI correta para a região us-east-1
2. Escolher e documentar o modelo LLM (Mistral-7B-Instruct ou alternativa)
3. Criar prompts otimizados para análise de diagramas de arquitetura
4. Documentar o mapeamento completo de env vars de todos os serviços para todos os ambientes
5. Garantir que o `worker-service` envia o prompt correto ao endpoint

## User Scenarios & Testing

### User Story 1 - Endpoint SageMaker funcional (Priority: P1)

O operador faz `terraform apply` com `enable_sagemaker=true` e o endpoint fica disponível para receber invocações do worker-service.

**Why this priority**: Sem endpoint ativo, o worker não consegue gerar relatórios de análise.

**Independent Test**: `aws sagemaker-runtime invoke-endpoint` com payload de teste retorna resposta JSON com texto gerado.

**Acceptance Scenarios**:

1. **Given** `enable_sagemaker=true` e imagem de container definida, **When** `terraform apply`, **Then** endpoint SageMaker fica `InService` em ~10 minutos
2. **Given** endpoint ativo, **When** `invoke-endpoint` com prompt de teste, **Then** resposta contém `generated_text` com análise coerente
3. **Given** endpoint ativo, **When** worker-service envia prompt com metadados de diagrama, **Then** resposta contém componentes de arquitetura identificados

---

### User Story 2 - Env vars completas em todos os serviços (Priority: P1)

Todas as variáveis de ambiente de todos os serviços (Lambda, worker, notification) estão documentadas e mapeadas para os outputs do Terraform.

**Why this priority**: Uma variável faltando ou com valor errado quebra o fluxo inteiro.

**Acceptance Scenarios**:

1. **Given** todos os outputs do Terraform, **When** o operador consulta o mapeamento, **Then** consegue preencher 100% das env vars de todos os serviços
2. **Given** `terraform output -json`, **When** script processa os outputs, **Then** gera `values-dev.yaml` para Helm com todos os valores

---

### User Story 3 - Prompt de análise otimizado (Priority: P2)

O prompt enviado pelo worker ao SageMaker produz análises relevantes de diagramas de arquitetura.

**Why this priority**: Um prompt genérico produz respostas pobres; precisa ser calibrado para o domínio.

**Acceptance Scenarios**:

1. **Given** diagrama de arquitetura AWS com ELB, EC2, RDS, **When** prompt é enviado, **Then** resposta identifica esses componentes e sugere melhorias (ex: auto-scaling, multi-AZ)
2. **Given** diagrama simples com apenas um monolito, **When** prompt é enviado, **Then** resposta sugere decomposição em microsserviços

### Edge Cases

- Endpoint em `Creating` demora mais de 15 min → Timeout no Terraform; solução: aumentar timeout
- Modelo retorna resposta truncada → `MAX_TOTAL_TOKENS` precisa ser suficiente (8192 default)
- Instância GPU indisponível na região → Erro de `InsufficientInstanceCapacity`; solução: usar região/instância alternativa

## Requirements

### Functional Requirements

- **FR-001**: A variável `sagemaker_model_container_image` DEVE usar a imagem oficial HuggingFace TGI do ECR público da AWS para a região `us-east-1`
- **FR-002**: Modelo padrão DEVE ser `mistralai/Mistral-7B-Instruct-v0.2` (bom equilíbrio custo/qualidade)
- **FR-003**: Instância padrão DEVE ser `ml.g4dn.xlarge` (1 GPU NVIDIA T4, ~$0.73/hora)
- **FR-004**: Prompt do worker DEVE incluir instruções para: identificar componentes, avaliar patterns, sugerir melhorias
- **FR-005**: DEVE existir documentação mapeando cada output do Terraform para a env var de cada serviço
- **FR-006**: DEVE existir script que gere `values-dev.yaml` a partir de `terraform output`
- **FR-007**: Prompts DEVEM ser externalizados em `infra/llm/prompts/` (não hardcoded no worker)

### Key Entities

- **SageMaker Endpoint**: Endpoint HTTP gerenciado que serve o modelo LLM
- **HuggingFace TGI**: Container de inferência otimizado para text generation
- **Mistral-7B-Instruct**: Modelo LLM de 7B parâmetros com bom desempenho em tarefas de instrução

## Success Criteria

- **SC-001**: Endpoint SageMaker responde a invocações em menos de 30 segundos
- **SC-002**: Worker-service gera relatório de análise com componentes identificados
- **SC-003**: 100% das env vars estão documentadas com fonte (Terraform output ou valor fixo)
- **SC-004**: Script gera `values-dev.yaml` automaticamente

## Assumptions

- Conta AWS tem quota para instâncias `ml.g4dn.xlarge` na região us-east-1
- O modelo Mistral-7B é suficiente para análise de texto extraído de diagramas (não processa imagem diretamente — YOLO extrai elementos, LLM analisa texto)
- O custo do endpoint (~$0.73/h = ~$525/mês) é aceitável para o ambiente dev

## Clarifications

### Session 2026-04-18

- **SageMaker Failure Handling**: Worker usa SQS visibility timeout + DLQ com max 3 retries. Worker catches SageMaker errors (timeout, 5xx), mensagem retorna à fila após visibility timeout. Após 3 falhas, mensagem vai para DLQ para inspeção manual. Não há retry in-process com exponential backoff.
- **Encryption**: SageMaker usa chaves gerenciadas pela AWS (SSE). Sem KMS customizado para modelo ou endpoint.
- **Observability**: CloudWatch only — SageMaker CloudWatch metrics (Invocations, InvocationErrors, ModelLatency) + CloudWatch Alarms. Sem Prometheus/Grafana.
- **`user_email` field**: O prompt de análise não usa `user_email`, mas o worker deve propagar `user_email` nos eventos Kafka `AnalysisCompletedEvent` para o notification-service.

## Out of Scope

- Fine-tuning do modelo para o domínio específico de arquitetura
- Endpoint com auto-scaling (0 → N instâncias) — pode ser spec futura para otimizar custo
- Modelo YOLO para detecção visual de elementos no diagrama — já é outra camada
- Batch transform (processamento em lote) — o fluxo é em tempo real

## Technical Design

### Imagem de container (HuggingFace TGI)

Para `us-east-1`, a imagem oficial AWS Deep Learning Container é:
```
763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.1-tgi1.4.0-gpu-py310-cu121-ubuntu22.04
```

### Mapeamento completo de Env Vars

#### order-handler (Lambda)
| Env Var | Fonte Terraform | Valor exemplo |
|---|---|---|
| `S3_BUCKET` | `module.s3.diagrams_bucket_name` | `tech-challenger-diagrams-dev` |
| `SQS_QUEUE_URL` | `module.sqs.architecture_analysis_queue_url` | `https://sqs.us-east-1.amazonaws.com/...` |
| `DYNAMODB_TABLE` | `module.dynamodb.diagrams_table_name` | `tech-challenger-diagrams-dev` |
| `AWS_REGION` | `var.aws_region` | `us-east-1` |

#### worker-service (EKS)
| Env Var | Fonte Terraform | Valor exemplo |
|---|---|---|
| `SQS_QUEUE_URL` | `module.sqs.architecture_analysis_queue_url` | `https://sqs.us-east-1.amazonaws.com/...` |
| `S3_BUCKET` | `module.s3.diagrams_bucket_name` | `tech-challenger-diagrams-dev` |
| `DYNAMODB_TABLE` | `module.dynamodb.diagrams_table_name` | `tech-challenger-diagrams-dev` |
| `KAFKA_BOOTSTRAP_SERVERS` | `module.kafka[0].bootstrap_brokers` | `b-1.tech-challenger...:9092,b-2...` |
| `KAFKA_TOPIC_ANALYSIS_COMPLETED` | fixo | `analysis-completed` |
| `SAGEMAKER_ENDPOINT` | `module.sagemaker[0].endpoint_name` | `tech-challenger-llm-dev` |
| `AWS_REGION` | `var.aws_region` | `us-east-1` |

#### notification-service (EKS)
| Env Var | Fonte Terraform | Valor exemplo |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `module.kafka[0].bootstrap_brokers` | `b-1.tech-challenger...:9092,b-2...` |
| `KAFKA_TOPIC_ANALYSIS_COMPLETED` | fixo | `analysis-completed` |
| `KAFKA_GROUP_ID` | fixo | `notification-service` |
| `DYNAMODB_TABLE` | `module.dynamodb.notifications_table_name` | `tech-challenger-notifications-dev` |
| `AWS_REGION` | `var.aws_region` | `us-east-1` |
| `SES_SENDER_EMAIL` | manual (SES verified) | `noreply@techchallenger.com` |

### Script generate-values.sh
```bash
#!/bin/bash
# Gera values-dev.yaml a partir dos outputs do Terraform

cd infra/terraform
OUTPUTS=$(terraform output -json)

# Worker
cat > ../../deploy/helm/worker-service/values-dev.yaml <<EOF
image:
  repository: $(echo $OUTPUTS | jq -r '.ecr_worker_url.value')
  tag: "1.0.0"
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "$(echo $OUTPUTS | jq -r '.worker_service_role_arn.value')"
env:
  AWS_REGION: "$(echo $OUTPUTS | jq -r '.aws_region.value // "us-east-1"')"
  SQS_QUEUE_URL: "$(echo $OUTPUTS | jq -r '.architecture_analysis_queue_url.value')"
  S3_BUCKET: "$(echo $OUTPUTS | jq -r '.diagrams_bucket_name.value')"
  DYNAMODB_TABLE: "$(echo $OUTPUTS | jq -r '.diagrams_table_name.value')"
  KAFKA_BOOTSTRAP_SERVERS: "$(echo $OUTPUTS | jq -r '.kafka_bootstrap_brokers.value')"
  KAFKA_TOPIC_ANALYSIS_COMPLETED: "analysis-completed"
  SAGEMAKER_ENDPOINT: "$(echo $OUTPUTS | jq -r '.sagemaker_endpoint_name.value')"
EOF

echo "Generated values-dev.yaml for worker-service and notification-service"
```

### Prompt de análise (infra/llm/prompts/architecture_analysis.txt)
```
You are an expert software architect. Analyze the following architecture diagram description and provide:

1. **Components Identified**: List all architecture components (load balancers, servers, databases, queues, caches, etc.)
2. **Architecture Patterns**: Identify patterns used (microservices, monolith, event-driven, CQRS, etc.)
3. **Strengths**: What is well-designed
4. **Weaknesses**: Potential issues (single points of failure, missing redundancy, security gaps)
5. **Recommendations**: Specific improvements with justification

Diagram ID: {diagram_id}
Image size: {image_size} bytes
Detected elements: {elements}

Provide a structured analysis report.
```

## Dependencies
- **Spec 009** — VPC para SageMaker VPC endpoint (se necessário)
- **Spec 010** — `enable_sagemaker=true` e integração no main.tf
- **Spec 012** — Deploy dos serviços com as env vars corretas
- `infra/sagemaker/terraform/` — módulo existente
- `services/worker-service/src/domain/analysis_service.py` — consome o endpoint
- `shared/libs/llm/sagemaker_client.py` — client que invoca o endpoint

## Test / Validação
```bash
# Teste direto do endpoint SageMaker
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name tech-challenger-llm-dev \
  --content-type application/json \
  --body '{"inputs": "Analyze this architecture: Load Balancer -> 2 EC2 instances -> RDS MySQL"}' \
  response.json

cat response.json | jq '.generated_text'

# Verificar endpoint status
aws sagemaker describe-endpoint --endpoint-name tech-challenger-llm-dev --query EndpointStatus
```

## Custo estimado (ambiente dev)
| Recurso | Tipo | Custo/hora | Custo/mês (24/7) |
|---|---|---|---|
| SageMaker Endpoint | ml.g4dn.xlarge | $0.736 | ~$530 |
| EKS Cluster | Control plane | $0.10 | ~$72 |
| MSK (2 brokers) | kafka.m5.large | $0.21 x 2 | ~$302 |
| NAT Gateway | Por hora + dados | $0.045 | ~$32 |
| **Total estimado** | | | **~$936/mês** |

> **Dica**: Para reduzir custo em dev, considerar endpoint SageMaker serverless (spec futura) ou desligar fora do horário comercial.
