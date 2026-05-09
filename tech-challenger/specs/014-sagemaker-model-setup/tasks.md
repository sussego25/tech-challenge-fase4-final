# Tasks: 014 — SageMaker Model Setup e Configuração do Endpoint

**Input**: Design documents from `/specs/014-sagemaker-model-setup/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Prompt templates directory and script directory

- [ ] T001 [P] Verify `infra/llm/prompts/` directory exists (already in workspace structure)
- [ ] T002 [P] Verify `deploy/scripts/` directory exists (created in spec 012; create if not yet done)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: SageMaker variables and container image configuration that endpoint creation depends on

**⚠️ CRITICAL**: Without correct container image URI and model config, endpoint creation fails

- [ ] T003 Update `infra/sagemaker/terraform/variables.tf` — set `model_container_image` default to `"763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.1-tgi1.4.0-gpu-py310-cu121-ubuntu22.04"`; add `model_id` (default `"mistralai/Mistral-7B-Instruct-v0.2"`); add `instance_type` (default `"ml.g5.xlarge"`); document cost in description (~$1.41/h)
- [ ] T004 Update `infra/sagemaker/terraform/main.tf` — add `environment` block to `aws_sagemaker_model` container definition: `HF_MODEL_ID = var.model_id`, `SM_NUM_GPUS = "1"`, `MAX_INPUT_LENGTH = "4096"`, `MAX_TOTAL_TOKENS = "8192"`, `MAX_BATCH_PREFILL_TOKENS = "4096"`; update `aws_sagemaker_endpoint_configuration` to use `var.instance_type`
- [ ] T005 Update `infra/terraform/variables.tf` — set default of `sagemaker_model_container_image` to the HuggingFace TGI URI; add `sagemaker_model_id` and `sagemaker_instance_type` with passthrough to sagemaker module

**Checkpoint**: `terraform validate` passes with updated SageMaker variables

---

## Phase 3: User Story 1 — Endpoint SageMaker funcional (Priority: P1) 🎯 MVP

**Goal**: `terraform apply` with `enable_sagemaker=true` creates endpoint that responds to `invoke-endpoint`

**Independent Test**: `terraform plan` generates SageMaker Model, EndpointConfig, and Endpoint with correct container image and model environment

### Tests for User Story 1

- [ ] T006 [US1] Run `terraform validate` on `infra/sagemaker/terraform/` to verify module syntax
- [ ] T007 [US1] Run `terraform plan -var="environment=dev"` on `infra/terraform/` with `enable_sagemaker=true` and verify SageMaker resources appear with correct container image URI and model environment variables

---

## Phase 4: User Story 2 — Env vars completas em todos os serviços (Priority: P1)

**Goal**: All env vars of all services (Lambda, worker, notification) are documented and mapped to Terraform outputs

**Independent Test**: Env var mapping document covers 100% of env vars with Terraform output source

- [ ] T008 [P] [US2] Create `docs/deployment/env-var-mapping.md` — complete table mapping each Terraform output to service, env var name, and Helm path: `sqs_queue_url` → worker `SQS_QUEUE_URL`, `s3_bucket_name` → worker `S3_BUCKET`, `dynamodb_diagrams_table_name` → worker `DYNAMODB_TABLE`, `kafka_bootstrap_brokers` → worker+notification `KAFKA_BOOTSTRAP_SERVERS`, `sagemaker_endpoint_name` → worker `SAGEMAKER_ENDPOINT`, `dynamodb_notifications_table_name` → notification `DYNAMODB_TABLE`, ECR URLs → `image.repository`, IRSA ARNs → `serviceAccount.annotations`, `api_gateway_url` → documentation
- [ ] T009 [US2] Create `deploy/scripts/generate-values.sh` — reads `terraform output -json` via `jq`, generates `deploy/helm/worker-service/values-dev.yaml` and `deploy/helm/notification-service/values-dev.yaml` with real values from Terraform outputs (ECR URLs, IRSA ARNs, SQS URL, S3 bucket, DynamoDB tables, Kafka brokers, SageMaker endpoint)
- [ ] T010 [US2] Make `deploy/scripts/generate-values.sh` executable and add `jq` as documented prerequisite in script header

### Tests for User Story 2

- [ ] T011 [US2] Verify `deploy/scripts/generate-values.sh` runs without error when `terraform output -json` is available (or mock the output for dry-run test)

---

## Phase 5: User Story 3 — Prompt de análise otimizado (Priority: P2)

**Goal**: Externalized prompt template for architecture diagram analysis produces relevant SageMaker responses

**Independent Test**: Prompt file exists and is referenced in worker-service configuration

- [ ] T012 [US3] Create `infra/llm/prompts/diagram-analysis.txt` — structured prompt instructing LLM to identify components, communication patterns, architecture style, strengths, risks and improvements from diagram metadata
- [ ] T013 [US3] Verify `shared/libs/llm/sagemaker_client.py` loads prompt from external source (file, S3, or ConfigMap) — if hardcoded, document the path for future refactoring

---

## Phase 6: Polish & Cross-Cutting

- [ ] T014 Document SageMaker failure handling in `docs/deployment/env-var-mapping.md` — worker uses SQS visibility timeout + DLQ (max 3 retries) for SageMaker errors; add `SQS_DLQ_URL` to env var mapping table
- [ ] T015 Verify `user_email` field propagation: worker must include `user_email` in `AnalysisCompletedEvent` published to Kafka (verify in `shared/contracts/events/`)
- [ ] T016 Add CloudWatch alarm configuration notes to `docs/deployment/env-var-mapping.md` — SageMaker CloudWatch metrics to monitor: `Invocations`, `InvocationErrors`, `ModelLatency` (clarification: CloudWatch only, no Prometheus)
- [ ] T017 Run full `terraform init -upgrade` + `terraform validate` + `terraform plan -var="environment=dev" -var="enable_sagemaker=true"` on `infra/terraform/` and confirm clean plan

---

## Dependencies

```
T001-T002 ──→ T009, T012 (directories must exist)
T003-T005 ──→ T006-T007 (variables needed for validation)
T008 ──→ T009 (mapping doc informs script)
T009-T010 ──→ T011 (script must exist for test)

External:
Spec 010 ──→ T005 (enable_sagemaker in root variables)
Spec 012 ──→ T002, T009 (deploy/scripts directory, values-dev.yaml)
shared/contracts ──→ T015 (user_email in events)
```

## Parallel Execution

```
Phase 1: T001 + T002 [P]
Phase 2: T003 → T004 → T005
Phase 3: T006 → T007
Phase 4: T008 [P] → T009 → T010 → T011
Phase 5: T012 + T013 [P]
Phase 6: T014 + T015 + T016 [P] → T017
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 17 |
| User Story 1 (SageMaker endpoint) | 2 tasks (T006-T007) |
| User Story 2 (Env var mapping + script) | 4 tasks (T008-T011) |
| User Story 3 (Analysis prompt) | 2 tasks (T012-T013) |
| Setup + Foundational | 5 tasks (T001-T005) |
| Polish | 4 tasks (T014-T017) |
| Parallel opportunities | 5 groups |
| MVP scope | Phases 1-4 (endpoint + env mapping + generate-values script) |
| External dependencies | Specs 010, 012, shared/contracts |

**Next**: `/speckit.implement` to start implementation in phases
