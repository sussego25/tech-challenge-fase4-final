import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from libs.aws.exceptions import S3UploadError, S3NotFoundError


class S3Client:
    def __init__(
        self,
        bucket_name: str | None = None,
        region: str | None = None,
        boto_client: Any = None,
    ) -> None:
        self._bucket = bucket_name or ""
        self._client = boto_client or boto3.client(
            "s3", region_name=region or os.getenv("AWS_REGION")
        )

    def upload_file(
        self,
        data: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
            )
        except ClientError as e:
            raise S3UploadError(f"Failed to upload {s3_key} to S3: {e}") from e

    def download_file(self, s3_key: str, bucket: str | None = None) -> bytes:
        bucket_name = bucket or self._bucket
        try:
            response = self._client.get_object(Bucket=bucket_name, Key=s3_key)
            return response["Body"].read()
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "NoSuchKey":
                raise S3NotFoundError(f"Object {s3_key} not found in bucket {bucket_name}") from e
            raise S3UploadError(f"Failed to download {s3_key} from S3: {e}") from e
