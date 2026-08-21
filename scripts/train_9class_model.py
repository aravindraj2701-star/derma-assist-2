"""
train_9class_model.py
---------------------
Trains a 9-class skin disease image classification model using TensorFlow/Keras
with EfficientNetB0 transfer learning.

Steps:
1. Load dataset/train, dataset/validation, dataset/test (resized to 224x224).
2. Configure image augmentation layers for the training dataset.
3. Compute class weights to address imbalance.
4. Load pre-trained EfficientNetB0 backbone (frozen).
5. Add GlobalAveragePooling, Dropout, and Dense classification head.
6. Train head (Phase 1).
7. Unfreeze top layers and fine-tune with low learning rate (Phase 2).
8. Save best model to models/skin_disease_model.keras.
9. Plot accuracy/loss graphs.
10. Evaluate on test set, output classification report and confusion matrix.
"""

import os
import argparse
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

# Set random seeds for reproducibility
tf.keras.utils.set_random_seed(42)

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(MODELS_DIR, "reports")


def get_augment_model():
    """Build the image augmentation pipeline as a Keras sequential model."""
    augment_layers = [
        tf.keras.layers.RandomFlip("horizontal_and_vertical"),
        tf.keras.layers.RandomRotation(0.15),
        tf.keras.layers.RandomTranslation(height_factor=0.1, width_factor=0.1),
        tf.keras.layers.RandomZoom(0.15),
        tf.keras.layers.RandomContrast(0.1),
    ]
    return tf.keras.Sequential(augment_layers, name="augmentation")


