# Tasks: Shared Contracts

**Input**: [spec.md](./spec.md) + [plan.md](./plan.md)  
**Branch**: `001-shared-contracts`

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Pode rodar em paralelo
- **[US#]**: User Story correspondente

---

## Phase 1: Setup (Infraestrutura Compartilhada)

- [ ] T001 [US1] Criar `shared/pyproject.toml` com Pydantic v2 como dependência e configuração de pacote instalável
- [ ] T002 [US1] Criar `shared/contracts/__init__.py` exportando todos os contratos públicos
- [ ] T003 [P] [US1] Criar `shared/contracts/events/__init__.py`
- [ ] T004 [P] [US1] Criar `shared/contracts/dto/__init__.py`
- [ ] T005 [P] [US1] Criar `shared/contracts/entities/__init__.py`
- [ ] T006 [P] [US1] Criar estrutura de pastas nos testes: `tests/unit/shared/contracts/events/`, `dto/`, `entities/`

---

## Phase 2: Events — P1 (Bloqueador do Pipeline)

**Goal**: Contratos de mensageria SQS e Kafka prontos para uso pelos serviços

**⚠️ CRÍTICO**: worker-service e notification-service dependem desta fase

- [ ] T007 [US1] Escrever testes unitários para `ArchitectureAnalysisRequestedEvent` ANTES da implementação:
  - Serialização/desserialização JSON round-trip
  - Geração automática de UUID quando `diagram_id` ausente
  - Validação: campos obrigatórios (`s3_bucket`, `s3_key`, `user_id`, `requested_at`)
  - Validação: `diagram_id` inválido (não UUID) levanta `ValidationError`
- [ ] T008 [US1] Implementar `shared/contracts/events/analysis_requested.py` com `ArchitectureAnalysisRequestedEvent` (Pydantic v2, UTC datetime, UUID default)
- [ ] T009 [US2] Escrever testes unitários para `ArchitectureAnalysisCompletedEvent` ANTES da implementação:
  - `status=completed` sem `analysis_report` levanta `ValidationError`
  - `status=failed` sem `error_message` levanta `ValidationError`
  - `status=completed` com `analysis_report` aceito com sucesso
  - `elements_detected` lista vazia aceita como válido
- [ ] T010 [US2] Implementar `shared/contracts/events/analysis_completed.py` com `ArchitectureAnalysisCompletedEvent` e `AnalysisStatus` enum + `@model_validator`
- [ ] T011 [P] [US1] Atualizar `shared/contracts/events/__init__.py` exportando ambos os eventos

**Checkpoint**: Eventos prontos — worker-service e notification-service podem ser implementados em paralelo

---

## Phase 3: Entity — P3

**Goal**: Entidade `ArchitectureDiagram` com transições de status para uso no DynamoDB

- [ ] T012 [US4] Escrever testes unitários para `ArchitectureDiagram` ANTES da implementação:
  - Criação com dados mínimos gera `diagram_id` UUID e `status=pending`
  - `mark_processing()` muda `status=processing` e atualiza `updated_at`
  - `mark_completed(report, elements)` muda `status=completed` e preenche `analysis_report`
  - `mark_failed(error)` muda `status=failed`
  - Transição inválida (ex: `pending → completed` direto) levanta `ValueError`
- [ ] T013 [US4] Implementar `shared/contracts/entities/architecture_diagram.py` com `ArchitectureDiagram` e `DiagramStatus` enum
- [ ] T014 [P] [US4] Atualizar `shared/contracts/entities/__init__.py`

---

## Phase 4: DTOs — P3

**Goal**: DTOs de request/response para a camada de API (Lambda/API Gateway)

- [ ] T015 [US3] Escrever testes unitários para `DiagramUploadRequest`:
  - Request com `user_id` e `file_name` válidos aceita
  - Request sem `user_id` levanta `ValidationError`
  - `content_type` inválido (não image/*) levanta `ValidationError`
- [ ] T016 [P] [US3] Escrever testes para `AnalysisStatusResponse`:
  - Resposta com `status=pending` e sem `result` é válida
  - Resposta com `status=completed` e `result` preenchido é válida
- [ ] T017 [US3] Implementar `shared/contracts/dto/diagram_upload.py` com `DiagramUploadRequest`
- [ ] T018 [P] [US3] Implementar `shared/contracts/dto/analysis_status.py` com `AnalysisStatusResponse`
- [ ] T019 [P] [US3] Atualizar `shared/contracts/dto/__init__.py`

---

## Phase 5: Integração e Validação Final

- [ ] T020 [P] Atualizar `shared/contracts/__init__.py` exportando todos os contratos das 3 camadas
- [ ] T021 [P] Verificar cobertura de testes ≥ 90% com `pytest --cov=shared/contracts`
- [ ] T022 Testar instalação do pacote: `pip install -e shared/` em ambiente limpo
