"""
make_square.py - turns non-square images in images/ into squares by adding
background-coloured space around them (nothing gets cropped off).

    python make_square.py

The original versions are kept in images/originals/, just in case.
"""

import shutil
from pathlib import Path

from PIL import Image

IMAGES_DIR = Path(__file__).parent / "images"
BACKUP_DIR = IMAGES_DIR / "originals"
FORMATS = {".png", ".jpg", ".jpeg", ".webp"}


def main():
    fixed = 0
    for path in sorted(IMAGES_DIR.iterdir()):
        if path.suffix.lower() not in FORMATS:
            continue
        with Image.open(path) as img:
            img = img.convert("RGB")
            w, h = img.size
            if w == h:
                continue
            # Use the colour of the top-left corner, so the added space matches the background
            background = img.getpixel((0, 0))
            side = max(w, h)
            square = Image.new("RGB", (side, side), background)
            square.paste(img, ((side - w) // 2, (side - h) // 2))

        BACKUP_DIR.mkdir(exist_ok=True)
        shutil.copy(path, BACKUP_DIR / path.name)
        square.save(path)
        print(f"{path.name}: {w}x{h} -> {side}x{side}")
        fixed += 1

    print(f"\nMade {fixed} image(s) square." if fixed else "All images were already square.")


if __name__ == "__main__":
    main()