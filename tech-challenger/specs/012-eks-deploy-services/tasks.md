# Tasks: 012 — Deploy worker-service e notification-service no EKS

**Input**: Design documents from `/specs/012-eks-deploy-services/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: ECR Terraform module and deploy scripts directory

- [ ] T001 [P] Create directory `infra/ecr/terraform/` and create `infra/ecr/terraform/variables.tf` with inputs: `environment`, `project_name`, `common_tags`, `services` (list, default `["worker-service", "notification-service"]`), `max_image_count` (number, default `30`)
- [ ] T002 [P] Create directory `deploy/scripts/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ECR repositories and build script that all deploy tasks depend on

**⚠️ CRITICAL**: No Helm deploy can work without ECR repos and images

- [ ] T003 Create `infra/ecr/terraform/main.tf` — `aws_ecr_repository` (for_each over `var.services`) with name `"${var.project_name}-${var.environment}-${each.value}"`, `image_tag_mutability = "MUTABLE"`, `image_scanning_configuration { scan_on_push = true }`, plus `aws_ecr_lifecycle_policy` keeping only `var.max_image_count` most recent images
- [ ] T004 Create `infra/ecr/terraform/outputs.tf` — export `repository_urls` (map: service_name → URL) and `repository_arns` (map: service_name → ARN)
- [ ] T005 Add `module "ecr"` to `infra/terraform/main.tf` with source `"../ecr/terraform"` (no count — always needed for deploy)
- [ ] T006 Add `ecr_repository_urls` and `ecr_repository_arns` outputs to `infra/terraform/outputs.tf`
- [ ] T007 Create `deploy/scripts/build-and-push.sh` — accepts `--service <name>` and `--tag <tag>`, does ECR login via `aws ecr get-login-password`, `docker build` from `services/<service>/`, `docker tag` + `docker push` to ECR with tag and `latest`

**Checkpoint**: `terraform validate` passes with ECR module; `build-and-push.sh --help` shows usage

---

## Phase 3: User Story 1 — Build e push de imagens Docker (Priority: P1) 🎯 MVP

**Goal**: Docker images for both services are built and pushed to ECR

**Independent Test**: `docker build` succeeds for both Dockerfiles; images appear in ECR after push

### Tests for User Story 1

- [ ] T008 [US1] Verify `services/worker-service/Dockerfile` builds without error: `docker build -t worker-service-test services/worker-service/`
- [ ] T009 [US1] Verify `services/notification-service/Dockerfile` builds without error: `docker build -t notification-service-test services/notification-service/`

---

## Phase 4: User Story 2 — Deploy via Helm com values reais (Priority: P1)

**Goal**: `helm install` with `values-dev.yaml` deploys both services to EKS with correct env vars and images

**Independent Test**: `helm template` with values-dev.yaml generates valid Kubernetes manifests with correct image URIs and env vars

- [ ] T010 [US2] Create `deploy/helm/worker-service/values-dev.yaml` — override `image.repository` (ECR URL placeholder), `image.tag: "latest"`, `serviceAccount.annotations."eks.amazonaws.com/role-arn"` (IRSA ARN placeholder), `env` with all worker env vars: `AWS_REGION`, `SQS_QUEUE_URL`, `SQS_DLQ_URL`, `S3_BUCKET`, `DYNAMODB_TABLE`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_ANALYSIS_COMPLETED`, `SAGEMAKER_ENDPOINT`
- [ ] T011 [US2] Create `deploy/helm/notification-service/values-dev.yaml` — override `image.repository` (ECR URL placeholder), `image.tag: "latest"`, `serviceAccount.annotations."eks.amazonaws.com/role-arn"` (IRSA ARN placeholder), `env` with all notification env vars: `AWS_REGION`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_ANALYSIS_COMPLETED`, `KAFKA_GROUP_ID`, `DYNAMODB_TABLE`, `SES_SENDER_EMAIL`, `SES_AWS_REGION`
- [ ] T012 [P] [US2] Update HPA in `deploy/helm/worker-service/values.yaml` — set `minReplicas: 1`, `maxReplicas: 2`, `targetCPUUtilizationPercentage: 70` (clarification: spot t3.medium, minimal sizing)
- [ ] T013 [P] [US2] Update HPA in `deploy/helm/notification-service/values.yaml` — set `minReplicas: 1`, `maxReplicas: 2`, `targetCPUUtilizationPercentage: 70`

