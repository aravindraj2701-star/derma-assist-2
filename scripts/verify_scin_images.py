"""
Google SCIN Image Verification Tool
Loads 8-10 downloaded sample images directly using PIL and Matplotlib,
extracts real metadata (dimensions, byte size, format, mode),
and generates a verification grid to confirm genuine image files.
"""

import os
import glob
import shutil
import matplotlib.pyplot as plt
from PIL import Image

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
ARTIFACT_DIR = r"C:\Users\aravi\.gemini\antigravity-ide\brain\e5562b2e-36da-4b3e-84a3-fba022aca532"


def verify_downloaded_images(num_samples: int = 10):
    print("=" * 70)
    print("  GOOGLE SCIN DATASET — IMAGE VERIFICATION & INSPECTION")
    print("=" * 70)

    image_files = sorted(glob.glob(os.path.join(IMAGES_DIR, "*.png")) + glob.glob(os.path.join(IMAGES_DIR, "*.jpg")))

    if not image_files:
        raise FileNotFoundError(f"No images found in {IMAGES_DIR}. Please run scin_downloader.py first.")

    print(f"Total downloaded images in directory: {len(image_files)}")
    print(f"Selecting {min(num_samples, len(image_files))} sample images for visual & dimensional verification...\n")

    selected_files = image_files[:num_samples]
    verification_data = []

    for idx, filepath in enumerate(selected_files, 1):
        filename = os.path.basename(filepath)
        filesize_bytes = os.path.getsize(filepath)
        filesize_kb = filesize_bytes / 1024.0

        try:
            with Image.open(filepath) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode

                verification_data.append({
                    "index": idx,
                    "filename": filename,
                    "filepath": filepath,
                    "size_kb": filesize_kb,
                    "size_bytes": filesize_bytes,
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "is_valid": True
                })

                print(f"[{idx:02d}] File: {filename:<30} | Size: {filesize_kb:6.1f} KB | Dims: {width:4d}x{height:4d} | Format: {format_name} | Mode: {mode}")
        except Exception as e:
            print(f"[{idx:02d}] File: {filename:<30} | ERROR READING IMAGE: {e}")

    # Create visual grid
    rows, cols = 2, 5
    fig, axes = plt.subplots(rows, cols, figsize=(18, 8))
    fig.patch.set_facecolor('#ffffff')
    plt.subplots_adjust(wspace=0.25, hspace=0.35, top=0.90, bottom=0.08, left=0.04, right=0.96)

    fig.suptitle("Google SCIN Dataset — Downloaded Image Verification Grid", fontsize=16, fontweight='bold', color='#0f172a', y=0.97)

    for i, ax in enumerate(axes.flat):
        if i < len(verification_data):
            data = verification_data[i]
            img = Image.open(data["filepath"])
            ax.imshow(img)
            ax.axis('on')
            ax.set_xticks([])
            ax.set_yticks([])

            # Styled title and caption
            title_text = f"Sample #{data['index']}\n{data['filename'][:16]}..."
            caption = f"{data['width']}x{data['height']} px | {data['size_kb']:.1f} KB | {data['format']}"

            ax.set_title(title_text, fontsize=10, fontweight='600', color='#0f766e', pad=6)
            ax.set_xlabel(caption, fontsize=9, fontweight='500', color='#334155', labelpad=4)

            # Clean border around image
            for spine in ax.spines.values():
                spine.set_edgecolor('#0d9488')
                spine.set_linewidth(1.5)
        else:
            ax.axis('off')

    # Save visualization to dataset directory and artifact directory
    output_plot_path = os.path.join(DATASET_DIR, "scin_image_verification_grid.png")
    plt.savefig(output_plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    print(f"\n[OK] Verification grid saved to: {output_plot_path}")

    # Copy to artifacts directory
    if os.path.exists(ARTIFACT_DIR):
        artifact_dest = os.path.join(ARTIFACT_DIR, "scin_image_verification_grid.png")
        shutil.copy2(output_plot_path, artifact_dest)
        print(f"[OK] Verification grid copied to artifacts: {artifact_dest}")

    return verification_data


if __name__ == "__main__":
    verify_downloaded_images(num_samples=10)
