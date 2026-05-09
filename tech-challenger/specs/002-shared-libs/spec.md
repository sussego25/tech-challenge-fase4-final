# Feature Specification: Shared Libs (AWS, Messaging, LLM)

**Feature Branch**: `002-shared-libs`
**Created**: 2026-04-12
**Status**: Draft
**Depends on**: `001-shared-contracts`

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Lambda publica evento no SQS (Priority: P1)

A Lambda `order-handler` recebe um diagrama, salva no S3 e precisa publicar um `ArchitectureAnalysisRequestedEvent` no SQS usando um client reutilizável de `libs/aws/`.

**Why this priority**: Bloqueador direto para a Lambda funcionar. Sem o SQS client, nenhum serviço consegue publicar ou consumir mensagens.

**Independent Test**: Testar `SQSClient.send_message()` com mock do boto3, verificando que o corpo da mensagem é o JSON do evento serializado.

**Acceptance Scenarios**:

1. **Given** um `ArchitectureAnalysisRequestedEvent` válido, **When** `SQSClient.send_message(event)` é chamado, **Then** boto3 `send_message` é chamado com `MessageBody` igual ao JSON do evento
2. **Given** um erro de rede (boto3 lança `ClientError`), **When** `send_message` é chamado, **Then** lança `SQSPublishError` com mensagem descritiva
3. **Given** `queue_url` vazio, **When** `SQSClient` é instanciado, **Then** lança `ValueError`

---

### User Story 2 — Worker consome e deleta mensagem do SQS (Priority: P1)

O `worker-service` precisa receber mensagens do SQS, processar e deletar após sucesso.

**Why this priority**: Bloqueador direto do worker-service.

**Independent Test**: Testar `SQSClient.receive_messages()` e `SQSClient.delete_message()` com mocks boto3.

**Acceptance Scenarios**:

1. **Given** fila com mensagens, **When** `receive_messages(max_messages=5)` é chamado, **Then** retorna lista de `SQSMessage` com `body` e `receipt_handle`
2. **Given** fila vazia, **When** `receive_messages()` é chamado, **Then** retorna lista vazia
3. **Given** `receipt_handle` válido, **When** `delete_message(receipt_handle)` é chamado, **Then** boto3 `delete_message` é chamado com parâmetros corretos
4. **Given** erro no delete, **When** `delete_message()` é chamado, **Then** lança `SQSDeleteError`

---

### User Story 3 — Lambda salva diagrama no S3 (Priority: P1)

A Lambda `order-handler` precisa fazer upload do diagrama recebido para o S3.

**Why this priority**: O S3 é a fonte de verdade do diagrama para todo o pipeline.

**Independent Test**: Testar `S3Client.upload_file()` e `S3Client.get_presigned_url()` com mock boto3.

**Acceptance Scenarios**:

1. **Given** bytes de uma imagem e um `s3_key`, **When** `S3Client.upload_file(data, s3_key, content_type)` é chamado, **Then** boto3 `put_object` é chamado com os parâmetros corretos
2. **Given** um `s3_key` existente, **When** `S3Client.download_file(s3_key)` é chamado, **Then** retorna os bytes do objeto
3. **Given** erro de objeto não encontrado, **When** `download_file` é chamado, **Then** lança `S3NotFoundError`

---

### User Story 4 — Worker publica resultado no Kafka (Priority: P2)

Após processar o diagrama, o `worker-service` publica um `ArchitectureAnalysisCompletedEvent` no tópico Kafka `architecture-analysis-results`.

**Why this priority**: Necessário para fechar o pipeline com a notification-service.

**Independent Test**: Testar `KafkaProducer.publish(topic, event)` com mock do confluent-kafka.

**Acceptance Scenarios**:

