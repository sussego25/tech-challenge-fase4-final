import logging
import urllib.parse
from typing import Any

import boto3

from config import Config
from repositories import DynamoDBDiagramRepository
from use_cases import ProcessDiagramUploadUseCase
from libs.aws.sqs_client import SQSClient

logger = logging.getLogger(__name__)

_use_case: ProcessDiagramUploadUseCase | None = None


def _get_use_case() -> ProcessDiagramUploadUseCase:
    global _use_case
    if _use_case is None:
        config = Config()
        sqs_client = SQSClient(queue_url=config.SQS_QUEUE_URL, region=config.AWS_REGION)
        dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
        table = dynamodb.Table(config.DYNAMODB_TABLE)
        repo = DynamoDBDiagramRepository(table=table)
        _use_case = ProcessDiagramUploadUseCase(
            sqs_client=sqs_client,
            repository=repo,
        )
    return _use_case


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    records = event.get("Records", [])
    for record in records:
        s3_info = record.get("s3", {})
        bucket_name = s3_info["bucket"]["name"]
        s3_key = urllib.parse.unquote_plus(s3_info["object"]["key"])

        s3_client = boto3.client("s3")
        try:
            object_info = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        except Exception:
            logger.exception("Failed to verify object %s/%s", bucket_name, s3_key)
            raise

        content_length = object_info.get("ContentLength", 0)
        content_type = object_info.get("ContentType", "")
        if s3_key.endswith("/") or content_length == 0 or not content_type.startswith("image/"):
            logger.info(
                "Ignoring non-image S3 object: bucket=%s key=%s content_type=%s content_length=%s",
                bucket_name,
                s3_key,
                content_type,
                content_length,
            )
            continue

        try:
            use_case = _get_use_case()
            use_case.execute(s3_bucket=bucket_name, s3_key=s3_key)
        except Exception:
            logger.exception("Unexpected error processing S3 event for %s/%s", bucket_name, s3_key)
            raise
