import os


class Settings:
    SQS_QUEUE_URL: str = os.environ.get("SQS_QUEUE_URL", "")
    SNS_TOPIC_ARN: str = os.environ.get("SNS_TOPIC_ARN", "")
    S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
    DYNAMODB_TABLE: str = os.environ.get("DYNAMODB_TABLE", "")
    YOLO_SAGEMAKER_ENDPOINT: str = os.environ.get(
        "YOLO_SAGEMAKER_ENDPOINT",
        os.environ.get("SAGEMAKER_ENDPOINT", ""),
    )
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "sagemaker").lower()
    SAGEMAKER_ENDPOINT: str = os.environ.get("SAGEMAKER_ENDPOINT", "")
    BEDROCK_MODEL_ID: str = os.environ.get("BEDROCK_MODEL_ID", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
