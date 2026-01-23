"""ai_utils.py
Standalone AI utility script for extracting face embeddings.

Responsibilities:
  - Load an image
  - Detect multiple faces
  - Output 128-d embeddings + bounding boxes

This script uses:
  - opencv-python (cv2) for image loading
  - face-recognition (dlib-based) for face detection + encodings

Run:
  python backend/ai_utils.py path\\to\\image.jpg
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_deps():
    """Import heavy/optional deps only when needed."""
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: opencv-python. "
            "Install with: pip install opencv-python"
        ) from exc

    try:
        import face_recognition  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: face-recognition. "
            "Install with: pip install face-recognition"
        ) from exc

    return cv2, face_recognition


def extract_faces(
    image_path: str | Path,
    *,
    model: str = "hog",
    upsample: int = 1,
    num_jitters: int = 1,
) -> dict:
    """Return face bounding boxes and 128-d embeddings for all faces in an image.

    Bounding box format matches face_recognition: (top, right, bottom, left).
    """

    cv2, face_recognition = _load_deps()

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError(
            f"Failed to read image (unsupported format or corrupt file): {path}"
        )

    # face_recognition expects RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    locations = face_recognition.face_locations(
        image_rgb,
        number_of_times_to_upsample=upsample,
        model=model,
    )
    encodings = face_recognition.face_encodings(
        image_rgb,
        known_face_locations=locations,
        num_jitters=num_jitters,
    )

    faces: list[dict] = []
    for idx, (loc, enc) in enumerate(zip(locations, encodings)):
        top, right, bottom, left = loc
        faces.append(
            {
                "index": idx,
                "bounding_box": {
                    "top": int(top),
                    "right": int(right),
                    "bottom": int(bottom),
                    "left": int(left),
                },
                "embedding": [float(x) for x in enc.tolist()],
            }
        )

    return {
        "image": str(path),
        "face_count": len(faces),
        "faces": faces,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Detect faces and output 128-d embeddings + bounding boxes as JSON."
    )
    parser.add_argument("image", help="Path to an image file")
    parser.add_argument(
        "--model",
        choices=("hog", "cnn"),
        default="hog",
        help="Face detector backend (cnn requires more compute)",
    )
    parser.add_argument(
        "--upsample",
        type=int,
        default=1,
        help="Times to upsample the image when looking for faces",
    )
    parser.add_argument(
        "--jitters",
        type=int,
        default=1,
        help="How many times to re-sample when calculating encodings",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (0 for compact)",
    )

    args = parser.parse_args(argv)

    try:
        payload = extract_faces(
            args.image,
            model=args.model,
            upsample=args.upsample,
            num_jitters=args.jitters,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    indent = None if args.indent == 0 else args.indent
    print(json.dumps(payload, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
