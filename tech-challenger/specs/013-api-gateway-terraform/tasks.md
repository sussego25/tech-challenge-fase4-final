# Tasks: 013 — API Gateway Terraform

**Input**: Design documents from `/specs/013-api-gateway-terraform/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Module variables definition

- [ ] T001 Create `infra/api-gateway/terraform/variables.tf` with inputs: `environment`, `project_name`, `common_tags`, `lambda_function_name` (string), `lambda_invoke_arn` (string), `lambda_function_arn` (string)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: REST API resource and Lambda integration that all user stories depend on

**⚠️ CRITICAL**: No endpoint can work without the REST API and Lambda integration

- [ ] T002 Create `infra/api-gateway/terraform/main.tf` — `aws_api_gateway_rest_api` with name `"${var.project_name}-api-${var.environment}"`, `binary_media_types = ["multipart/form-data", "application/octet-stream"]`
- [ ] T003 Add `aws_api_gateway_resource "diagrams"` with `path_part = "diagrams"` and parent = root resource ID in `infra/api-gateway/terraform/main.tf`
- [ ] T004 Add `aws_api_gateway_method "post_diagrams"` — `POST`, `authorization = "NONE"` in `infra/api-gateway/terraform/main.tf`
- [ ] T005 Add `aws_api_gateway_integration "lambda"` — `type = "AWS_PROXY"`, `integration_http_method = "POST"`, `uri = var.lambda_invoke_arn` in `infra/api-gateway/terraform/main.tf`
- [ ] T006 Add `aws_lambda_permission "api_gateway"` — `action = "lambda:InvokeFunction"`, `function_name = var.lambda_function_name`, `principal = "apigateway.amazonaws.com"`, `source_arn = "${rest_api.execution_arn}/*/*"` in `infra/api-gateway/terraform/main.tf`
- [ ] T007 Add `aws_api_gateway_deployment "main"` with `depends_on` on method and integration, and `aws_api_gateway_stage "dev"` with `stage_name = var.environment` in `infra/api-gateway/terraform/main.tf`
- [ ] T008 Create `infra/api-gateway/terraform/outputs.tf` — export `api_id`, `api_url` (full invoke URL with stage), `api_execution_arn`

**Checkpoint**: `terraform validate` passes on API Gateway module in isolation

---

## Phase 3: User Story 1 — Upload de diagrama via HTTP (Priority: P1) 🎯 MVP

**Goal**: Client sends `POST /diagrams` with image + `x-user-email` header, Lambda is invoked, returns 201

**Independent Test**: `terraform plan` generates all API Gateway resources; curl test after apply returns Lambda response

### Tests for User Story 1

- [ ] T009 [US1] Run `terraform validate` on `infra/api-gateway/terraform/` to verify module syntax
- [ ] T010 [US1] Run `terraform plan` on `infra/api-gateway/terraform/` and verify resources: REST API, resource `/diagrams`, POST method, Lambda integration, Lambda permission, deployment, stage

---

## Phase 4: User Story 2 — Integração no main.tf (Priority: P1)

**Goal**: API Gateway module added to root `main.tf`, receiving Lambda outputs automatically

**Independent Test**: `terraform plan` on root generates API Gateway resources linked to Lambda

- [ ] T011 [US2] Add `module "api_gateway"` to `infra/terraform/main.tf` with source `"../api-gateway/terraform"`, passing `lambda_function_name = module.lambda.function_name`, `lambda_invoke_arn = module.lambda.invoke_arn`, `lambda_function_arn = module.lambda.function_arn`, `environment`, `project_name`, `common_tags`
- [ ] T012 [US2] Verify `infra/lambda/terraform/outputs.tf` exports `function_name`, `invoke_arn`, `function_arn` — add missing outputs if needed
- [ ] T013 [US2] Add `api_gateway_url` and `api_gateway_id` outputs to `infra/terraform/outputs.tf`

### Tests for User Story 2

- [ ] T014 [US2] Run `terraform init -upgrade` + `terraform validate` on `infra/terraform/`
- [ ] T015 [US2] Run `terraform plan -var="environment=dev"` on `infra/terraform/` and verify API Gateway resources appear in plan linked to Lambda

---

## Phase 5: User Story 3 — CORS (Priority: P2)

**Goal**: API Gateway responds to OPTIONS preflight with CORS headers allowing cross-origin requests

**Independent Test**: `terraform plan` shows OPTIONS method with mock integration and CORS headers

- [ ] T016 [US3] Add `aws_api_gateway_method "options_diagrams"` — OPTIONS, `authorization = "NONE"` in `infra/api-gateway/terraform/main.tf`
- [ ] T017 [US3] Add `aws_api_gateway_integration "options_mock"` — `type = "MOCK"`, `request_templates = {"application/json" = "{\"statusCode\": 200}"}` in `infra/api-gateway/terraform/main.tf`
- [ ] T018 [US3] Add `aws_api_gateway_method_response "options_200"` with CORS response headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`) in `infra/api-gateway/terraform/main.tf`
- [ ] T019 [US3] Add `aws_api_gateway_integration_response "options"` with CORS `response_parameters` in `infra/api-gateway/terraform/main.tf`

### Tests for User Story 3

- [ ] T020 [US3] Run `terraform plan` and verify OPTIONS method, mock integration, and CORS response headers appear in plan

---

## Phase 6: Polish & Cross-Cutting

- [ ] T021 Update `aws_api_gateway_deployment` `depends_on` to include OPTIONS method and integration (from Phase 5)
- [ ] T022 Add CloudWatch access logging to `aws_api_gateway_stage` — `access_log_settings` with CloudWatch log group ARN (clarification: observability via CloudWatch only)
- [ ] T023 Run full `terraform init -upgrade` + `terraform validate` + `terraform plan -var="environment=dev"` on `infra/terraform/` and confirm clean plan with API Gateway + CORS + logging

---

## Dependencies

```
T001 ──→ T002-T008 (variables needed for main.tf)
T002-T008 ──→ T009-T010 (module must exist for validation)
T008 ──→ T011-T013 (outputs must be defined for root main.tf wiring)
T011-T013 ──→ T014-T015 (root wiring must exist for root validation)
T016-T019 ──→ T020-T021 (CORS resources for validation and deployment depends_on)

External:
Spec 008 ──→ T011-T012 (Lambda module outputs required)
```

## Parallel Execution

```
Phase 1: T001 (single task)
Phase 2: T002 → T003 → T004 + T005 [P] → T006 → T007 → T008
Phase 3: T009 → T010
Phase 4: T011 + T012 [P] → T013 → T014 → T015
Phase 5: T016 → T017 + T018 [P] → T019 → T020
Phase 6: T021 → T022 → T023
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 23 |
| User Story 1 (Upload via HTTP) | 2 tasks (T009-T010) |
| User Story 2 (main.tf integration) | 5 tasks (T011-T015) |
| User Story 3 (CORS) | 5 tasks (T016-T020) |
| Setup + Foundational | 8 tasks (T001-T008) |
| Polish | 3 tasks (T021-T023) |
| Parallel opportunities | 4 groups |
| MVP scope | Phases 1-4 (REST API + Lambda integration) |
| External dependency | Spec 008 (Lambda module outputs) |

**Next**: `/speckit.implement` to start implementation in phases