def train_model(epochs_frozen=5, epochs_finetune=3, batch_size=32, lr=1e-3, fine_tune_lr=1e-5):
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print("  STARTING 9-CLASS SKIN DISEASE MODEL TRAINING")
    print("=" * 70)
    print(f"Dataset Path: {DATASET_DIR}")
    print(f"Batch Size: {batch_size}")
    print(f"Frozen Epochs: {epochs_frozen} | Fine-Tuning Epochs: {epochs_finetune}")
    print("-" * 70)

    # 1. Load Datasets
    print("[*] Loading train/validation/test splits...")
    train_ds = tf.keras.utils.image_dataset_from_directory(
        os.path.join(DATASET_DIR, "train"),
        image_size=(224, 224),
        batch_size=batch_size,
        label_mode="categorical",
        shuffle=True,
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        os.path.join(DATASET_DIR, "validation"),
        image_size=(224, 224),
        batch_size=batch_size,
        label_mode="categorical",
        shuffle=False,
    )

    test_ds = tf.keras.utils.image_dataset_from_directory(
        os.path.join(DATASET_DIR, "test"),
        image_size=(224, 224),
        batch_size=batch_size,
        label_mode="categorical",
        shuffle=False,
    )

    class_names = train_ds.class_names
    num_classes = len(class_names)
    print(f"\n[INFO] Detected classes: {class_names}")

    # 2. Apply Augmentations and Prefetching
    augment_model = get_augment_model()
    
    # We apply augmentation as a mapping function to the train dataset
    train_ds_augmented = train_ds.map(
        lambda x, y: (augment_model(x, training=True), y),
        num_parallel_calls=tf.data.AUTOTUNE
    )

    # Cache and prefetch for optimal training performance
    train_ds_augmented = train_ds_augmented.prefetch(buffer_size=tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(buffer_size=tf.data.AUTOTUNE)

    # 3. Handle Class Imbalance
    # Retrieve all label indices from the train dataset
    train_labels = []
    for _, labels in train_ds:
        train_labels.extend(np.argmax(labels.numpy(), axis=1))
    train_labels = np.array(train_labels)

    unique_classes = np.unique(train_labels)
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=unique_classes,
        y=train_labels
    )
    class_weight_dict = {int(c): float(w) for c, w in zip(unique_classes, class_weights)}

    print("\n[INFO] Class counts and weights in training set:")
    counts = np.bincount(train_labels)
    for idx, name in enumerate(class_names):
        print(f"  • {name:<30}: Count: {counts[idx]:>4} | Weight: {class_weight_dict[idx]:.4f}")

    # 4. Build Model with EfficientNetB0 Backbone
    print("\n[*] Initializing EfficientNetB0 backbone...")
    base_model = tf.keras.applications.EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(224, 224, 3)
    )
    # Freeze the base model
    base_model.trainable = False

    # Classification Head
    inputs = tf.keras.Input(shape=(224, 224, 3))
    # EfficientNetB0 expects inputs scaled [0, 255], which matches image_dataset_from_directory defaults.
    x = base_model(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(256, activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs, outputs)

    # Compile for initial head training
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    model.summary()

    # Callbacks
    checkpoint_path = os.path.join(MODELS_DIR, "skin_disease_model.keras")
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        verbose=1
    )
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True,
        verbose=1
    )

    # 5. Train Phase 1: Feature Extraction
    print("\n[*] Training classification head (Phase 1)...")
    history_frozen = model.fit(
        train_ds_augmented,
        validation_data=val_ds,
        epochs=epochs_frozen,
        class_weight=class_weight_dict,
        callbacks=[checkpoint, early_stopping]
    )

    # 6. Train Phase 2: Fine-Tuning
    if epochs_finetune > 0:
        print("\n[*] Unfreezing top layers of backbone for fine-tuning (Phase 2)...")
        base_model.trainable = True
        
        # Keep bottom 80% layers frozen, fine-tune the top 20%
        fine_tune_at = int(len(base_model.layers) * 0.8)
        for layer in base_model.layers[:fine_tune_at]:
            layer.trainable = False

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=fine_tune_lr),
            loss="categorical_crossentropy",
            metrics=["accuracy"]
        )

        history_finetune = model.fit(
            train_ds_augmented,
            validation_data=val_ds,
            epochs=epochs_finetune,
            class_weight=class_weight_dict,
            callbacks=[checkpoint, early_stopping]
        )
        
        # Combine histories
        acc = history_frozen.history["accuracy"] + history_finetune.history["accuracy"]
        val_acc = history_frozen.history["val_accuracy"] + history_finetune.history["val_accuracy"]
        loss = history_frozen.history["loss"] + history_finetune.history["loss"]
        val_loss = history_frozen.history["val_loss"] + history_finetune.history["val_loss"]
    else:
        acc = history_frozen.history["accuracy"]
        val_acc = history_frozen.history["val_accuracy"]
        loss = history_frozen.history["loss"]
        val_loss = history_frozen.history["val_loss"]

    # Save class names list to JSON in the models and model folders for compatibility
    import json
    class_data = {"classes": class_names}
    for folder in [MODELS_DIR, os.path.join(BASE_DIR, "model")]:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "class_names.json"), "w") as f:
            json.dump(class_data, f, indent=2)
        # Also copy config.json or model_config.json
        model_config = {"image_size": 224, "num_classes": num_classes, "classes": class_names, "model": "EfficientNetB0"}
        with open(os.path.join(folder, "model_config.json"), "w") as f:
            json.dump(model_config, f, indent=2)

    # 7. Save History Graphs
    print("\n[*] Saving accuracy and loss graphs...")
    epochs_range = range(1, len(acc) + 1)
    
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(epochs_range, acc, label="Training Accuracy")
    plt.plot(epochs_range, val_acc, label="Validation Accuracy")
    if epochs_finetune > 0:
        plt.axvline(x=epochs_frozen, color='r', linestyle='--', label='Fine-Tuning Start')
    plt.title("Model Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(epochs_range, loss, label="Training Loss")
    plt.plot(epochs_range, val_loss, label="Validation Loss")
    if epochs_finetune > 0:
        plt.axvline(x=epochs_frozen, color='r', linestyle='--', label='Fine-Tuning Start')
    plt.title("Model Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, "training_history.png"))
    plt.close()
    print(f"[SAVED] History plot saved to {os.path.join(REPORTS_DIR, 'training_history.png')}")

    # 8. Load best model and evaluate on test dataset
    print(f"\n[*] Evaluating best model from {checkpoint_path} on Test Dataset...")
    best_model = tf.keras.models.load_model(checkpoint_path)

    # Predict test set
    y_true = []
    y_pred = []
    y_conf = []
    for images, labels in test_ds:
        preds = best_model.predict(images, verbose=0)
        y_true.extend(np.argmax(labels.numpy(), axis=1))
        y_pred.extend(np.argmax(preds, axis=1))
        y_conf.extend(np.max(preds, axis=1))
    
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_conf = np.array(y_conf)

    # Loss and Accuracy
    test_loss, test_acc = best_model.evaluate(test_ds, verbose=0)
    print(f"\n  Test Loss: {test_loss:.4f}")
    print(f"  Test Accuracy: {test_acc:.4f}")

    # Classification Report
    report = classification_report(y_true, y_pred, target_names=class_names)
    print("\n  CLASSIFICATION REPORT:")
    print(report)

    # Disease symptoms and body locations lookup dictionary
    DISEASE_METADATA_LOOKUP = {
        "Melanoma": {
            "symptoms": "Asymmetrical, irregular borders, variegated color (brown/black/red/blue), diameter >6mm, evolving lesion.",
            "location": "Trunk, Back (men), Lower legs (women), Face"
        },
        "Basal Cell Carcinoma": {
            "symptoms": "Pearly translucent papule or nodule, rolled borders, telangiectasia, non-healing ulcer.",
            "location": "Face, Nose, Scalp, Neck, Shoulders"
        },
        "Squamous Cell Carcinoma": {
            "symptoms": "Hyperkeratotic, crusted, firm erythematous plaque or nodule, may ulcerate or bleed easily.",
            "location": "Lower lip, Ears, Face, Scalp, Dorsal hands"
        },
        "Actinic Keratosis": {
            "symptoms": "Rough, scaly, gritty erythematous patch, sandpapery texture on chronically sun-exposed skin.",
            "location": "Face, Scalp, Ears, Forearms, Hands"
        },
        "Nevus": {
            "symptoms": "Symmetrical, uniform brown/tan pigmented macule or papule with well-defined borders.",
            "location": "Trunk, Neck, Extremities, Face"
        },
        "Pigmented Benign Keratosis": {
            "symptoms": "Well-demarcated stuck-on pigmented plaque, verrucous or waxy surface, follicular plugging.",
            "location": "Trunk, Face, Back, Neck"
        },
        "Seborrheic Keratosis": {
            "symptoms": "Waxy, stuck-on hyperkeratotic plaque, brown to black, dull surface with horn pseudocysts.",
            "location": "Chest, Back, Shoulders, Face"
        },
        "Dermatofibroma": {
            "symptoms": "Firm, solitary, hyperpigmented button-like nodule that dimples downward with lateral pinching.",
            "location": "Lower extremities, Arms, Trunk"
        },
        "Vascular Lesion": {
            "symptoms": "Bright red or purple spot, smooth dome-shaped papule, small dilated blood vessels, blenches slightly",
            "location": "Trunk, Face, Neck, Limbs, Lips"
        }
    }

    # Print sample predictions with lookup
    sample_outputs = []
    sample_outputs.append("\n" + "=" * 80)
    sample_outputs.append("  SAMPLE TEST PREDICTIONS WITH POST-PREDICTION LOOKUP")
    sample_outputs.append("=" * 80)
    
    num_samples_to_show = min(10, len(y_pred))
    file_paths = test_ds.file_paths
    
    for i in range(num_samples_to_show):
        filename = os.path.basename(file_paths[i])
        true_lbl = class_names[y_true[i]]
        pred_lbl = class_names[y_pred[i]]
        conf = y_conf[i] * 100
        
        metadata = DISEASE_METADATA_LOOKUP.get(pred_lbl, {
            "symptoms": "No symptom mapping found.",
            "location": "No body location mapping found."
        })
        
        sample_outputs.append(f"Sample #{i+1}:")
        sample_outputs.append(f"  • Image File   : {filename}")
        sample_outputs.append(f"  • True Class   : {true_lbl}")
        sample_outputs.append(f"  • Predicted    : {pred_lbl} ({conf:.2f}% confidence)")
        sample_outputs.append(f"  • Symptoms     : {metadata['symptoms']}")
        sample_outputs.append(f"  • Body Location: {metadata['location']}")
        sample_outputs.append("-" * 80)

    sample_predictions_text = "\n".join(sample_outputs)
    print(sample_predictions_text)

    with open(os.path.join(REPORTS_DIR, "classification_report.txt"), "w") as f:
        f.write("9-CLASS SKIN DISEASE CLASSIFIER - CLASSIFICATION REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Test Accuracy: {test_acc:.4f}\n")
        f.write(f"Test Loss: {test_loss:.4f}\n\n")
        f.write(report)
        f.write("\n\n" + sample_predictions_text)
    print(f"[SAVED] Classification report and sample predictions saved to {os.path.join(REPORTS_DIR, 'classification_report.txt')}")

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=class_names, yticklabels=class_names)
    plt.title("Confusion Matrix")
    plt.ylabel("True Class")
    plt.xlabel("Predicted Class")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, "confusion_matrix.png"))
    plt.close()
    print(f"[SAVED] Confusion matrix plot saved to {os.path.join(REPORTS_DIR, 'confusion_matrix.png')}")

    print("\n" + "=" * 70)
    print("  TRAINING PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs-frozen", type=int, default=5)
    parser.add_argument("--epochs-finetune", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    train_model(
        epochs_frozen=args.epochs_frozen,
        epochs_finetune=args.epochs_finetune,
        batch_size=args.batch_size
    )
