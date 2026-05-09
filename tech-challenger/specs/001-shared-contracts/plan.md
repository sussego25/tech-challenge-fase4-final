# Implementation Plan: Shared Contracts

**Branch**: `001-shared-contracts` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification de `shared/contracts/` — DTOs, Entities e Events

---

## Summary

Implementar os contratos compartilhados (Pydantic v2) que servem de linguagem comum entre todos os microserviços do pipeline: Lambda → SQS → worker-service → Kafka → notification-service. Inclui eventos de mensageria, DTOs de API e entidade de domínio `ArchitectureDiagram`.

---

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Pydantic v2, python-dateutil, uuid (stdlib)  
**Storage**: N/A (contratos são modelos de dados puros)  
**Testing**: pytest + pytest-pydantic  
**Target Platform**: Pacote Python instalável (shared lib)  
**Project Type**: library  
**Performance Goals**: Serialização/desserialização < 1ms por instância  
**Constraints**: Zero dependências de infraestrutura AWS nos contratos  
**Scale/Scope**: Utilizado por 4+ serviços simultâneos

---

## Constitution Check

- ✅ **Hexagonal**: Contratos em `shared/` — sem import de infra
- ✅ **Python Quality**: Pydantic v2 + type hints obrigatórios + PEP 8
- ✅ **Test-First**: Testes unitários escritos antes da implementação
- ✅ **Security**: Nenhum dado sensível nos contratos; UUIDs para IDs

---

## Project Structure

### Documentation (this feature)

```text
specs/001-shared-contracts/
├── spec.md        ✅ criado
├── plan.md        ✅ este arquivo
└── tasks.md       (gerado por /speckit.tasks)
```

### Source Code

```text
shared/
├── pyproject.toml              # pacote instalável
├── contracts/
│   ├── __init__.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── analysis_requested.py   # ArchitectureAnalysisRequestedEvent
│   │   └── analysis_completed.py   # ArchitectureAnalysisCompletedEvent
│   ├── dto/
│   │   ├── __init__.py
│   │   ├── diagram_upload.py       # DiagramUploadRequest
│   │   └── analysis_status.py      # AnalysisStatusResponse
│   └── entities/
│       ├── __init__.py
│       └── architecture_diagram.py # ArchitectureDiagram

tests/unit/
└── shared/
    └── contracts/
        ├── events/
        │   ├── test_analysis_requested.py
        │   └── test_analysis_completed.py
        ├── dto/
        │   ├── test_diagram_upload.py
        │   └── test_analysis_status.py
        └── entities/
            └── test_architecture_diagram.py
```

---

## Implementation Phases

### Phase 0 — Setup

- Criar `shared/pyproject.toml` com Pydantic v2 como dependência
- Criar `shared/contracts/__init__.py` e subpastas

### Phase 1 — Events (P1 — bloqueador)

**`ArchitectureAnalysisRequestedEvent`** — publicado pela Lambda no SQS:
```python
class ArchitectureAnalysisRequestedEvent(BaseModel):
    diagram_id: UUID = Field(default_factory=uuid4)
    s3_bucket: str
    s3_key: str
    user_id: str
    requested_at: datetime  # UTC
    metadata: dict[str, str] = Field(default_factory=dict)
```

**`ArchitectureAnalysisCompletedEvent`** — publicado pelo worker no Kafka:
```python
class AnalysisStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"

class ArchitectureAnalysisCompletedEvent(BaseModel):
    diagram_id: UUID
    user_id: str
    status: AnalysisStatus
    analysis_report: str | None = None  # obrigatório se status=completed
    elements_detected: list[str] = Field(default_factory=list)
    completed_at: datetime  # UTC
    error_message: str | None = None  # obrigatório se status=failed

    @model_validator(mode="after")
    def validate_status_fields(self) -> "ArchitectureAnalysisCompletedEvent":
        if self.status == AnalysisStatus.COMPLETED and not self.analysis_report:
            raise ValueError("analysis_report is required when status=completed")
        if self.status == AnalysisStatus.FAILED and not self.error_message:
            raise ValueError("error_message is required when status=failed")
        return self
```

### Phase 2 — Entity (P3)

**`ArchitectureDiagram`** — entidade DynamoDB com transições de status:
```python
class DiagramStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ArchitectureDiagram(BaseModel):
    diagram_id: UUID = Field(default_factory=uuid4)
    s3_key: str
    s3_bucket: str
    user_id: str
    status: DiagramStatus = DiagramStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_report: str | None = None
    elements_detected: list[str] = Field(default_factory=list)

    def mark_processing(self) -> None: ...
    def mark_completed(self, report: str, elements: list[str]) -> None: ...
    def mark_failed(self, error: str) -> None: ...
```

### Phase 3 — DTOs (P3)

**`DiagramUploadRequest`** e **`AnalysisStatusResponse`** para a camada de API.

---

## Test Strategy

- **Unit**: Validação Pydantic (campos obrigatórios, tipos, enums), round-trip JSON, transições de status da entidade
- **Cobertura mínima**: 90% por arquivo
- **Ferramenta**: pytest com `model_validate` e `.model_dump()`
