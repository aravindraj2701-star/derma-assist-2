"""
Tests for the Image Utilities.
"""

import sys
import os
import numpy as np
from PIL import Image
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.utils.image_utils import preprocess_image, image_to_base64, numpy_to_base64


def test_preprocess_image():
    """Test image preprocessing produces correct shape."""
    # Create a dummy image
    img = Image.new("RGB", (500, 500), color=(128, 100, 80))
    result = preprocess_image(img, image_size=224)
    assert result.shape == (1, 224, 224, 3), f"Expected (1, 224, 224, 3), got {result.shape}"
    assert result.dtype == np.float32
    print("✅ test_preprocess_image passed")


def test_preprocess_different_sizes():
    """Test preprocessing with different image sizes."""
    img = Image.new("RGB", (300, 200), color=(50, 50, 50))

    for size in [224, 128, 380]:
        result = preprocess_image(img, image_size=size)
        assert result.shape == (1, size, size, 3)
    print("✅ test_preprocess_different_sizes passed")


def test_image_to_base64():
    """Test PIL image to base64 conversion."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    b64 = image_to_base64(img)
    assert isinstance(b64, str)
    assert len(b64) > 0
    print("✅ test_image_to_base64 passed")


def test_numpy_to_base64():
    """Test numpy array to base64 conversion."""
    arr = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    b64 = numpy_to_base64(arr)
    assert isinstance(b64, str)
    assert len(b64) > 0
    print("✅ test_numpy_to_base64 passed")


if __name__ == "__main__":
    test_preprocess_image()
    test_preprocess_different_sizes()
    test_image_to_base64()
    test_numpy_to_base64()
    print("\n🎉 All image utility tests passed!")
