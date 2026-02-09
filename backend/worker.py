import os
import tempfile
import logging

from celery_app import celery_app
from database import SessionLocal
from models import Face
from ai_utils import extract_faces
from s3_utils import _s3_client, S3_BUCKET_NAME

logger = logging.getLogger(__name__)

@celery_app.task(name="worker.process_image")
def process_image(image_id: str, s3_key: str):
    logger.info(f"Processing image {image_id} from {s3_key}")

    # Download image directly from S3 into a temporary file.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            s3_response = _s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            for chunk in s3_response["Body"].iter_chunks():
                tmp.write(chunk)

        # Extract faces from the downloaded file
        logger.info(f"Extracting faces for {image_id}")
        result = extract_faces(tmp_path)

        # Save faces to the database
        faces_data = result.get("faces", [])
        logger.info(f"Found {len(faces_data)} faces for image {image_id}")

        db = SessionLocal()
        try:
            for face_data in faces_data:
                face = Face(
                    image_id=image_id,
                    embedding=face_data["embedding"],
                    bounding_box=face_data["bounding_box"],
                )
                db.add(face)
            db.commit()
            logger.info(f"Saved {len(faces_data)} faces for image {image_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while saving faces for {image_id}: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Worker failed for image {image_id}: {e}")
        raise
    finally:
        # Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {"status": "success", "image_id": image_id, "faces_found": result.get("face_count", 0)}