1. **Given** um `ArchitectureAnalysisCompletedEvent`, **When** `KafkaProducer.publish(topic, event)` é chamado, **Then** o producer envia a mensagem com key=`diagram_id` e value=JSON do evento
2. **Given** broker indisponível, **When** `publish` é chamado, **Then** lança `KafkaPublishError`
3. **Given** um tópico e callback, **When** `KafkaConsumer.consume(topic, handler)` é chamado, **Then** chama `handler(event)` para cada mensagem recebida

---

### User Story 5 — Worker invoca LLM via SageMaker (Priority: P2)

O `worker-service` envia o contexto extraído pelo YOLO para o endpoint SageMaker e recebe o relatório em Markdown.

**Why this priority**: Core do negócio — gera o valor principal do sistema.

**Independent Test**: Testar `LLMClient.invoke(prompt)` com mock boto3 SageMaker Runtime.

**Acceptance Scenarios**:

1. **Given** um prompt com elementos detectados, **When** `LLMClient.invoke(prompt)` é chamado, **Then** boto3 `invoke_endpoint` é chamado e retorna a string do relatório
2. **Given** endpoint indisponível, **When** `invoke` é chamado, **Then** lança `LLMInvokeError`
3. **Given** resposta malformada do SageMaker, **When** o response body é parseado, **Then** lança `LLMResponseParseError`

---

### Edge Cases

- O que acontece quando boto3 recebe credenciais inválidas? → propagar como `AWSAuthError`
- Mensagem SQS com body inválido (não é JSON válido)? → `SQSMessage.parse_body()` lança `ValueError`
- Kafka producer não consegue confirmar entrega? → usar `delivery_timeout_ms` configurável

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `libs/aws/sqs_client.py` DEVE expor `send_message`, `receive_messages`, `delete_message`
- **FR-002**: `libs/aws/s3_client.py` DEVE expor `upload_file`, `download_file`
- **FR-003**: `libs/messaging/kafka_producer.py` DEVE expor `publish(topic, event)`
- **FR-004**: `libs/messaging/kafka_consumer.py` DEVE expor `consume(topic, handler)`
- **FR-005**: `libs/llm/sagemaker_client.py` DEVE expor `invoke(prompt) -> str`
- **FR-006**: Todos os clients DEVEM aceitar configuração via variáveis de ambiente (região AWS, endpoint, etc.)
- **FR-007**: Todos os erros de infraestrutura DEVEM ser encapsulados em exceções próprias do domínio (`libs/aws/exceptions.py`, etc.)
- **FR-008**: Clients AWS DEVEM usar `boto3` com suporte a injeção de cliente para testabilidade
- **FR-009**: Kafka client DEVE usar `confluent-kafka`

### Key Entities

- **`SQSClient`**: Wrapper boto3 SQS — send, receive, delete
- **`SQSMessage`**: DTO com `body: str`, `receipt_handle: str`, método `parse_body() -> dict`
- **`S3Client`**: Wrapper boto3 S3 — upload, download
- **`KafkaProducer`**: Wrapper confluent-kafka producer
- **`KafkaConsumer`**: Wrapper confluent-kafka consumer
- **`LLMClient`**: Wrapper boto3 SageMaker Runtime

---

## Success Criteria *(mandatory)*

- **SC-001**: Cobertura de testes ≥ 90% para todos os clients
- **SC-002**: Nenhum teste faz chamada real para AWS ou Kafka — 100% mocks
- **SC-003**: Todos os serviços importam clients exclusivamente de `shared/libs/`
- **SC-004**: Erros AWS/Kafka nunca vazam como `botocore.exceptions.*` para os serviços — sempre encapsulados

---

## Assumptions

- boto3 já disponível no ambiente
- confluent-kafka para Kafka (não kafka-python)
- Variáveis de ambiente: `AWS_REGION`, `SQS_QUEUE_URL`, `S3_BUCKET_NAME`, `KAFKA_BOOTSTRAP_SERVERS`, `SAGEMAKER_ENDPOINT_NAME`
- SageMaker responde com JSON `{"generated_text": "..."}` ou texto puro
