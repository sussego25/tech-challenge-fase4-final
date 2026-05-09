# Plan: 002 — Shared Libraries

## Objective
Implement reusable infrastructure clients (`SQSClient`, `S3Client`, `KafkaProducer`, `KafkaConsumer`, `LLMClient`) under `shared/libs/` with full unit test coverage.

## Architecture Decisions
- Each client receives dependencies via constructor injection (`boto_client`, `_producer`, `_consumer`) to enable unit testing without real cloud connections
- Kafka clients use **lazy import** pattern: `confluent_kafka` is only imported when no mock is injected — avoids import errors in environments without the package
- All clients raise domain-specific exceptions (never raw `botocore.exceptions.ClientError` or similar)
- Pydantic models are serialized via `.model_dump_json()` before sending

## Module Breakdown

### `libs/aws/`
| File | Responsibility |
|------|---------------|
| `sqs_client.py` | Send, receive, delete SQS messages |
| `s3_client.py`  | Upload and download bytes from S3 |
| `exceptions.py` | `AWSAuthError`, `SQSPublishError`, `SQSDeleteError`, `S3UploadError`, `S3NotFoundError` |

### `libs/messaging/`
| File | Responsibility |
|------|---------------|
| `kafka_producer.py` | Publish JSON payloads to Kafka topics |
| `kafka_consumer.py` | Consume messages from a topic in an infinite poll loop |
| `exceptions.py`     | `KafkaPublishError`, `KafkaConsumeError` |

### `libs/llm/`
| File | Responsibility |
|------|---------------|
| `sagemaker_client.py` | Invoke SageMaker endpoint, parse `generated_text` response |
| `exceptions.py`       | `LLMInvokeError`, `LLMResponseParseError` |

## Testing Strategy
- All tests use dependency injection (no real AWS/Kafka/SageMaker calls)
- `boto3.exceptions` simulated with `MagicMock(side_effect=ClientError(...))`
- Kafka loop break simulated with `StopIteration` raised by mock consumer
- PYTHONPATH must be set to `./shared` before running tests

## Test Counts
| Module | Tests |
|--------|-------|
| `test_s3_client.py`        | 8  |
| `test_sqs_client.py`       | 12 |
| `test_kafka_producer.py`   | 5  |
| `test_kafka_consumer.py`   | 5  |
| `test_sagemaker_client.py` | 5  |
| **Total**                  | **35** |

## Run Command
```bash
cd tech-challenger
$env:PYTHONPATH = ".\shared"
python -m pytest tests/unit/shared/libs/ -v --no-cov
```
