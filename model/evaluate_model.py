"""
Model Evaluation — Standalone evaluation of a trained model on the test set.

Usage:
  python model/evaluate_model.py
  python model/evaluate_model.py --model model/skin_model.h5 --dataset dataset/
"""

import os
import sys
import json
import argparse
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def evaluate_model(model_path: str, dataset_path: str, image_size: int = 224):
    """
    Evaluate a trained model on the test set.
    Generates classification report, confusion matrix, and accuracy metrics.
    """
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Load model
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        sys.exit(1)

    print(f"  Loading model: {model_path}")
    model = tf.keras.models.load_model(model_path)

    # Load class names
    class_names_path = os.path.join(os.path.dirname(model_path), "class_names.json")
    if os.path.exists(class_names_path):
        with open(class_names_path, "r") as f:
            class_names = json.load(f).get("classes", [])
    else:
        class_names = None

    # Create test data generator
    test_dir = os.path.join(dataset_path, "test")
    if not os.path.isdir(test_dir):
        print(f"[ERROR] Test directory not found: {test_dir}")
        sys.exit(1)

    test_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        preprocessing_function=tf.keras.applications.efficientnet.preprocess_input,
    )

    test_gen = test_datagen.flow_from_directory(
        test_dir,
        target_size=(image_size, image_size),
        batch_size=32,
        class_mode="categorical",
        shuffle=False,
    )

    if class_names is None:
        class_names = list(test_gen.class_indices.keys())

    # Predict
    print("  Running predictions on test set...")
    predictions = model.predict(test_gen, verbose=1)
    y_pred = np.argmax(predictions, axis=1)
    y_true = test_gen.classes

    # Reports directory
    reports_dir = os.path.join(os.path.dirname(model_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Classification report
    report = classification_report(
        y_true, y_pred, target_names=class_names, digits=4
    )

    print(f"\n{'='*60}")
    print("  CLASSIFICATION REPORT")
    print(f"{'='*60}")
    print(report)

    report_path = os.path.join(reports_dir, "classification_report.txt")
    with open(report_path, "w") as f:
        f.write("DERMA ASSIST — Classification Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Model: {model_path}\n")
        f.write(f"Test Set: {test_dir}\n")
        f.write(f"Number of Classes: {len(class_names)}\n\n")
        f.write(report)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    fig_size = max(10, len(class_names))
    plt.figure(figsize=(fig_size, fig_size * 0.8))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names,
    )
    plt.title("Confusion Matrix — Derma Assist", fontsize=14)
    plt.xlabel("Predicted", fontsize=12)
    plt.ylabel("Actual", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    cm_path = os.path.join(reports_dir, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=150)
    plt.close()

    # Test accuracy
    test_loss, test_acc = model.evaluate(test_gen, verbose=0)

    print(f"\n  TEST ACCURACY:  {test_acc:.4f} ({test_acc:.1%})")
    print(f"  TEST LOSS:      {test_loss:.4f}")
    print(f"\n  Reports saved to: {reports_dir}")
    print(f"    - {report_path}")
    print(f"    - {cm_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate a trained Derma Assist model")
    parser.add_argument(
        "--model", default=os.path.join(PROJECT_ROOT, "model", "skin_model.h5"),
        help="Path to the trained model file"
    )
    parser.add_argument(
        "--dataset", default=os.path.join(PROJECT_ROOT, "dataset"),
        help="Path to the dataset directory"
    )
    parser.add_argument("--image-size", type=int, default=224, help="Image size")
    args = parser.parse_args()

    evaluate_model(args.model, args.dataset, args.image_size)


if __name__ == "__main__":
    main()
