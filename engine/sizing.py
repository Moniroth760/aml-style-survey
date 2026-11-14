"""
sizing.py - recommends a clothing size from height, weight and fit preference.

How it works:
  1. Look up which size your HEIGHT points to, and which size your WEIGHT points to.
  2. If they disagree, take the bigger one (a bit loose is better than too tight).
  3. Adjust for how you like clothes to fit (slim / regular / relaxed).
  4. Adjust for the item itself, if it's known to run small or large.
  5. Check it's in stock; if not, suggest the nearest size that is.

The size chart in data/size_chart.csv is a general placeholder, NOT Uniqlo's
real chart. Swap in the store's official chart before using this for real.
Shoes are not handled here: customers choose their shoe size directly.
"""

from dataclasses import dataclass, field

from .catalogue import CLOTHING_SIZES, in_stock, sizes_for

FIT_PREFERENCES = ["slim", "regular", "relaxed"]


@dataclass
class SizeAdvice:
    size: str
    in_stock: bool
    reasons: list = field(default_factory=list)
    alternative: str = None    # nearest in-stock size, if the recommended one is sold out


def _size_index(rows, value, key):
    """Index of the first size whose upper limit fits `value` (or the largest size)."""
    for i, row in enumerate(rows):
        if value <= row[key]:
            return i
    return len(rows) - 1


def recommend_size(item, height_cm, weight_kg, chart, stock, fit_preference="regular"):
    if item.slot == "shoes":
        raise ValueError("Shoes use shoe sizes. Ask the customer for their shoe size instead.")
    if fit_preference not in FIT_PREFERENCES:
        raise ValueError(f"fit_preference must be one of {FIT_PREFERENCES}")

    section = "women" if item.section == "women" else "men"   # unisex uses the men's chart
    rows = chart[section]
    names = [row["size"] for row in rows]
    reasons = []

    # 1 + 2: height vs weight
    h = _size_index(rows, height_cm, "height_max")
    w = _size_index(rows, weight_kg, "weight_max")
    if h == w:
        index = h
        reasons.append(f"Your height and weight both point to {names[h]}.")
    elif fit_preference == "slim":
        index = min(h, w)
        reasons.append(f"Height suggests {names[h]}, weight suggests {names[w]}; "
                       f"you prefer a slim fit, so we start from the smaller one.")
    else:
        index = max(h, w)
        reasons.append(f"Height suggests {names[h]}, weight suggests {names[w]}; "
                       f"we start from the larger one, since slightly loose is better than tight.")

    if height_cm > rows[-1]["height_max"] or weight_kg > rows[-1]["weight_max"]:
        reasons.append("You're above our size chart's range, so please try it on to be sure.")

    # 3: personal preference
    if fit_preference == "relaxed":
        index += 1
        reasons.append("One size up for the relaxed fit you prefer.")

    # 4: the item itself
    if item.fit_note == "runs_small":
        index += 1
        reasons.append("This item runs small, so we went one size up.")
    elif item.fit_note == "runs_large":
        index -= 1
        reasons.append("This item runs large, so we went one size down.")

    # Keep within the sizes this item actually comes in
    available = sizes_for(stock, item.item_id) or names
    chart_size = names[max(0, min(index, len(names) - 1))]
    if chart_size not in available:
        ordered = [s for s in CLOTHING_SIZES if s in available]
        target = CLOTHING_SIZES.index(chart_size)
        chart_size = min(ordered, key=lambda s: abs(CLOTHING_SIZES.index(s) - target))
        reasons.append(f"This item doesn't come in that size; {chart_size} is the closest.")

    advice = SizeAdvice(size=chart_size, in_stock=in_stock(stock, item.item_id, chart_size), reasons=reasons)

    # 5: stock check
    if not advice.in_stock:
        target = CLOTHING_SIZES.index(chart_size)
        options = [s for s in available if in_stock(stock, item.item_id, s)]
        if options:
            advice.alternative = min(options, key=lambda s: abs(CLOTHING_SIZES.index(s) - target))
            advice.reasons.append(f"{chart_size} is sold out here; the nearest size in stock is {advice.alternative}.")
        else:
            advice.reasons.append("This item is sold out in every size.")
    return advice
