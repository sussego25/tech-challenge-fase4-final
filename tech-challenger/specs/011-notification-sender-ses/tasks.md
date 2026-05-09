# Tasks: 011 — NotificationSender Real (Amazon SES)

**Input**: Design documents from `/specs/011-notification-sender-ses/`  
**Prerequisites**: plan.md ✅, spec.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Dependencies and configuration additions

- [ ] T001 Verify `boto3` is listed in `services/notification-service/requirements.txt` (add if missing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuration settings that the sender implementation needs

**⚠️ CRITICAL**: Settings must exist before the sender can be instantiated

- [ ] T002 Add `SES_SENDER_EMAIL: str` (default `""`) and `SES_AWS_REGION: str` (default `"us-east-1"`) to `services/notification-service/src/config/settings.py`

**Checkpoint**: Settings import works without errors

---

## Phase 3: User Story 1 — Envio de e-mail ao completar análise (Priority: P1) 🎯 MVP

**Goal**: When analysis completes, notification-service sends email via SES to `user_email` (not `user_id`)

**Independent Test**: Unit test with mocked boto3 SES verifies `send_email` is called with correct Source, Destination (`user_email`), Subject, Body

### Tests for User Story 1

- [ ] T003 [P] [US1] Create `tests/unit/notification_service/test_notification_sender.py` — test: SES configured + send success → `ses.send_email()` called with `Source=sender_email`, `Destination.ToAddresses=[notification.user_email]`, `Subject.Data="Architecture Diagram Analysis - {diagram_id}"`
- [ ] T004 [P] [US1] Add test in `tests/unit/notification_service/test_notification_sender.py` — test: SES configured + SES raises `ClientError` → exception propagates (not caught by sender)

### Implementation for User Story 1

- [ ] T005 [US1] Rewrite `services/notification-service/src/infrastructure/notification_sender.py` — constructor receives `sender_email: str` and `region: str`; if `sender_email` non-empty, create `boto3.client("ses", region_name=region)`; `send(notification)` calls `ses.send_email()` using `notification.user_email` as ToAddresses destination
- [ ] T006 [US1] Update `services/notification-service/src/main.py` — read `SES_SENDER_EMAIL` and `SES_AWS_REGION` from settings, inject into `NotificationSender(sender_email=..., region=...)`
- [ ] T007 [US1] Run unit tests: `python -m pytest tests/unit/notification_service/test_notification_sender.py -v` and verify T003 and T004 pass

**Checkpoint**: SES sender works with mocked boto3; real SES not required yet

---

## Phase 4: User Story 2 — Configuração via variáveis de ambiente (Priority: P1)

**Goal**: Operator configures SES sender and region via environment variables in Helm chart

**Independent Test**: Setting `SES_SENDER_EMAIL` env var changes the sender's behavior

- [ ] T008 [US2] Add `SES_SENDER_EMAIL: ""` and `SES_AWS_REGION: "us-east-1"` to `env` section in `deploy/helm/notification-service/values.yaml`

---

## Phase 5: User Story 3 — Fallback gracioso (Priority: P2)

**Goal**: When SES is not configured (empty `SES_SENDER_EMAIL`), sender logs instead of sending; no error thrown

**Independent Test**: Unit test with empty sender_email → only logs, no SES client created

### Tests for User Story 3

- [ ] T009 [P] [US3] Add test in `tests/unit/notification_service/test_notification_sender.py` — test: SES not configured (empty sender_email) → `send()` only logs warning, no exception, `ses.send_email` NOT called

### Implementation for User Story 3

- [ ] T010 [US3] Verify fallback logic in `notification_sender.py`: if `self._ses is None`, `logger.warning("SES not configured, logging only: %s", notification.message)` and return without error
- [ ] T011 [US3] Run all unit tests: `python -m pytest tests/unit/notification_service/ -v` and verify T003, T004, T009 all pass

---

## Phase 6: Polish & Cross-Cutting

- [ ] T012 Add IAM permission `ses:SendEmail` and `ses:SendRawEmail` to the notification-service IRSA role — document in spec 010 integration (file: `infra/eks/terraform/iam-notification/iam_role.tf`)
- [ ] T013 Verify `user_email` field exists in `shared/contracts/entities/` and `shared/contracts/events/` — if missing, add `user_email: str` to `Notification` entity and `AnalysisCompletedEvent`

---

## Dependencies

```
T001 ──→ T002 (boto3 must be available)
T002 ──→ T005-T006 (settings must exist for sender)
T003-T004 ──→ T007 (tests must exist before running)
T005-T006 ──→ T007 (implementation must exist for tests to pass)
T009 ──→ T010-T011 (fallback test before verifying logic)

External:
Spec 010 ──→ T012 (IRSA role must exist to add SES policy)
shared/contracts ──→ T013 (user_email field in contracts)
```

## Parallel Execution

```
Phase 2: T002 (single task)
Phase 3: T003 + T004 [P] → T005 + T006 [sequential] → T007
Phase 5: T009 → T010 → T011
Phase 6: T012 + T013 [P]
```

## Summary

| Metric | Value |
|---|---|
| Total tasks | 13 |
| User Story 1 (SES email send) | 5 tasks (T003-T007) |
| User Story 2 (Env var config) | 1 task (T008) |
| User Story 3 (Graceful fallback) | 3 tasks (T009-T011) |
| Setup + Foundational | 2 tasks (T001-T002) |
| Polish | 2 tasks (T012-T013) |
| Parallel opportunities | 3 groups |
| MVP scope | Phases 1-4 (US1 + US2) |
| External dependencies | Spec 010 (IRSA role), shared contracts (user_email field) |

**Next**: `/speckit.implement` to start implementation in phases
