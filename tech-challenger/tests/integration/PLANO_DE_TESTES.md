# Plano de Testes — Tech Challenge Fase 4
## Analisador de Desenhos de Arquitetura

---

## 1. Visão Geral

| Dimensão | Detalhe |
|---|---|
| **Objetivo** | Validar integridade de dados, resiliência de integrações e consistência de contratos no fluxo `order-handler → worker-service`. |
| **Escopo** | Testes de integração, contrato (pacto), e infraestrutura (LocalStack/moto). |
| **Stack de Teste** | Python 3.11+, Pytest, unittest.mock, moto (LocalStack mock), Pydantic v2. |
| **Serviços Cobertos** | `order-handler` (Lambda), `worker-service` (EKS). |
| **Infra Coberta** | S3, DynamoDB, SQS, SageMaker. |

---

## 2. Matriz de Cenários de Teste

### 2.1 Integração & Resiliência — Upload e Persistência (`order-handler`)

| # | Cenário (Gherkin) | Prioridade | Arquivo |
|---|---|---|---|
| 1 | **Happy Path**: Upload PNG válido → S3 + DynamoDB (PENDING) + SQS | P0 | `test_upload_persistencia.py` |
| 2 | Content-type inválido (`application/pdf`) → 400 | P0 | `test_upload_persistencia.py` |
| 3 | Header `x-user-id` ausente → 400 | P0 | `test_upload_persistencia.py` |
| 4 | Body vazio → 400 | P1 | `test_upload_persistencia.py` |
| 5 | Falha no S3 → 500 sem leak de stack trace | P0 | `test_upload_persistencia.py` |

### 2.2 Integração & Resiliência — Consumo Assíncrono (`worker-service`)

| # | Cenário (Gherkin) | Prioridade | Arquivo |
|---|---|---|---|
| 6 | **Happy Path**: SQS → Fetch diagram → S3 download → LLM → COMPLETED no DynamoDB | P0 | `test_consumo_assincrono.py` |
| 7 | SageMaker falha → DynamoDB FAILED | P0 | `test_consumo_assincrono.py` |
| 8 | SQS deleta mensagem mesmo após falha no processamento | P0 | `test_consumo_assincrono.py` |
| 9 | JSON malformado no SQS → mensagem NÃO deletada, sem crash | P1 | `test_consumo_assincrono.py` |
| 10 | Payload SQS com campos faltantes → mensagem NÃO deletada | P1 | `test_consumo_assincrono.py` |

### 2.3 Testes de Contrato (Pacto)

| # | Cenário (Gherkin) | Prioridade | Arquivo |
|---|---|---|---|
| 17 | `DiagramUploadRequest` aceita png/jpeg/jpg/webp | P0 | `test_contratos.py` |
| 18 | `DiagramUploadRequest` rejeita pdf/gif/svg/bmp/text/empty | P0 | `test_contratos.py` |
| 19 | Constante `ACCEPTED_CONTENT_TYPES` = set exato esperado | P1 | `test_contratos.py` |
| 23 | `ArchitectureDiagram` PENDING → PROCESSING válido | P0 | `test_contratos.py` |
| 24 | `ArchitectureDiagram` PENDING → COMPLETED inválido | P0 | `test_contratos.py` |
| 25 | `mark_completed("")` → ValueError | P1 | `test_contratos.py` |
| 26 | `mark_failed()` limpa report e elements | P1 | `test_contratos.py` |

### 2.4 Infraestrutura — LocalStack (moto)

| # | Cenário (Gherkin) | Prioridade | Arquivo |
|---|---|---|---|
| 27 | DynamoDB: save + get preserva dados completos | P0 | `test_localstack_infra.py` |
| 28 | DynamoDB: update status PENDING → COMPLETED persiste corretamente | P0 | `test_localstack_infra.py` |
| 29 | DynamoDB: get inexistente → DiagramNotFoundError | P0 | `test_localstack_infra.py` |
| 30 | DynamoDB: múltiplos diagramas isolados | P1 | `test_localstack_infra.py` |
| 31 | S3: upload + download bytes idênticos | P0 | `test_localstack_infra.py` |
| 32 | S3: download inexistente → ClientError/NoSuchKey | P0 | `test_localstack_infra.py` |
| 33 | S3: upload com diferentes content-types | P1 | `test_localstack_infra.py` |

---

## 3. Estrutura de Arquivos de Teste

```
tests/
├── integration/
│   ├── __init__.py
│   ├── conftest.py                    # Fixtures compartilhadas (mocks boto3 e env vars)
│   ├── test_upload_persistencia.py    # order-handler: upload → S3 + DynamoDB + SQS
│   ├── test_consumo_assincrono.py     # worker-service: SQS → Process → DynamoDB
│   ├── test_contratos.py             # DTOs, Events, Entity state machine
│   └── test_localstack_infra.py       # DynamoDB + S3 via moto (LocalStack mock)
```

---

## 4. Tecnologias e Bibliotecas

| Biblioteca | Versão | Uso |
|---|---|---|
| `pytest` | ≥7.0 | Runner e assertions |
| `pydantic` | ≥2.0 | Validação de contratos/DTOs |
| `moto` | ≥4.0 | Mock AWS (S3, DynamoDB) — substitui LocalStack para CI |
| `boto3` | ≥1.28 | SDK AWS |
| `unittest.mock` | stdlib | Mocks para SQS e SageMaker |

---

## 5. Como Executar

```bash
# Instalar dependências de teste
pip install pytest moto boto3 pydantic

# Executar todos os testes de integração
cd tech-challenger
pytest tests/integration/ -v --tb=short

# Executar por categoria
pytest tests/integration/test_contratos.py -v             # Contratos
pytest tests/integration/test_localstack_infra.py -v       # LocalStack/Infra
pytest tests/integration/test_upload_persistencia.py -v    # Upload & Persistência
pytest tests/integration/test_consumo_assincrono.py -v     # Consumo Assíncrono

# Executar com markers específicos (se configurados)
pytest tests/integration/ -v -k "Happy" --tb=short
```

---

## 6. Critérios de Saída

- [x] Casos de teste documentados em formato **Gherkin** (Given/When/Then) como docstrings
- [x] Trechos de código Python usando **Mocks** para `boto3`
- [x] Cobertura dos serviços do fluxo crítico
- [x] Validação de **máquina de estados** (transições de DiagramStatus)
- [x] Testes de **resiliência**: falhas em S3 e SageMaker
- [x] Testes de **contrato**: DTOs, Events, serialização round-trip
- [x] Testes de **infraestrutura**: DynamoDB e S3 via moto (LocalStack mock)
