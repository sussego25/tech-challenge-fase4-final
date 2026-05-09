# Plan: 014 — SageMaker Model Setup

## Objective
Definir a imagem de container HuggingFace TGI para o SageMaker endpoint, documentar o mapeamento de variáveis de ambiente entre Terraform outputs e os 3 serviços, criar script para gerar `values-dev.yaml` a partir de `terraform output -json` e externalizar prompts do LLM.

## Architecture Decisions
- **HuggingFace TGI (Text Generation Inference)** — container oficial AWS otimizado para inferência de LLMs; suporta Mistral-7B out-of-the-box
- **Mistral-7B-Instruct-v0.2** — modelo instrução-tuned de 7B parâmetros; balanço entre qualidade e custo (`ml.g5.xlarge` ~$1.41/h)
- **Script `generate-values.sh`** — automatiza extração de terraform outputs e geração de values-dev.yaml para ambos os serviços; evita copiar valores manualmente
- **Prompts externalizados em arquivos** — `infra/llm/prompts/` já existe; adicionar template de análise de diagrama que o worker-service carrega de S3 ou ConfigMap
- **`ml.g5.xlarge`** — GPU A10G 24GB; suficiente para Mistral-7B quantizado; menor instância GPU com capacidade adequada

## Flow
```
terraform apply
  └─ module "sagemaker"
       ├─ aws_sagemaker_model (container image URI + model data)
       ├─ aws_sagemaker_endpoint_configuration (instance type, volume)
       └─ aws_sagemaker_endpoint → endpoint_name
                                      │
generate-values.sh                    │
  ├─ terraform output -json ──────────┘
  ├─ Extrai: sqs_queue_url, s3_bucket_name, dynamodb_table_name,
  │          kafka_bootstrap_brokers, sagemaker_endpoint_name,
  │          ecr_repository_urls, worker_role_arn, notification_role_arn,
  │          api_gateway_url
  ├─ Gera: deploy/helm/worker-service/values-dev.yaml
  └─ Gera: deploy/helm/notification-service/values-dev.yaml

worker-service Pod
  └─ SageMakerClient.invoke(endpoint_name, prompt)
       └─ sagemaker-runtime.invoke_endpoint(
            EndpointName=<SAGEMAKER_ENDPOINT>,
            Body=json.dumps({"inputs": prompt, "parameters": {...}})
          )
```

## Module Structure
```
infra/sagemaker/terraform/             # MODIFICAR
├── main.tf         # atualizar container_image default, environment vars do model
├── variables.tf    # refinar defaults, documentar imagem URI
└── outputs.tf      # (sem alterações necessárias)

infra/llm/prompts/                     # PREENCHER
└── diagram-analysis.txt               # NOVO — prompt template para análise

deploy/scripts/
└── generate-values.sh                 # NOVO — terraform output → values-dev.yaml

docs/deployment/
└── env-var-mapping.md                 # NOVO — mapeamento completo

infra/terraform/
└── variables.tf    # MODIFICAR — default da imagem SageMaker
```

## Implementation Steps

### Step 1 — Atualizar `infra/sagemaker/terraform/variables.tf`
- Alterar `model_container_image` default para:
  `"763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.1-tgi1.4.0-gpu-py310-cu121-ubuntu22.04"`
- Adicionar `model_id` (default `"mistralai/Mistral-7B-Instruct-v0.2"`)
- Adicionar `instance_type` (default `"ml.g5.xlarge"`)
- Documentar na description: custo estimado, requisitos GPU

### Step 2 — Atualizar `infra/sagemaker/terraform/main.tf`
- No `aws_sagemaker_model`, adicionar environment no container:
  ```hcl
  environment = {
    HF_MODEL_ID             = var.model_id
    SM_NUM_GPUS             = "1"
    MAX_INPUT_LENGTH        = "4096"
    MAX_TOTAL_TOKENS        = "8192"
    MAX_BATCH_PREFILL_TOKENS = "4096"
  }
  ```
- No `aws_sagemaker_endpoint_configuration`, referenciar `var.instance_type`

### Step 3 — Atualizar `infra/terraform/variables.tf`
- Alterar default de `sagemaker_model_container_image` para a URI completa do Step 1
- Adicionar `sagemaker_model_id` e `sagemaker_instance_type` com passthrough para o módulo

