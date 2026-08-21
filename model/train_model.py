"""
Model Training — EfficientNetB0 Transfer Learning for Skin Disease Classification.

Training pipeline:
1. Load and preprocess dataset
2. Build EfficientNetB0 with classification head
3. Train with frozen base (feature extraction)
4. Fine-tune with unfrozen top layers
5. Evaluate on test set
6. Save model + configuration

All parameters are configurable via config.json or command-line arguments.
"""

import os
import sys
import json
import argparse
import numpy as np
from pathlib import Path
from collections import Counter

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def load_config(config_path: str = None) -> dict:
    """Load training configuration."""
    default_config = {
        "image_size": 224,
        "batch_size": 32,
        "epochs_frozen": 10,
        "epochs_finetune": 10,
        "learning_rate": 1e-3,
        "learning_rate_finetune": 1e-5,
        "dataset_path": os.path.join(PROJECT_ROOT, "dataset"),
        "model_path": os.path.join(PROJECT_ROOT, "model", "skin_model.h5"),
        "class_names_path": os.path.join(PROJECT_ROOT, "model", "class_names.json"),
        "model_config_path": os.path.join(PROJECT_ROOT, "model", "model_config.json"),
        "reports_dir": os.path.join(PROJECT_ROOT, "model", "reports"),
    }

    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            user_config = json.load(f)
            default_config.update(user_config)

    return default_config


def create_data_generators(config: dict):
    """Create training, validation, and test data generators with augmentation."""
    import tensorflow as tf

    dataset_path = config["dataset_path"]
    image_size = config["image_size"]
    batch_size = config["batch_size"]

    train_dir = os.path.join(dataset_path, "train")
    val_dir = os.path.join(dataset_path, "validation")
    test_dir = os.path.join(dataset_path, "test")

    # Verify directories exist
    for d, name in [(train_dir, "train"), (val_dir, "validation"), (test_dir, "test")]:
        if not os.path.isdir(d):
            print(f"[ERROR] {name} directory not found: {d}")
            sys.exit(1)

    # Training data with augmentation
    train_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        preprocessing_function=tf.keras.applications.efficientnet.preprocess_input,
        horizontal_flip=True,
        rotation_range=15,
        zoom_range=0.15,
        brightness_range=[0.8, 1.2],
        width_shift_range=0.1,
        height_shift_range=0.1,
        fill_mode="nearest",
    )

    # Validation/Test without augmentation — only preprocessing
    val_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        preprocessing_function=tf.keras.applications.efficientnet.preprocess_input,
    )

    train_gen = train_datagen.flow_from_directory(
        train_dir,
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=True,
    )

    val_gen = val_datagen.flow_from_directory(
        val_dir,
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
    )

    test_gen = val_datagen.flow_from_directory(
        test_dir,
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
    )

    return train_gen, val_gen, test_gen


def compute_class_weights(train_gen) -> dict:
    """Compute class weights to handle imbalanced datasets."""
    from sklearn.utils.class_weight import compute_class_weight

    labels = train_gen.classes
    class_names = list(train_gen.class_indices.keys())
    unique_classes = np.unique(labels)

    weights = compute_class_weight(
        class_weight="balanced",
        classes=unique_classes,
        y=labels,
    )

    class_weight_dict = {int(cls): float(w) for cls, w in zip(unique_classes, weights)}

    # Print imbalance report
    counter = Counter(labels)
    print("\n  --- CLASS DISTRIBUTION (TRAIN) ---")
    for idx, name in enumerate(class_names):
        count = counter.get(idx, 0)
        weight = class_weight_dict.get(idx, 1.0)
        print(f"  {name:<30} {count:>6} images  (weight: {weight:.3f})")

    return class_weight_dict


