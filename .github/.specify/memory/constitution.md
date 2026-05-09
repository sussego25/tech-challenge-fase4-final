# Tech-Challenge-fase-4 Constitution

## Core Principles

### I. Hexagonal Architecture (NON-NEGOTIABLE)
Every microservice must follow hexagonal architecture with strict layer separation: `domain/` (business rules, no external deps), `application/` (use cases), `infrastructure/` (AWS, DB, messaging adapters), `presentation/` (FastAPI routes); Cross-layer imports only inward — never infrastructure importing domain directly from another service; Shared contracts only via `shared/contracts/` (DTOs, entities, events).

### II. Python Quality Standards (NON-NEGOTIABLE)
Language: Python for all services (lambda-functions, worker-service, notification-service, order-service, payment-service); PEP 8 + SOLID mandatory, enforced by Black formatter; Type hints required on all functions and class attributes; snake_case for variables/functions, PascalCase for classes; No code merged without lint passing.

### III. Test-First Development (NON-NEGOTIABLE)
TDD mandatory: unit tests written and approved before implementation; Test structure mirrors service structure under `tests/unit/`, `tests/integration/`, `tests/e2e/`; No PR merged with untested code; Integration tests required for: new service contracts, messaging changes (Kafka/SQS topics), DynamoDB schema changes.

### IV. Infrastructure as Code
All AWS resources provisioned via Terraform in `infra/`; No manual resource creation in AWS console; Each resource module has its own IAM role in a dedicated `iam/` subfolder; Principle of least privilege enforced on all IAM roles and policies.

### V. Messaging Segregation
Kafka for internal inter-service events; SQS for external integrations and async processing; All topics/queues documented in `messaging/`; Event contracts defined in `shared/contracts/events/` — never duplicated across services.

### VI. Security-First
IAM roles scoped per service — no shared roles across services; Secrets stored in Kubernetes Secrets or AWS Secrets Manager — never in code or ConfigMaps; VPC isolation mandatory for all services; LGPD/GDPR compliance required for any user data handling; LLM outputs must not expose PII.

## Technology Stack

- **Runtime**: Python (FastAPI + Pydantic), AWS Lambda
- **Orchestration**: Kubernetes/EKS via Helm charts (`infra/eks/helm-charts/`)
- **Databases**: DynamoDB (NoSQL), S3 (object storage)
- **Messaging**: Apache Kafka (internal), AWS SQS (external)
- **AI/ML**: AWS SageMaker (LLM inference), YOLO (diagram element detection)
- **IaC**: Terraform (all infra modules under `infra/`)
- **Containers**: Docker with multi-stage builds

## Development Workflow

- **Branches**: `feature/nome-da-feature`, `bugfix/issue-id`, `hotfix/urgente`; merge only via Pull Request
- **Commits**: Conventional Commits in English (e.g., `feat: add order validation`, `fix: sqs consumer retry`)
- **PRs**: Minimum 1 approver; CI/CD (build, lint, tests) must pass; no merge with conflicts; prefer small, focused PRs
- **Containers**: Every service must have a `Dockerfile` with multi-stage build
- **Deploy**: Via Helm charts to EKS; ConfigMaps for non-sensitive config; Kubernetes Secrets for sensitive config
- **Monitoring**: Structured logs required; metrics via CloudWatch/Prometheus

## Governance

This constitution supersedes all other practices; Amendments require PR with documented justification and migration plan; All PRs must verify compliance with these principles; Every new AWS resource must have corresponding Terraform code and IAM policy before deployment.

**Version**: 1.0.0 | **Ratified**: 2026-04-12 | **Last Amended**: 2026-04-12
