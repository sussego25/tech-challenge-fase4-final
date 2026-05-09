import logging

import boto3

from config.settings import Settings
from consumers.sqs_consumer import SQSConsumer
from domain.analysis_service import AnalysisService
from infrastructure.diagram_repository import DynamoDBDiagramRepository
from infrastructure.yolo_detector import YoloDetector
from libs.aws.s3_client import S3Client
from libs.aws.sns_client import SNSClient
from libs.aws.sqs_client import SQSClient
from libs.llm import LLMClient
from processors.diagram_processor import DiagramProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()

    if not settings.SQS_QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL env var is not set — cannot start worker")
    if not settings.SNS_TOPIC_ARN:
        raise RuntimeError("SNS_TOPIC_ARN env var is not set — cannot start worker")
    if not settings.YOLO_SAGEMAKER_ENDPOINT:
        raise RuntimeError(
            "YOLO_SAGEMAKER_ENDPOINT env var is not set — cannot start worker"
        )

    s3_client = S3Client(region=settings.AWS_REGION)
    sqs_client = SQSClient(queue_url=settings.SQS_QUEUE_URL, region=settings.AWS_REGION)
    sns_client = SNSClient(topic_arn=settings.SNS_TOPIC_ARN, region=settings.AWS_REGION)
    yolo_detector = YoloDetector(
        endpoint_name=settings.YOLO_SAGEMAKER_ENDPOINT,
        region=settings.AWS_REGION,
    )

    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    table = dynamodb.Table(settings.DYNAMODB_TABLE)
    repo = DynamoDBDiagramRepository(table=table)

    if settings.LLM_PROVIDER == "sagemaker":
        if not settings.SAGEMAKER_ENDPOINT:
            raise RuntimeError(
                "SAGEMAKER_ENDPOINT env var is not set — cannot start worker"
            )
    elif settings.LLM_PROVIDER == "bedrock":
        if not settings.BEDROCK_MODEL_ID:
            raise RuntimeError(
                "BEDROCK_MODEL_ID env var is not set — cannot start worker"
            )
    else:
        raise RuntimeError(
            "LLM_PROVIDER env var must be either 'sagemaker' or 'bedrock'"
        )

    llm_client = LLMClient(
        provider=settings.LLM_PROVIDER,
        endpoint_name=settings.SAGEMAKER_ENDPOINT,
        model_id=settings.BEDROCK_MODEL_ID,
        region=settings.AWS_REGION,
    )
    analysis_service = AnalysisService(llm_client=llm_client)
    processor = DiagramProcessor(
        s3_client=s3_client,
        analysis_service=analysis_service,
        repository=repo,
        yolo_detector=yolo_detector,
        sns_client=sns_client,
    )
    consumer = SQSConsumer(sqs_client=sqs_client, processor=processor)

    logger.info("Worker service starting...")
    consumer.run()


if __name__ == "__main__":
    main()
