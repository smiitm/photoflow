"""
s3_utils.py
Standalone utility functions for interacting with AWS S3.

Responsibilities:
  - Upload an image file (from a local path or raw bytes) to the private S3 bucket.
  - Generate a time-limited presigned URL so a client can securely download a file
    directly from S3 without needing AWS credentials.
"""

import os
import uuid
import logging
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv


# Configuration --------------------------------------------------
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
    raise EnvironmentError(
        "Missing required AWS environment variables. "
        "Ensure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME are set in .env"
    )

logger = logging.getLogger(__name__)

# S3 Client --------------------------------------------------
_s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


# Public API --------------------------------------------------
def upload_image(
    source: str | Path | bytes,
    s3_key: str | None = None,
    content_type: str = "image/jpeg",
    project_id: str | None = None,
) -> str:
    """Upload an image to the configured S3 bucket.

    Parameters
    - source: Either a local file path (str or Path) **or** raw image bytes.
    - s3_key: The desired key (path) inside the bucket.  When omitted a unique key is auto-generated using the pattern ``<project_id>/<uuid4>.<ext>``.
    - content_type: MIME type stored as the object's ContentType metadata. Defaults to ``"image/jpeg"``.
    - project_id: Optional project UUID used as the top-level S3 "folder" when auto-generating the key.  Ignored when ``s3_key`` is provided.

    Returns
    - str : The S3 key of the uploaded object.

    Raises
    - FileNotFoundError : If ``source`` is a path that does not exist on disk.
    - ClientError / BotoCoreError : On any AWS-side upload failure.
    """

    # Resolve source to bytes 
    if isinstance(source, (str, Path)):
        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(f"Image not found: {file_path}")
        file_bytes = file_path.read_bytes()
        extension = file_path.suffix.lstrip(".") or "jpg"
    elif isinstance(source, bytes):
        file_bytes = source
        extension = "jpg"
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")

    # Build S3 key if not provided 
    if s3_key is None:
        unique_id = uuid.uuid4()
        prefix = f"{project_id}/" if project_id else "uploads/"
        s3_key = f"{prefix}{unique_id}.{extension}"

    # Upload
    try:
        _s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info("Uploaded %d bytes to s3://%s/%s", len(file_bytes), S3_BUCKET_NAME, s3_key)
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed for key '%s': %s", s3_key, exc)
        raise

    return s3_key


def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """Generate a time-limited presigned URL for a private S3 object.

    Parameters
    - s3_key: The key of the object inside the bucket (as returned by :func:`upload_image` or stored in ``images.s3_key``).
    - expiry_seconds: How long the URL remains valid.  Defaults to ``3600`` (1 hour). AWS allows a maximum of 604 800 seconds (7 days) for this operation.

    Returns
    - str : A presigned HTTPS URL that grants temporary read access to the object.

    Raises
    - ClientError / BotoCoreError : On any AWS-side failure.
    """
    try:
        url = _s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )
        logger.info(
            "Presigned URL generated for '%s' (expires in %ds)", s3_key, expiry_seconds
        )
        return url
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to generate presigned URL for '%s': %s", s3_key, exc)
        raise


# Quick smoke-test --------------------------------------------------
# (run directly: python s3_utils.py)

if __name__ == "__main__":
    import sys
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    # Create a tiny 1×1 white JPEG in memory (no Pillow required)
    # This is a valid minimal JPEG binary so the test doesn't depend on any
    # image library being installed.
    MINIMAL_JPEG = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05"
        b"\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06"
        b"\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1"
        b"\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJ"
        b"STUVWXYZ"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xca(\xa2\x80\xff\xd9"
    )

    print("=== PhotoFlow S3 Utility Smoke-Test ===\n")

    test_project = "test-project-001"

    print("1. Uploading minimal test image as raw bytes...")
    key = upload_image(MINIMAL_JPEG, project_id=test_project, content_type="image/jpeg")
    print(f"   [OK] Uploaded -> s3://{S3_BUCKET_NAME}/{key}\n")

    print("2. Generating a 60-second presigned URL...")
    url = generate_presigned_url(key, expiry_seconds=60)
    print(f"   [OK] URL (valid 60 s):\n   {url}\n")

    print("=== All tests passed [OK] ===")
    sys.exit(0)
