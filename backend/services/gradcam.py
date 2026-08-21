"""
Grad-CAM Service — Generate Gradient-weighted Class Activation Maps for EfficientNetB0.

Grad-CAM highlights regions of the input image that most influenced the model's prediction.
IMPORTANT: Grad-CAM only shows which areas the AI focused on. It does NOT prove a diagnosis.
"""

import numpy as np
import cv2
from PIL import Image
import io
import base64


def generate_gradcam(
    model,
    img_array: np.ndarray,
    class_index: int,
    image_size: int = 224,
    layer_name: str = None,
) -> dict:
    """
    Generate Grad-CAM heatmap for a given prediction.

    Args:
        model: Loaded Keras model (EfficientNetB0-based)
        img_array: Preprocessed image array of shape (1, H, W, 3)
        class_index: The predicted class index to explain
        image_size: Size of the input image
        layer_name: Name of the convolutional layer to target. If None, auto-detects.

    Returns:
        Dict with base64-encoded images:
        - heatmap: The raw heatmap
        - overlay: Heatmap overlaid on the original image
    """
    if model is None:
        return _mock_gradcam(img_array, image_size)

    try:
        import tensorflow as tf

        # Auto-detect the last convolutional layer if not specified
        if layer_name is None:
            layer_name = _find_last_conv_layer(model)

        if layer_name is None:
            print("[WARN] Could not find a convolutional layer for Grad-CAM")
            return _mock_gradcam(img_array, image_size)

        # Create a model that outputs both the conv layer output and the final predictions
        grad_model = tf.keras.Model(
            inputs=model.input,
            outputs=[
                model.get_layer(layer_name).output,
                model.output,
            ],
        )

        # Apply EfficientNet preprocessing
        processed = tf.keras.applications.efficientnet.preprocess_input(img_array.copy())

        # Compute gradients
        with tf.GradientTape() as tape:
            conv_output, predictions = grad_model(processed)
            loss = predictions[:, class_index]

        # Gradients of the predicted class with respect to the conv layer output
        grads = tape.gradient(loss, conv_output)

        # Global average pooling of gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight the conv output channels by the pooled gradients
        conv_output = conv_output[0]
        heatmap = conv_output @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        # ReLU and normalize
        heatmap = tf.maximum(heatmap, 0)
        if tf.reduce_max(heatmap) > 0:
            heatmap = heatmap / tf.reduce_max(heatmap)

        heatmap = heatmap.numpy()

        # Resize heatmap to match image size
        heatmap_resized = cv2.resize(heatmap, (image_size, image_size))

        # Create colorized heatmap
        heatmap_colored = cv2.applyColorMap(
            np.uint8(255 * heatmap_resized), cv2.COLORMAP_JET
        )
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        # Get original image for overlay
        original = img_array[0].copy()
        if original.max() > 1.0:
            original = original / 255.0
        original_uint8 = np.uint8(255 * original)

        # Create overlay
        overlay = cv2.addWeighted(original_uint8, 0.6, heatmap_colored, 0.4, 0)

        return {
            "heatmap": _numpy_to_base64(heatmap_colored),
            "overlay": _numpy_to_base64(overlay),
        }

    except Exception as e:
        print(f"[ERROR] Grad-CAM generation failed: {e}")
        return _mock_gradcam(img_array, image_size)


def _find_last_conv_layer(model) -> str:
    """Find the name of the last convolutional layer in the model."""
    for layer in reversed(model.layers):
        if "conv" in layer.name.lower() and len(layer.output_shape) == 4:
            return layer.name
    # Fallback: look in the EfficientNet base
    for layer in reversed(model.layers):
        if hasattr(layer, "layers"):  # It's a nested model
            for sub_layer in reversed(layer.layers):
                if "conv" in sub_layer.name.lower() and len(sub_layer.output_shape) == 4:
                    return sub_layer.name
    return None


def _mock_gradcam(img_array: np.ndarray, image_size: int = 224) -> dict:
    """
    Generate a mock Grad-CAM visualization when no model is available.
    Creates a simple centered gradient heatmap for demonstration.
    """
    # Create a simple circular gradient heatmap
    y, x = np.ogrid[-1:1:image_size * 1j, -1:1:image_size * 1j]
    heatmap = np.exp(-(x * x + y * y) / 0.5)
    heatmap = (heatmap * 255).astype(np.uint8)

    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    # Get original image for overlay
    if img_array is not None and len(img_array.shape) == 4:
        original = img_array[0].copy()
        if original.max() > 1.0:
            original = original / 255.0
        original = cv2.resize(np.uint8(original * 255), (image_size, image_size))
    else:
        original = np.ones((image_size, image_size, 3), dtype=np.uint8) * 128

    overlay = cv2.addWeighted(original, 0.6, heatmap_colored, 0.4, 0)

    return {
        "heatmap": _numpy_to_base64(heatmap_colored),
        "overlay": _numpy_to_base64(overlay),
        "_mock": True,
    }


def _numpy_to_base64(img_array: np.ndarray) -> str:
    """Convert numpy array to base64 PNG string."""
    img = Image.fromarray(img_array.astype(np.uint8))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
