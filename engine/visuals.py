"""
visuals.py - puts an outfit's item images together into one picture.

Layout (like a flat-lay on a table):

    top + bottom + shoes          dress + shoes
    +---------+---------+         +---------+---------+
    |   top   | (jacket)|         |         | (jacket)|
    +---------+  shoes  +         |  dress  +  shoes  +
    | bottom  |         |         |         |         |
    +---------+---------+         +---------+---------+

Each item photo is trimmed to the clothing itself (the empty white space
around it is cut off), so every piece fills its space evenly.
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
FORMATS = (".png", ".jpg", ".jpeg", ".webp")

# How much of its space each piece fills (shoes look huge if they fill the whole space)
SCALE = {"top": 0.92, "bottom": 0.92, "full": 0.95, "outer": 0.88, "shoes": 0.62}


def find_image(item_id, images_dir=IMAGES_DIR):
    for ext in FORMATS:
        path = Path(images_dir) / f"{item_id}{ext}"
        if path.exists():
            return path
    return None


def _cut_out(img, tolerance=14):
    """Trim the empty background, and make the background see-through,
    so items with a slightly off-white background still sit cleanly on the canvas."""
    img = img.convert("RGB")
    background = Image.new("RGB", img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, background).convert("L")
    box = diff.point(lambda p: 255 if p > tolerance else 0).getbbox()
    if box:
        img, diff = img.crop(box), diff.crop(box)
    mask = diff.point(lambda p: min(255, p * 12))   # near-background pixels become transparent
    img = img.convert("RGBA")
    img.putalpha(mask)
    return img


def _placeholder(item, size):
    """Grey box with the item's name, used if an image is missing."""
    img = Image.new("RGBA", size, (235, 235, 235, 255))
    ImageDraw.Draw(img).text((10, 10), f"{item.item_id}\n{item.label()}", fill=(90, 90, 90))
    return img


def _layout(slots, size, margin):
    """Where each piece goes, as (left, top, right, bottom) boxes inside the margin."""
    m, s = margin, size - margin
    mid = size // 2
    boxes = {}
    if "full" in slots:
        boxes["full"] = (m, m, mid, s)
    else:
        boxes["top"] = (m, m, mid, mid)
        boxes["bottom"] = (m, mid, mid, s)
    if "outer" in slots:
        boxes["outer"] = (mid, m, s, mid)
        boxes["shoes"] = (mid, mid, s, s)
    else:
        boxes["shoes"] = (mid, size // 4, s, size * 3 // 4)
    return boxes


def outfit_image(outfit, images_dir=IMAGES_DIR, size=1000, background=(255, 255, 255)):
    """Returns a square PIL image showing every piece of the outfit."""
    canvas = Image.new("RGB", (size, size), background)
    boxes = _layout([item.slot for item in outfit.items], size, margin=size // 25)

    for item in outfit.items:
        left, top, right, bottom = boxes[item.slot]
        box_w, box_h = right - left, bottom - top
        scale = SCALE.get(item.slot, 0.9)
        max_w, max_h = int(box_w * scale), int(box_h * scale)

        path = find_image(item.item_id, images_dir)
        if path:
            with Image.open(path) as raw:
                piece = _cut_out(raw)
            piece.thumbnail((max_w, max_h), Image.LANCZOS)
        else:
            piece = _placeholder(item, (max_w, max_h))

        x = left + (box_w - piece.width) // 2
        y = top + (box_h - piece.height) // 2
        canvas.paste(piece, (x, y), piece)
    return canvas