### Step 4 — Criar `infra/llm/prompts/diagram-analysis.txt`
```
You are an expert software architect analyzing architecture diagrams.

Analyze the following architecture diagram and provide:
1. **Components identified**: List all services, databases, queues, and external systems
2. **Communication patterns**: Describe how components interact (sync/async, protocols)
3. **Architecture style**: Identify the pattern (microservices, monolith, event-driven, etc.)
4. **Strengths**: What the architecture does well
5. **Risks and improvements**: Potential issues and recommendations

Be specific and reference the actual components visible in the diagram.
```

### Step 5 — Criar `docs/deployment/env-var-mapping.md`
Tabela de mapeamento:

| Terraform Output | Service | Env Var | Helm Path |
|---|---|---|---|
| `sqs_queue_url` | worker | `SQS_QUEUE_URL` | `env.SQS_QUEUE_URL` |
| `s3_bucket_name` | worker | `S3_BUCKET` | `env.S3_BUCKET` |
| `dynamodb_diagrams_table_name` | worker | `DYNAMODB_TABLE` | `env.DYNAMODB_TABLE` |
| `kafka_bootstrap_brokers` | worker, notification | `KAFKA_BOOTSTRAP_SERVERS` | `env.KAFKA_BOOTSTRAP_SERVERS` |
| `sagemaker_endpoint_name` | worker | `SAGEMAKER_ENDPOINT` | `env.SAGEMAKER_ENDPOINT` |
| `dynamodb_notifications_table_name` | notification | `DYNAMODB_TABLE` | `env.DYNAMODB_TABLE` |
| `ecr_repository_urls["worker-service"]` | worker | — | `image.repository` |
| `ecr_repository_urls["notification-service"]` | notification | — | `image.repository` |
| `worker_service_role_arn` | worker | — | `serviceAccount.annotations` |
| `notification_service_role_arn` | notification | — | `serviceAccount.annotations` |
| `api_gateway_url` | (documentation) | — | — |

### Step 6 — Criar `deploy/scripts/generate-values.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
# 1. cd infra/terraform && terraform output -json > /tmp/tf-outputs.json
# 2. Extrair valores com jq
# 3. Gerar deploy/helm/worker-service/values-dev.yaml via heredoc
# 4. Gerar deploy/helm/notification-service/values-dev.yaml via heredoc
# 5. Print: "Generated values-dev.yaml for both services"
```
- Usa `jq` para parsing (dependency declarada no README)
- Gera YAML válido sem dependência de template engine

## Dependencies
- **Spec 010** — IRSA roles (ARNs necessários para values-dev.yaml)
- **Spec 012** — ECR repos (URLs necessárias para image.repository)
- `infra/sagemaker/terraform/` já existe com estrutura base
- `jq` necessário no PATH para `generate-values.sh`
- Acesso AWS com quota para `ml.g5.xlarge` na região (pode precisar de service quota request)

## Validation
```powershell
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate
terraform plan -var="environment=dev" -var="enable_sagemaker=true"
```

Após apply:
```bash
# Verificar endpoint
aws sagemaker describe-endpoint \
  --endpoint-name $(terraform output -raw sagemaker_endpoint_name) \
  --query "{Status:EndpointStatus,InstanceType:ProductionVariants[0].CurrentInstanceCount}"

# Testar invocação
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name $(terraform output -raw sagemaker_endpoint_name) \
  --content-type "application/json" \
  --body '{"inputs": "Describe a microservices architecture", "parameters": {"max_new_tokens": 100}}' \
  /tmp/sagemaker-response.json

cat /tmp/sagemaker-response.json

# Testar generate-values.sh
cd tech-challenger
bash deploy/scripts/generate-values.sh
cat deploy/helm/worker-service/values-dev.yaml
cat deploy/helm/notification-service/values-dev.yaml
```

## Cost Estimate
| Resource | Tipo | Custo/hora | Custo/mês (24/7) |
|---|---|---|---|
| SageMaker endpoint | ml.g5.xlarge | ~$1.41 | ~$1,015 |
| EBS volume (model) | 50 GB gp3 | — | ~$4 |
| **Total** | | | **~$1,019/mês** |

> **Dica**: Para reduzir custo em dev, desligar endpoint quando não em uso (`aws sagemaker delete-endpoint`) e recriar com `terraform apply` quando necessário.
