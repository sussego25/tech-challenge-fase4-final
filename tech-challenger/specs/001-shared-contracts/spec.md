# Feature Specification: Shared Contracts (DTOs, Entities, Events)

**Feature Branch**: `001-shared-contracts`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: Contratos compartilhados entre todos os microserviços do pipeline de análise de arquitetura

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Evento de Análise Publicado no SQS (Priority: P1)

Uma Lambda recebe um diagrama via API Gateway, salva no S3 e precisa publicar um evento no SQS para o worker-service processar. Todos os campos necessários para o worker iniciar o processamento devem estar presentes e validados.

**Why this priority**: É o gatilho de entrada do pipeline inteiro. Sem este contrato, nenhum serviço consegue se comunicar.

**Independent Test**: Pode ser testado de forma isolada criando uma instância do `ArchitectureAnalysisRequestedEvent` com dados válidos e verificando que a serialização/desserialização JSON é perfeita e que validações Pydantic rejeitam dados inválidos.

**Acceptance Scenarios**:

1. **Given** um evento com `diagram_id`, `s3_bucket`, `s3_key`, `user_id` e `requested_at` válidos, **When** serializado para JSON, **Then** todos os campos estão presentes e tipados corretamente
2. **Given** um evento com `diagram_id` ausente, **When** validado pelo Pydantic, **Then** levanta `ValidationError` com mensagem clara
3. **Given** um JSON válido recebido do SQS, **When** desserializado para `ArchitectureAnalysisRequestedEvent`, **Then** o objeto é criado sem erros

---

### User Story 2 — Resultado da Análise Publicado no Kafka (Priority: P2)

O worker-service termina o processamento (YOLO + LLM) e precisa publicar o resultado no Kafka para a notification-service consumir e notificar o usuário.

**Why this priority**: É o contrato de saída do pipeline. Sem ele, o resultado da análise não chega ao usuário.

**Independent Test**: Criar uma instância de `ArchitectureAnalysisCompletedEvent` com resultado da LLM e verificar serialização/desserialização e validações.

**Acceptance Scenarios**:

1. **Given** um evento com `diagram_id`, `user_id`, `analysis_report`, `elements_detected`, `status=completed` e `completed_at`, **When** serializado, **Then** todos os campos presentes e corretos
2. **Given** um evento com `status=failed` e `error_message` preenchido, **When** validado, **Then** aceito como evento de falha válido
3. **Given** `analysis_report` vazio, **When** validado com `status=completed`, **Then** levanta `ValidationError`

---

### User Story 3 — DTOs de Request/Response da API (Priority: P3)

O API Gateway recebe requisições HTTP multipart (upload de diagrama) e retorna status de processamento. Os DTOs devem ser consistentes entre os serviços.

**Why this priority**: Necessário para o contrato público da API, mas pode ser definido depois dos eventos internos.

**Independent Test**: Criar instâncias dos DTOs `DiagramUploadRequest` e `AnalysisStatusResponse` e verificar validações e serialização.

**Acceptance Scenarios**:

1. **Given** uma request com `file` (imagem) e `user_id`, **When** validado por `DiagramUploadRequest`, **Then** aceito corretamente
2. **Given** uma request sem `file`, **When** validado, **Then** levanta `ValidationError`
3. **Given** um `analysis_id` válido, **When** mapeado para `AnalysisStatusResponse`, **Then** retorna `status`, `diagram_id`, `created_at` e `result` (opcional)

---

### User Story 4 — Entidade de Domínio ArchitectureDiagram (Priority: P3)

Representa o diagrama e seus metadados armazenados no DynamoDB. Usada pelo worker-service e pela Lambda para persistência.

**Why this priority**: Necessária para persistência, mas não bloqueia a mensageria interna.

**Independent Test**: Criar instância de `ArchitectureDiagram` e verificar campos obrigatórios, geração de ID e transição de status.

**Acceptance Scenarios**:

1. **Given** dados mínimos (`s3_key`, `s3_bucket`, `user_id`), **When** criar `ArchitectureDiagram`, **Then** `diagram_id` é gerado (UUID), `status=pending` e `created_at` preenchido
2. **Given** uma entidade com `status=pending`, **When** chamar `mark_processing()`, **Then** `status=processing` e `updated_at` atualizado
3. **Given** uma entidade com `status=processing`, **When** chamar `mark_completed(report)`, **Then** `status=completed` e `analysis_report` preenchido

---

### Edge Cases

- O que acontece quando `elements_detected` é lista vazia (diagrama sem elementos reconhecidos)?
- Como o sistema lida com `analysis_report` muito grande (>256KB limite SQS)? → Deve ser salvo no S3 e referenciado por URL
- O que acontece quando o `diagram_id` do evento SQS não existe no DynamoDB?
- Eventos com `requested_at` no futuro devem ser aceitos ou rejeitados?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `shared/contracts/events/` DEVE conter classes Pydantic para todos os eventos do pipeline
- **FR-002**: `shared/contracts/dto/` DEVE conter classes Pydantic para request/response da API
- **FR-003**: `shared/contracts/entities/` DEVE conter a entidade `ArchitectureDiagram` com lógica de transição de status
- **FR-004**: Todos os contratos DEVEM ser serializáveis/desserializáveis para JSON sem perda de dados
- **FR-005**: Todos os contratos DEVEM ter validações Pydantic com mensagens de erro claras
- **FR-006**: Contratos DEVEM usar `datetime` com timezone UTC para todos os campos de data
- **FR-007**: `diagram_id` DEVE ser UUID v4 gerado automaticamente se não fornecido
- **FR-008**: Cada módulo (`events/`, `dto/`, `entities/`) DEVE ter `__init__.py` exportando todas as classes públicas

### Key Entities

- **`ArchitectureAnalysisRequestedEvent`**: Publicado pela Lambda no SQS. Campos: `diagram_id`, `s3_bucket`, `s3_key`, `user_id`, `requested_at`, `metadata` (opcional)
- **`ArchitectureAnalysisCompletedEvent`**: Publicado pelo worker no Kafka. Campos: `diagram_id`, `user_id`, `status` (completed/failed), `analysis_report`, `elements_detected`, `completed_at`, `error_message` (opcional)
- **`DiagramUploadRequest`**: DTO de entrada da API. Campos: `user_id`, `file_name`, `content_type`
- **`AnalysisStatusResponse`**: DTO de resposta da API. Campos: `analysis_id`, `diagram_id`, `status`, `created_at`, `result` (opcional)
- **`ArchitectureDiagram`**: Entidade DynamoDB. Campos: `diagram_id`, `s3_key`, `s3_bucket`, `user_id`, `status`, `created_at`, `updated_at`, `analysis_report` (opcional), `elements_detected` (opcional)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos campos obrigatórios validados pelo Pydantic — nenhum campo inválido chega ao serviço consumidor
- **SC-002**: Serialização/desserialização JSON round-trip sem perda para todas as classes
- **SC-003**: Cobertura de testes unitários ≥ 90% para todos os contratos
- **SC-004**: Todos os serviços (worker, notification, lambda) importam contratos exclusivamente de `shared/contracts/` — zero duplicação

---

## Assumptions

- Python 3.11+ com Pydantic v2
- UUID v4 para todos os IDs de diagrama
- Datas sempre em UTC (usando `datetime.now(timezone.utc)`)
- O campo `analysis_report` é uma string contendo o Markdown gerado pela LLM
- `elements_detected` é uma lista de strings com os nomes dos elementos identificados pelo YOLO
- Os contratos são pacotes Python instaláveis localmente via `pip install -e shared/`
