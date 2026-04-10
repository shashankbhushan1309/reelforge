"""Cloudflare R2 (S3-compatible) storage client."""

import io
import logging
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from shared.config import get_settings

logger = logging.getLogger(__name__)


class R2StorageClient:
    """Cloudflare R2 storage client using S3-compatible API."""

    def __init__(self):
        settings = get_settings()
        self._bucket = settings.r2.bucket_name
        self._public_url = settings.r2.public_url

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2.endpoint_url,
            aws_access_key_id=settings.r2.access_key_id,
            aws_secret_access_key=settings.r2.secret_access_key,
            config=BotoConfig(
                region_name="auto",
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def upload_file(self, local_path: str, r2_key: str, content_type: str = "application/octet-stream") -> str:
        """Upload a file to R2 and return the public URL."""
        try:
            self._client.upload_file(
                local_path,
                self._bucket,
                r2_key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info(f"Uploaded {local_path} -> {r2_key}")
            return f"{self._public_url}/{r2_key}"
        except ClientError as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            raise

    def upload_bytes(self, data: bytes, r2_key: str, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to R2 and return the public URL."""
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=r2_key,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Uploaded bytes -> {r2_key}")
            return f"{self._public_url}/{r2_key}"
        except ClientError as e:
            logger.error(f"Failed to upload bytes to {r2_key}: {e}")
            raise

    def download_file(self, r2_key: str, local_path: str) -> str:
        """Download a file from R2 to local path."""
        try:
            self._client.download_file(self._bucket, r2_key, local_path)
            logger.info(f"Downloaded {r2_key} -> {local_path}")
            return local_path
        except ClientError as e:
            logger.error(f"Failed to download {r2_key}: {e}")
            raise

    def download_bytes(self, r2_key: str) -> bytes:
        """Download file content as bytes."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=r2_key)
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"Failed to download {r2_key}: {e}")
            raise

    def generate_presigned_url(self, r2_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for temporary access."""
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": r2_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {r2_key}: {e}")
            raise

    def delete_file(self, r2_key: str) -> None:
        """Delete a file from R2."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=r2_key)
            logger.info(f"Deleted {r2_key}")
        except ClientError as e:
            logger.error(f"Failed to delete {r2_key}: {e}")
            raise

    def file_exists(self, r2_key: str) -> bool:
        """Check if a file exists in R2."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=r2_key)
            return True
        except ClientError:
            return False

    def get_public_url(self, r2_key: str) -> str:
        """Get the public CDN URL for a stored file."""
        return f"{self._public_url}/{r2_key}"


# Singleton instance
_storage_client: Optional[R2StorageClient] = None


def get_storage() -> R2StorageClient:
    """Get or create the singleton storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = R2StorageClient()
    return _storage_client