### Tests for User Story 2

- [ ] T014 [US2] Run `helm template worker deploy/helm/worker-service/ -f deploy/helm/worker-service/values-dev.yaml` and verify rendered Deployment has correct image, env vars, and ServiceAccount annotation
- [ ] T015 [US2] Run `helm template notification deploy/helm/notification-service/ -f deploy/helm/notification-service/values-dev.yaml` and verify rendered Deployment has correct image, env vars, and ServiceAccount annotation

---

## Phase 5: User Story 3 — IRSA funciona corretamente (Priority: P1)

**Goal**: ServiceAccounts have correct IRSA annotations so pods assume IAM roles automatically

**Independent Test**: `helm template` output shows correct `eks.amazonaws.com/role-arn` annotation on ServiceAccount

- [ ] T016 [US3] Verify `deploy/helm/worker-service/templates/serviceaccount.yaml` includes annotation from values `serviceAccount.annotations`
- [ ] T017 [US3] Verify `deploy/helm/notification-service/templates/serviceaccount.yaml` includes annotation from values `serviceAccount.annotations`

---

## Phase 6: Polish & Cross-Cutting

- [ ] T018 Create `docs/deployment/deploy-eks.md` — step-by-step guide: prerequisites, ECR login, build/push, generate values, helm install, kubectl verify, troubleshooting (ImagePullBackOff, AccessDenied, Kafka timeout)
- [ ] T019 Add spot instance configuration note in `docs/deployment/deploy-eks.md` — EKS node group uses `t3.medium` spot instances for dev environment (clarification: ~70% cost savings)
- [ ] T020 Run `terraform init -upgrade` + `terraform validate` + `terraform plan -var="environment=dev"` on `infra/terraform/` and confirm ECR resources appear in plan
- [ ] T021 Run `helm lint deploy/helm/worker-service/` and `helm lint deploy/helm/notification-service/` to verify chart validity

---

## Dependencies

```
T001-T002 ──→ T003-T007 (directories must exist)
T003-T004 ──→ T005-T006 (ECR module must exist for root main.tf)
T007 ──→ T008-T009 (build script for Docker builds)
T005-T006 ──→ T010-T011 (ECR URLs needed for values-dev)
T010-T013 ──→ T014-T015 (values-dev needed for helm template)
T016-T017 ──→ independent (only reads existing templates)

External:
Spec 009 ──→ EKS cluster requires VPC
Spec 010 ──→ T010-T011 (IRSA role ARNs for serviceAccount annotation)
Spec 011 ──→ T011 (SES_SENDER_EMAIL env var)
Spec 014 ──→ T010 (SAGEMAKER_ENDPOINT env var)
```

## Parallel Execution

```
Phase 1: T001 + T002 [P]
Phase 2: T003 → T004 → T005 + T006 [P] → T007
Phase 3: T008 + T009 [P]
Phase 4: T010 + T011 [P] | T012 + T013 [P] → T014 + T015 [P]
Phase 6: T018 + T019 [P] → T020 → T021
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 21 |
| User Story 1 (Docker build & push) | 2 tasks (T008-T009) |
| User Story 2 (Helm deploy) | 6 tasks (T010-T015) |
| User Story 3 (IRSA) | 2 tasks (T016-T017) |
| Setup + Foundational | 7 tasks (T001-T007) |
| Polish | 4 tasks (T018-T021) |
| Parallel opportunities | 7 groups |
| MVP scope | Phases 1-4 (ECR + Docker + Helm values) |
| External dependencies | Specs 009, 010, 011, 014 |

**Next**: `/speckit.implement` to start implementation in phases
