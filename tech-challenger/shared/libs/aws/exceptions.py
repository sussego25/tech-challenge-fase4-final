class AWSAuthError(Exception):
    """Raised when AWS credentials are invalid or missing."""


class SQSPublishError(Exception):
    """Raised when a message cannot be published to SQS."""


class SNSPublishError(Exception):
    """Raised when a message cannot be published to SNS."""


class SQSDeleteError(Exception):
    """Raised when a message cannot be deleted from SQS."""


class S3UploadError(Exception):
    """Raised when a file cannot be uploaded to S3."""


class S3NotFoundError(Exception):
    """Raised when an S3 object is not found."""
