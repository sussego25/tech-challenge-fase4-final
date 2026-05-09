# Tasks: 010 — Habilitar EKS, Kafka e SageMaker no Terraform

**Input**: Design documents from `/specs/010-enable-optional-modules/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: New IAM module directory for notification-service

- [ ] T001 [P] Create `infra/eks/terraform/iam-notification/variables.tf` with inputs: `environment`, `project_name`, `common_tags`, `eks_oidc_provider_arn`, `eks_oidc_provider_url`, `k8s_namespace` (default `"default"`), `k8s_service_account_name` (default `"notification-service"`), `dynamodb_notifications_table_arn`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: IAM roles and policies that user stories depend on

**⚠️ CRITICAL**: Module wiring in main.tf depends on these roles existing

- [ ] T002 Create `infra/eks/terraform/iam-notification/iam_role.tf` — IRSA role `notification-service` with trust policy for OIDC, `aws_iam_role_policy` with `dynamodb:PutItem`, `dynamodb:UpdateItem` on `var.dynamodb_notifications_table_arn`
- [ ] T003 Create `infra/eks/terraform/iam-notification/outputs.tf` — export `notification_service_role_arn`
- [ ] T004 Add `sagemaker_endpoint_arn` variable (default `""`) to `infra/eks/terraform/iam/variables.tf`
- [ ] T005 Add conditional `aws_iam_role_policy "worker_sagemaker_policy"` (count = `var.sagemaker_endpoint_arn != "" ? 1 : 0`) with `sagemaker:InvokeEndpoint` to `infra/eks/terraform/iam/iam_role.tf`

**Checkpoint**: Both IAM modules pass `terraform validate` in isolation

---

## Phase 3: User Story 1 — Ativação integrada dos módulos (Priority: P1) 🎯 MVP

**Goal**: All optional modules (EKS, Kafka, SageMaker) activate with correct auto-wiring from networking outputs

**Independent Test**: `terraform plan` with flags enabled generates all resources without missing variable errors

- [ ] T006 [US1] Update `module "eks"` in `infra/terraform/main.tf` — replace `var.eks_vpc_id` → `module.networking.vpc_id`, `var.eks_subnet_ids` → `module.networking.private_subnet_ids`
- [ ] T007 [US1] Update `module "kafka"` in `infra/terraform/main.tf` — replace `var.kafka_vpc_id` → `module.networking.vpc_id`, `var.kafka_subnet_ids` → `module.networking.private_subnet_ids`, `var.kafka_allowed_cidr_blocks` → `module.networking.private_subnet_cidrs`
- [ ] T008 [US1] Update `module "worker_iam"` in `infra/terraform/main.tf` — replace `var.eks_oidc_provider_arn` → `module.eks[0].oidc_provider_arn`, `var.eks_oidc_provider_url` → `module.eks[0].oidc_provider_url`; add `sagemaker_endpoint_arn = try(module.sagemaker[0].endpoint_arn, "")`

### Tests for User Story 1

- [ ] T009 [US1] Run `terraform validate` on `infra/terraform/` and confirm no errors
- [ ] T010 [US1] Run `terraform plan` with `enable_eks=true`, `enable_kafka=true`, `enable_sagemaker=true` and verify EKS uses networking VPC/subnets, Kafka uses networking CIDRs, worker_iam uses EKS OIDC

---

## Phase 4: User Story 2 — IAM do worker com SageMaker (Priority: P1)

**Goal**: Worker-service IRSA role includes `sagemaker:InvokeEndpoint` permission

**Independent Test**: `terraform plan` shows SageMaker policy in worker IAM when `enable_sagemaker=true`

- [ ] T011 [US2] Verify `terraform plan` output includes `aws_iam_role_policy.worker_sagemaker_policy` when `sagemaker_endpoint_arn != ""`
- [ ] T012 [US2] Verify worker IAM policy resource ARN matches `module.sagemaker[0].endpoint_arn`

---

## Phase 5: User Story 3 — IRSA para notification-service (Priority: P1)

**Goal**: Notification-service has its own IRSA role with DynamoDB PutItem on notifications table

**Independent Test**: `terraform plan` shows notification IAM role and DynamoDB policy

- [ ] T013 [US3] Add `enable_notification_iam` variable (bool, default `false`) to `infra/terraform/variables.tf`
- [ ] T014 [US3] Add `module "notification_iam"` block to `infra/terraform/main.tf` with `count = var.enable_notification_iam ? 1 : 0`, source `"../eks/terraform/iam-notification"`, wired to EKS OIDC and DynamoDB notifications ARN
- [ ] T015 [US3] Add `notification_service_role_arn` output to `infra/terraform/outputs.tf` (using `try(module.notification_iam[0].notification_service_role_arn, null)`)

### Tests for User Story 3

- [ ] T016 [US3] Run `terraform plan` with `enable_notification_iam=true` and verify notification IRSA role and DynamoDB policy appear in plan

---

## Phase 6: Polish & Cross-Cutting

- [ ] T017 Create `infra/terraform/terraform.tfvars.example` with all variables for full activation: `environment`, `project_name`, `aws_region`, `enable_eks`, `enable_kafka`, `enable_sagemaker`, `enable_worker_iam`, `enable_notification_iam`, SageMaker container image/model/instance vars
- [ ] T018 Deprecate manual VPC/subnet variables in `infra/terraform/variables.tf` — mark `eks_vpc_id`, `eks_subnet_ids`, `kafka_vpc_id`, `kafka_subnet_ids` as deprecated in description
- [ ] T019 Run full `terraform init -upgrade` + `terraform validate` + `terraform plan -var-file="terraform.tfvars.example"` on `infra/terraform/` and confirm clean plan

---

## Dependencies

```
T001 ──→ T002-T003 (variables needed for IAM role)
T004 ──→ T005 (variable needed for conditional policy)
T002-T005 ──→ T006-T008 (IAM modules must exist for main.tf wiring)
T006-T008 ──→ T009-T010 (wiring must exist for validation)
T013 ──→ T014-T015 (variable must exist before module block)
All ──→ T017-T019 (final docs and validation)

External:
Spec 009 ──→ T006-T007 (module.networking outputs required)
```

## Parallel Execution

```
Phase 1: T001 (single task)
Phase 2: T002 + T003 [sequential] | T004 + T005 [sequential] — both groups [P]
Phase 3: T006 + T007 + T008 [P] → T009 → T010
Phase 5: T013 → T014 + T015 [P] → T016
Phase 6: T017 + T018 [P] → T019
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 19 |
| User Story 1 (Module activation) | 5 tasks (T006-T010) |
| User Story 2 (Worker SageMaker IAM) | 2 tasks (T011-T012) |
| User Story 3 (Notification IRSA) | 4 tasks (T013-T016) |
| Setup + Foundational | 5 tasks (T001-T005) |
| Polish | 3 tasks (T017-T019) |
| Parallel opportunities | 5 groups |
| MVP scope | Phases 1-4 (US1 + US2) |
| External dependency | Spec 009 (networking module) |

**Next**: `/speckit.implement` to start implementation in phases
