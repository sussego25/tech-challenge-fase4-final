# Tasks: 009 — VPC/Networking Terraform

**Input**: Design documents from `/specs/009-networking-terraform/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Module directory and variable definitions

- [x] T001 [P] Create `infra/networking/terraform/variables.tf` with inputs: `aws_region`, `environment`, `project_name`, `common_tags`, `vpc_cidr` (default `"10.0.0.0/16"`), `enable_ha_nat` (default `false`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: VPC resources that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Create `infra/networking/terraform/main.tf` — `data "aws_availability_zones"`, `aws_vpc` with CIDR variable, DNS support/hostnames enabled, tags `environment`, `project_name`, `common_tags`
- [x] T003 Add Internet Gateway `aws_internet_gateway` associated to VPC in `infra/networking/terraform/main.tf`
- [x] T004 Add 2 public subnets `aws_subnet "public"` (count=2) in distinct AZs with CIDRs `10.0.1.0/24`, `10.0.2.0/24`, `map_public_ip_on_launch=true`, tag `kubernetes.io/role/elb=1` in `infra/networking/terraform/main.tf`
- [x] T005 Add 2 private subnets `aws_subnet "private"` (count=2) in distinct AZs with CIDRs `10.0.10.0/24`, `10.0.20.0/24`, tag `kubernetes.io/role/internal-elb=1` in `infra/networking/terraform/main.tf`
- [x] T006 Add `aws_eip` (count = `enable_ha_nat ? 2 : 1`) and `aws_nat_gateway` (count = `enable_ha_nat ? 2 : 1`) in public subnets in `infra/networking/terraform/main.tf`
- [x] T007 Add route tables: public (`0.0.0.0/0 → IGW`), private (count = `enable_ha_nat ? 2 : 1`, `0.0.0.0/0 → NAT`) and 4 route table associations in `infra/networking/terraform/main.tf`
- [x] T008 Create `infra/networking/terraform/outputs.tf` exporting `vpc_id`, `vpc_cidr_block`, `public_subnet_ids`, `private_subnet_ids`, `private_subnet_cidrs`, `nat_gateway_ips`

**Checkpoint**: `terraform validate` passes on the networking module in isolation

---

## Phase 3: User Story 1 — VPC com isolamento de rede (Priority: P1) 🎯 MVP

**Goal**: VPC with public/private subnets, NAT, and route tables provisioned via `terraform apply`

**Independent Test**: `terraform plan` on the networking module generates VPC, subnets, IGW, NAT, route tables without errors

### Tests for User Story 1

- [x] T009 [US1] Run `terraform init` + `terraform validate` on `infra/networking/terraform/` to verify module syntax
- [x] T010 [US1] Run `terraform plan -var="environment=dev"` on `infra/networking/terraform/` and verify all expected resources appear (1 VPC, 4 subnets, 1 IGW, 1 NAT, 1 EIP, 2 route tables, 4 associations)

---

## Phase 4: User Story 2 — Integração com módulos existentes (Priority: P1)

**Goal**: Networking outputs automatically feed EKS and Kafka modules in root `main.tf`

**Independent Test**: `terraform plan` on root with `enable_eks=true` resolves VPC/subnet IDs from networking outputs

- [x] T011 [US2] Add `module "networking"` block to `infra/terraform/main.tf` with source `"../networking/terraform"` passing `vpc_cidr`, `environment`, `project_name`, `common_tags`, `enable_ha_nat`
- [x] T012 [US2] Update `module "eks"` in `infra/terraform/main.tf` — replace `var.eks_vpc_id` with `module.networking.vpc_id` and `var.eks_subnet_ids` with `module.networking.private_subnet_ids`
- [x] T013 [US2] Update `module "kafka"` in `infra/terraform/main.tf` — replace `var.kafka_vpc_id` with `module.networking.vpc_id`, `var.kafka_subnet_ids` with `module.networking.private_subnet_ids`, `var.kafka_allowed_cidr_blocks` with `module.networking.private_subnet_cidrs`
- [x] T014 [US2] Add `vpc_cidr` and `enable_ha_nat` to `infra/terraform/variables.tf`; mark `eks_vpc_id`, `eks_subnet_ids`, `kafka_vpc_id`, `kafka_subnet_ids`, `kafka_allowed_cidr_blocks` as deprecated in description
- [x] T015 [US2] Add `vpc_id`, `public_subnet_ids`, `private_subnet_ids` outputs to `infra/terraform/outputs.tf`

### Tests for User Story 2

- [x] T016 [US2] Run `terraform init -upgrade` + `terraform validate` on `infra/terraform/` and confirm no errors
- [x] T017 [US2] Run `terraform plan -var="environment=dev"` on `infra/terraform/` and verify networking resources appear in plan

---

## Phase 5: User Story 3 — Security Groups base (Priority: P2)

**Goal**: Base security groups for EKS nodes allowing Kafka (9092) and SageMaker (443) egress

**Independent Test**: After apply, SG `eks-nodes` exists with correct ingress/egress rules

- [x] T018 [US3] Add `aws_security_group "eks_nodes"` to `infra/networking/terraform/main.tf` with egress rules for ports 9092 (Kafka) and 443 (SageMaker/AWS APIs)
- [x] T019 [US3] Export `eks_nodes_security_group_id` in `infra/networking/terraform/outputs.tf`
- [x] T020 [US3] Add `eks_nodes_security_group_id` output to `infra/terraform/outputs.tf`

---

## Phase 6: Polish & Cross-Cutting

- [x] T021 Run full `terraform init -upgrade` + `terraform validate` + `terraform plan -var="environment=dev"` on `infra/terraform/` and confirm clean plan
- [x] T022 Validate edge case: verify `data.aws_availability_zones` handles regions with <2 AZs gracefully (validation in variable or data source filter)

---

## Dependencies

```
T001 ──→ T002-T008 (variables needed for main.tf and outputs.tf)
T002-T008 ──→ T009-T010 (module must exist for validation)
T008 ──→ T011-T015 (outputs must be defined for root main.tf wiring)
T011-T015 ──→ T016-T017 (root wiring must exist for root validation)
T018-T019 ──→ T020 (SG must exist before exposing in root outputs)
All ──→ T021-T022 (final validation)
```

## Parallel Execution

```
Phase 1: T001 (single task)
Phase 2: T002 → T003 → T004+T005 [P] → T006 → T007 → T008
Phase 4: T011 + T014 + T015 [P] → T012 + T013 [P] → T016 → T017
Phase 5: T018 → T019 + T020 [P]
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 22 |
| User Story 1 (VPC isolation) | 2 tasks (T009-T010) |
| User Story 2 (Module integration) | 7 tasks (T011-T017) |
| User Story 3 (Security groups) | 3 tasks (T018-T020) |
| Setup + Foundational | 8 tasks (T001-T008) |
| Polish | 2 tasks (T021-T022) |
| Parallel opportunities | 5 groups |
| MVP scope | Phases 1-4 (US1 + US2) |

**Next**: `/speckit.implement` to start implementation in phases
