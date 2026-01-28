import os
import tempfile
import logging
import httpx

from celery_app import celery_app
from database import SessionLocal
from models import Face
from ai_utils import extract_faces
from s3_utils import generate_presigned_url

logger = logging.getLogger(__name__)

@celery_app.task(name="worker.process_image")
def process_image(image_id: str, s3_key: str):
    logger.info(f"Processing image {image_id} from {s3_key}")
    
    # 1. Get presigned URL
    try:
        url = generate_presigned_url(s3_key)
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
        raise e
        
    # 2. Download image to temporary file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        with httpx.stream("GET", url) as response:
            response.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    
        # 3. Extract faces
        logger.info(f"Extracting faces for {image_id}")
        result = extract_faces(tmp_path)
        
        # 4. Save to database
        db = SessionLocal()
        try:
            faces_data = result.get("faces", [])
            logger.info(f"Found {len(faces_data)} faces for image {image_id}")
            
            for face_data in faces_data:
                face = Face(
                    image_id=image_id,
                    embedding=face_data["embedding"],
                    bounding_box=face_data["bounding_box"]
                )
                db.add(face)
            db.commit()
            logger.info(f"Successfully saved {len(faces_data)} faces to database for image {image_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while saving faces for {image_id}: {e}")
            raise e
        finally:
            db.close()
            
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return {"status": "success", "image_id": image_id, "faces_found": result.get("face_count", 0)}
