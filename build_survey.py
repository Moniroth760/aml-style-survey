"""
build_survey.py - creates the outfits to show in the Like / Next survey.

    python build_survey.py                 # 10 outfits per style, for men and women
    python build_survey.py --per-group 6   # fewer outfits

For each style (old money, streetwear, soft, casual, alternative), for men and women:
  - about 70% are the program's TOP PICKS (to check its best ideas really are good)
  - about 30% are EXPLORE picks: random lower-scoring outfits
    (to find out if the rules are wrong: maybe people love something it scored low)
  - no single item appears in more than 3 outfits per group, so people see variety

It saves:
  survey/images/<outfit_key>.png   one picture per outfit
  survey/outfits.csv               the list: which items, which style, which group
Each outfit's key (e.g. T01+B01+S01) is how its ratings are matched back later.
"""

import argparse
import csv
import random
import shutil
from collections import Counter
from pathlib import Path

from engine.catalogue import load_items, load_stock
from engine.outfits import STYLES, all_outfits
from engine.visuals import outfit_image

SURVEY_DIR = Path(__file__).parent / "survey"
MAX_USES_PER_ITEM = 3
MIN_POSSIBLE = 10   # skip a style if the catalogue can only make a handful of outfits for it


def pick_varied(outfits, how_many, used, max_uses=MAX_USES_PER_ITEM):
    """Take outfits in order, skipping any that would overuse an item."""
    picked = []
    for outfit in outfits:
        if len(picked) == how_many:
            break
        ids = [item.item_id for item in outfit.items]
        if all(used[i] < max_uses for i in ids):
            picked.append(outfit)
            used.update(ids)
    return picked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-group", type=int, default=10, help="outfits per style, per men/women")
    parser.add_argument("--seed", type=int, default=42, help="change it to get a different random mix")
    args = parser.parse_args()

    items, stock = load_items(), load_stock()
    rng = random.Random(args.seed)

    if SURVEY_DIR.exists():
        shutil.rmtree(SURVEY_DIR)
    (SURVEY_DIR / "images").mkdir(parents=True)

    rows = []
    for section in ["men", "women"]:
        for style in STYLES:
            outfits = all_outfits(items, style, section, stock=stock)
            if len(outfits) < MIN_POSSIBLE:
                print(f"{section:5} {style:12}: only {len(outfits)} possible outfits, skipped")
                continue

            n_top = round(args.per_group * 0.7)
            used = Counter()
            top_picks = pick_varied(outfits, n_top, used)

            rest = [o for o in outfits[len(outfits) // 5:] if o not in top_picks]  # skip the top 20%
            rng.shuffle(rest)
            explore = pick_varied(rest, args.per_group - len(top_picks), used)

            for group, picked in (("top_pick", top_picks), ("explore", explore)):
                for outfit in picked:
                    outfit_image(outfit).save(SURVEY_DIR / "images" / f"{outfit.key}.png")
                    rows.append({
                        "survey_id": f"{section[0].upper()}-{style.replace(' ', '_')}-{len(rows) + 1:03d}",
                        "outfit_key": outfit.key,
                        "section": section,
                        "style": style,
                        "group": group,
                        "score": outfit.score,
                        "items": " + ".join(item.label() for item in outfit.items),
                        "image": f"images/{outfit.key}.png",
                    })
            print(f"{section:5} {style:12}: {len(top_picks)} top picks + {len(explore)} explore "
                  f"(from {len(outfits)} possible outfits)")

    with open(SURVEY_DIR / "outfits.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} outfits to {SURVEY_DIR}/ (pictures in survey/images/)")


if __name__ == "__main__":
    main()
