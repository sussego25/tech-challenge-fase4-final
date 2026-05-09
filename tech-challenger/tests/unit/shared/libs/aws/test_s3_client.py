import pytest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from libs.aws.s3_client import S3Client
from libs.aws.exceptions import S3UploadError, S3NotFoundError


@pytest.fixture
def mock_boto_client():
    return MagicMock()


@pytest.fixture
def s3(mock_boto_client):
    return S3Client(bucket_name="my-bucket", boto_client=mock_boto_client)


class TestS3ClientInit:
    def test_raises_when_bucket_name_empty(self):
        with pytest.raises(ValueError, match="bucket_name"):
            S3Client(bucket_name="")

    def test_raises_when_bucket_name_none(self):
        with pytest.raises(ValueError, match="bucket_name"):
            S3Client(bucket_name=None)


class TestS3ClientUpload:
    def test_upload_file_calls_put_object(self, s3, mock_boto_client):
        data = b"PNG_IMAGE_BYTES"
        s3.upload_file(data=data, s3_key="diagrams/test.png", content_type="image/png")
        mock_boto_client.put_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="diagrams/test.png",
            Body=data,
            ContentType="image/png",
        )

    def test_upload_file_raises_s3_upload_error_on_failure(self, s3, mock_boto_client):
        mock_boto_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Error"}}, "PutObject"
        )
        with pytest.raises(S3UploadError, match="Failed to upload"):
            s3.upload_file(b"data", "key.png", "image/png")

    def test_upload_uses_default_content_type(self, s3, mock_boto_client):
        s3.upload_file(b"data", "key.png")
        call_args = mock_boto_client.put_object.call_args
        assert call_args.kwargs["ContentType"] == "application/octet-stream"


class TestS3ClientDownload:
    def test_download_file_returns_bytes(self, s3, mock_boto_client):
        mock_boto_client.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=b"IMAGE_DATA"))
        }
        result = s3.download_file("diagrams/test.png")
        assert result == b"IMAGE_DATA"

    def test_download_raises_s3_not_found_on_nosuchkey(self, s3, mock_boto_client):
        mock_boto_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )
        with pytest.raises(S3NotFoundError, match="not found"):
            s3.download_file("missing/key.png")

    def test_download_raises_s3_upload_error_on_other_errors(self, s3, mock_boto_client):
        mock_boto_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Error"}}, "GetObject"
        )
        with pytest.raises(S3UploadError):
            s3.download_file("key.png")