def build_model(num_classes: int, image_size: int = 224):
    """Build EfficientNetB0 model with transfer learning."""
    import tensorflow as tf

    # Load EfficientNetB0 with ImageNet weights, no top
    base_model = tf.keras.applications.EfficientNetB0(
        weights="imagenet",
        include_top=False,
        input_shape=(image_size, image_size, 3),
    )

    # Freeze base model for initial training
    base_model.trainable = False

    # Build classification head
    model = tf.keras.Sequential([
        base_model,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(256, activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])

    return model, base_model


def train(config: dict):
    """Full training pipeline."""
    import tensorflow as tf

    print("\n" + "=" * 60)
    print("  DERMA ASSIST — Model Training")
    print("=" * 60)
    print(f"  Image Size: {config['image_size']}")
    print(f"  Batch Size: {config['batch_size']}")
    print(f"  Frozen Epochs: {config['epochs_frozen']}")
    print(f"  Fine-tune Epochs: {config['epochs_finetune']}")
    print(f"  Dataset: {config['dataset_path']}")
    print("=" * 60)

    # Create data generators
    train_gen, val_gen, test_gen = create_data_generators(config)

    num_classes = train_gen.num_classes
    class_names = list(train_gen.class_indices.keys())
    print(f"\n  Detected {num_classes} classes: {', '.join(class_names)}")

    # Compute class weights
    class_weights = compute_class_weights(train_gen)

    # Build model
    model, base_model = build_model(num_classes, config["image_size"])

    # ─── Phase 1: Feature Extraction (frozen base) ───
    print("\n  PHASE 1: Feature Extraction (frozen base)")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config["learning_rate"]),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()

    # Callbacks
    os.makedirs(config["reports_dir"], exist_ok=True)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=5, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7
        ),
    ]

    history1 = model.fit(
        train_gen,
        epochs=config["epochs_frozen"],
        validation_data=val_gen,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    # ─── Phase 2: Fine-tuning (unfreeze top layers) ───
    print("\n  PHASE 2: Fine-tuning (unfreezing top layers)")
    base_model.trainable = True

    # Freeze the first 80% of layers, fine-tune the rest
    fine_tune_at = int(len(base_model.layers) * 0.8)
    for layer in base_model.layers[:fine_tune_at]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=config["learning_rate_finetune"]
        ),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    history2 = model.fit(
        train_gen,
        epochs=config["epochs_finetune"],
        validation_data=val_gen,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    # ─── Save Model ───
    model.save(config["model_path"])
    print(f"\n  [SAVED] Model saved to: {config['model_path']}")

    # ─── Save class_names.json ───
    class_data = {"classes": class_names}
    with open(config["class_names_path"], "w") as f:
        json.dump(class_data, f, indent=2)
    print(f"  [SAVED] class_names.json: {config['class_names_path']}")

    # ─── Save model_config.json ───
    model_config = {
        "image_size": config["image_size"],
        "num_classes": num_classes,
        "model": "EfficientNetB0",
        "classes": class_names,
    }
    with open(config["model_config_path"], "w") as f:
        json.dump(model_config, f, indent=2)
    print(f"  [SAVED] model_config.json: {config['model_config_path']}")

    # ─── Save Training History Plot ───
    _save_training_history(history1, history2, config["reports_dir"])

    # ─── Evaluate on Test Set ───
    print("\n  EVALUATING ON TEST SET...")
    evaluate(model, test_gen, class_names, config["reports_dir"])

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE!")
    print("=" * 60)


def evaluate(model, test_gen, class_names: list, reports_dir: str):
    """Evaluate model on test set and generate reports."""
    import tensorflow as tf
    from sklearn.metrics import classification_report, confusion_matrix
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Predict
    predictions = model.predict(test_gen, verbose=1)
    y_pred = np.argmax(predictions, axis=1)
    y_true = test_gen.classes

    # Classification report
    report = classification_report(
        y_true, y_pred, target_names=class_names, digits=4
    )
    print("\n  CLASSIFICATION REPORT:")
    print(report)

    report_path = os.path.join(reports_dir, "classification_report.txt")
    with open(report_path, "w") as f:
        f.write("DERMA ASSIST — Classification Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(report)
    print(f"  [SAVED] {report_path}")

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(max(10, len(class_names)), max(8, len(class_names) * 0.8)))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names,
    )
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    cm_path = os.path.join(reports_dir, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=150)
    plt.close()
    print(f"  [SAVED] {cm_path}")

    # Test accuracy
    test_loss, test_acc = model.evaluate(test_gen, verbose=0)
    print(f"\n  TEST ACCURACY: {test_acc:.4f}")
    print(f"  TEST LOSS: {test_loss:.4f}")


def _save_training_history(history1, history2, reports_dir: str):
    """Save training history plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Combine histories
    acc = history1.history["accuracy"] + history2.history["accuracy"]
    val_acc = history1.history["val_accuracy"] + history2.history["val_accuracy"]
    loss = history1.history["loss"] + history2.history["loss"]
    val_loss = history1.history["val_loss"] + history2.history["val_loss"]

    epochs = range(1, len(acc) + 1)
    phase1_end = len(history1.history["accuracy"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Accuracy plot
    ax1.plot(epochs, acc, "b-", label="Train Accuracy")
    ax1.plot(epochs, val_acc, "r-", label="Val Accuracy")
    ax1.axvline(x=phase1_end, color="gray", linestyle="--", alpha=0.5, label="Fine-tune Start")
    ax1.set_title("Model Accuracy")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Accuracy")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Loss plot
    ax2.plot(epochs, loss, "b-", label="Train Loss")
    ax2.plot(epochs, val_loss, "r-", label="Val Loss")
    ax2.axvline(x=phase1_end, color="gray", linestyle="--", alpha=0.5, label="Fine-tune Start")
    ax2.set_title("Model Loss")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Loss")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.suptitle("Derma Assist — Training History", fontsize=14)
    plt.tight_layout()

    history_path = os.path.join(reports_dir, "training_history.png")
    plt.savefig(history_path, dpi=150)
    plt.close()
    print(f"  [SAVED] {history_path}")


def main():
    """Main entry point for training."""
    parser = argparse.ArgumentParser(description="Train Derma Assist skin disease model")
    parser.add_argument("--config", type=str, default=None, help="Path to config.json")
    parser.add_argument("--dataset", type=str, default=None, help="Path to dataset directory")
    parser.add_argument("--epochs", type=int, default=None, help="Number of frozen epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size")
    parser.add_argument("--image-size", type=int, default=None, help="Image size")
    parser.add_argument("--lr", type=float, default=None, help="Learning rate")
    args = parser.parse_args()

    # Load config
    config_path = args.config or os.path.join(
        os.path.dirname(__file__), "config.json"
    )
    config = load_config(config_path)

    # Override with command-line args
    if args.dataset:
        config["dataset_path"] = args.dataset
    if args.epochs:
        config["epochs_frozen"] = args.epochs
    if args.batch_size:
        config["batch_size"] = args.batch_size
    if args.image_size:
        config["image_size"] = args.image_size
    if args.lr:
        config["learning_rate"] = args.lr

    train(config)


if __name__ == "__main__":
    main()
