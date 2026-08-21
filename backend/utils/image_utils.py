"""
Image Utilities — Validation, resizing, preprocessing for EfficientNetB0.
"""

import io
import base64
import numpy as np
from PIL import Image
from fastapi import HTTPException

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_IMAGE_SIZE = 224


def validate_image(file_bytes: bytes, filename: str, max_size_bytes: int) -> Image.Image:
    """
    Validate an uploaded image file.
    Checks: file size, extension, corruption.
    Returns a PIL Image if valid.
    """
    # Check file size
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Image file too large. Maximum size is {max_mb:.0f}MB."
        )

    # Check extension
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Try to open and validate
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # Check for corruption
        # Re-open after verify (verify() closes the file)
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert("RGB")
        return img
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Image file is corrupted or cannot be read."
        )


def preprocess_image(img: Image.Image, image_size: int = DEFAULT_IMAGE_SIZE) -> np.ndarray:
    """
    Preprocess a PIL Image for EfficientNetB0 inference.
    - Resize to (image_size, image_size)
    - Convert to numpy array
    - Scale to [0, 255] range (EfficientNetB0 uses its own preprocessing)
    - Add batch dimension
    """
    img = img.resize((image_size, image_size), Image.LANCZOS)
    img_array = np.array(img, dtype=np.float32)

    # EfficientNetB0 expects pixel values in [0, 255]
    # The tf.keras.applications.efficientnet.preprocess_input handles normalization
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

    return img_array


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert a PIL Image to base64 string."""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def numpy_to_base64(img_array: np.ndarray) -> str:
    """Convert a numpy array (H, W, 3) to base64 PNG string."""
    if img_array.max() <= 1.0:
        img_array = (img_array * 255).astype(np.uint8)
    else:
        img_array = img_array.astype(np.uint8)

    img = Image.fromarray(img_array)
    return image_to_base64(img)
