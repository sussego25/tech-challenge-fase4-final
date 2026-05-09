import os


class Config:
    S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
    SQS_QUEUE_URL: str = os.environ.get("SQS_QUEUE_URL", "")
    DYNAMODB_TABLE: str = os.environ.get("DYNAMODB_TABLE", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
