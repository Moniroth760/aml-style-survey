"""
preview.py - see the outfits the program builds around one item, as pictures.

    python preview.py T01 "old money"
    python preview.py T17 streetwear men     # unisex items need men or women

Pictures are saved in previews/ - open them to see how the outfits look.
"""

import sys
from pathlib import Path

from engine.catalogue import load_items, load_ratings, load_stock
from engine.outfits import generate_outfits
from engine.visuals import outfit_image

PREVIEW_DIR = Path(__file__).parent / "previews"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    item_id, style = sys.argv[1], sys.argv[2]
    section = sys.argv[3] if len(sys.argv) > 3 else None

    items, stock, ratings = load_items(), load_stock(), load_ratings()
    if item_id not in items:
        print(f"No item called {item_id}.")
        return
    if items[item_id].section == "unisex" and section not in ("men", "women"):
        print(f"{item_id} is unisex - add men or women, e.g.: python preview.py {item_id} \"{style}\" men")
        return

    outfits = generate_outfits(items, item_id, style, section=section, stock=stock, ratings=ratings)
    PREVIEW_DIR.mkdir(exist_ok=True)
    for n, outfit in enumerate(outfits, 1):
        path = PREVIEW_DIR / f"{item_id}_{style.replace(' ', '_')}_{n}.png"
        outfit_image(outfit).save(path)
        print(f"{n}. " + " + ".join(i.label() for i in outfit.items))
        print(f"   saved {path}")


if __name__ == "__main__":
    main()
