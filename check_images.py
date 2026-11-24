"""
check_images.py - checks the images/ folder matches the catalogue.

    python check_images.py

It reports:
  - items in items.csv that have no image (so the app would show no picture)
  - images whose name doesn't match any item (usually a typo, e.g. 001.png instead of O01.png)
  - images that aren't square or are very small
"""

from pathlib import Path

from PIL import Image

from engine.catalogue import load_items

IMAGES_DIR = Path(__file__).parent / "images"
FORMATS = {".png", ".jpg", ".jpeg", ".webp"}


def main():
    items = load_items()
    files = {p.stem: p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in FORMATS}

    missing = [item_id for item_id in items if item_id not in files]
    unknown = [name for name in files if name not in items]

    print(f"Catalogue items: {len(items)}   Images found: {len(files)}\n")

    if missing:
        print("No image for:")
        for item_id in missing:
            print(f"  {item_id}  ({items[item_id].label()})")
        print()

    if unknown:
        print("Image names that don't match any item (check for typos like 0 vs O, or lowercase):")
        for name in unknown:
            print(f"  {files[name].name}")
        print()

    problems = []
    for item_id, path in sorted(files.items()):
        if item_id not in items:
            continue
        with Image.open(path) as img:
            w, h = img.size
        if abs(w - h) > 0.05 * max(w, h):
            problems.append(f"  {path.name}: not square ({w}x{h})")
        elif w < 512:
            problems.append(f"  {path.name}: quite small ({w}x{h}); it may look blurry")
    if problems:
        print("Size issues:")
        print("\n".join(problems))
        print()

    if not (missing or unknown or problems):
        print("All good! Every item has a matching, square image.")


if __name__ == "__main__":
    main()