import hashlib
from typing import Protocol
import boto3
from botocore.config import Config
from ..config import get_settings

ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic"}
MAX_BYTES = 12 * 1024 * 1024


class Storage(Protocol):
    def presign_put(self, key: str, content_type: str, expires: int = 600) -> str: ...
    def presign_get(self, key: str, expires: int = 600) -> str: ...
    def head(self, key: str) -> dict | None: ...
    def get_bytes(self, key: str) -> bytes: ...


def derive_r2_secret(api_token: str) -> str:
    """El secreto S3 de un token de API de Cloudflare es el SHA-256 del valor del token."""
    return hashlib.sha256(api_token.encode()).hexdigest()


class R2Storage:
    def __init__(self):
        s = get_settings()
        secret = s.r2_secret_access_key or (derive_r2_secret(s.cloudflare_api_token) if s.cloudflare_api_token else "")
        self.bucket = s.r2_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{s.cloudflare_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=s.r2_access_key_id, aws_secret_access_key=secret,
            region_name="auto", config=Config(signature_version="s3v4"),
        )

    def presign_put(self, key, content_type, expires=600):
        return self.client.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type}, ExpiresIn=expires)

    def presign_get(self, key, expires=600):
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires)

    def head(self, key):
        try:
            r = self.client.head_object(Bucket=self.bucket, Key=key)
            return {"size": r["ContentLength"], "content_type": r.get("ContentType")}
        except Exception:
            return None

    def get_bytes(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def get_storage() -> Storage:
    return R2Storage()
