"""
outfits.py - builds complete outfits around the item a customer picked.

How it works (like a stylist's checklist):
  1. Keep only items that suit the chosen style, are in stock, and are the
     right section (men's / women's / unisex).
  2. Try every combination of top + bottom + shoes (or dress + shoes),
     with and without a jacket.
  3. Throw out combinations that break a hard rule
     (e.g. two loud colours, or two patterns fighting each other).
  4. Score the rest: good colour pairs, a good fit for the style, and
     what real people said in the Like / Next survey.
  5. Return the best few, making sure they aren't near-copies of each other.

This is "Level 2" (rules). The ratings bonus in step 4 is the start of
"Level 3": the more survey data you collect, the more the scores reflect
what people actually like.
"""

from dataclasses import dataclass, field
from itertools import combinations, product

from .catalogue import in_stock

STYLES = ["old money", "streetwear", "soft", "casual", "alternative"]

# Colours that go with almost anything
NEUTRALS = {
    "white", "black", "grey", "navy", "beige", "cream", "brown",
    "khaki", "olive", "blue", "light blue",   # blue = denim
}

# Colour pairs that are known to look good together
GOOD_PAIRS = {frozenset(pair) for pair in [
    ("navy", "beige"), ("navy", "white"), ("navy", "cream"), ("navy", "grey"),
    ("navy", "light blue"), ("navy", "brown"), ("beige", "white"), ("beige", "brown"),
    ("cream", "brown"), ("white", "blue"), ("white", "black"), ("black", "grey"),
    ("black", "khaki"), ("black", "olive"), ("olive", "beige"), ("olive", "blue"),
    ("brown", "blue"), ("cream", "blue"), ("grey", "white"), ("khaki", "white"),
    ("light blue", "beige"), ("light blue", "grey"), ("pink", "blue"), ("pink", "white"),
    ("pink", "cream"), ("lavender", "white"), ("lavender", "cream"), ("red", "blue"),
    ("red", "black"), ("grey", "blue"), ("black", "blue"),
]}

# Order pieces are listed in (and the order used for outfit keys like "T01+B01+S01")
SLOT_ORDER = ["top", "full", "bottom", "outer", "shoes"]


@dataclass
class Outfit:
    items: tuple
    style: str
    score: float
    reasons: list = field(default_factory=list)

    @property
    def key(self):
        """A short ID for this exact combination, used to store survey ratings."""
        return "+".join(item.item_id for item in self.items)

    @property
    def total_price(self):
        return sum(item.price for item in self.items)


def _same_section(pieces):
    """Men's and women's items can't be mixed; unisex goes with either."""
    sections = {p.section for p in pieces if p.section != "unisex"}
    return len(sections) <= 1


def score_outfit(pieces, style, ratings=None):
    """Returns (score, reasons), or (None, reason) if the outfit breaks a hard rule."""
    accents = [p for p in pieces if p.colour not in NEUTRALS]
    if len(accents) > 1:
        return None, "two bright colours compete"
    patterned = [p for p in pieces if p.pattern != "plain"]
    if len(patterned) > 1:
        return None, "two patterns clash"
    if not _same_section(pieces):
        return None, "mixes men's and women's items"

    reasons = []

    # Colour harmony: average over every pair of pieces
    pair_points = []
    for a, b in combinations(pieces, 2):
        if frozenset((a.colour, b.colour)) in GOOD_PAIRS:
            pair_points.append(2)
            reasons.append(f"{a.colour} + {b.colour} is a classic pairing")
        elif a.colour == b.colour and a.colour != "black" and a.slot != "shoes" and b.slot != "shoes":
            pair_points.append(-1)
        else:
            pair_points.append(0)
    score = 3 * sum(pair_points) / len(pair_points)

    # Style bonus
    colours = {p.colour for p in pieces}
    if style == "old money" and not accents:
        score += 1
        reasons.append("all-neutral colours suit old money")
    elif style == "streetwear" and colours & {"black", "white", "grey"}:
        score += 1
        reasons.append("black/white/grey base suits streetwear")
    elif style == "soft" and colours & {"pink", "lavender", "cream"}:
        score += 1
        reasons.append("soft tones suit the soft style")
    elif style == "alternative" and (patterned or any(p.type == "Boots" for p in pieces)):
        score += 1
        reasons.append("pattern or boots give it an alternative edge")
    elif style == "casual" and ("blue" in colours or any(p.type == "Sneakers" for p in pieces)):
        score += 1
        reasons.append("denim or sneakers keep it casual")

    # What real people said (Like / Next survey)
    if ratings:
        key = "+".join(p.item_id for p in pieces)
        if key in ratings:
            likes, nexts = ratings[key]
            score += 3 * (likes - nexts) / (likes + nexts + 2)
            reasons.insert(0, f"{likes} of {likes + nexts} people liked this outfit")

    # Remove duplicate reasons, keep order
    reasons = list(dict.fromkeys(reasons))
    return round(score, 2), reasons


def _candidates(items, slot, style, section, stock):
    return [
        item for item in items.values()
        if item.slot == slot
        and style in item.styles
        and (section is None or item.section in (section, "unisex"))
        and (stock is None or in_stock(stock, item.item_id))
    ]


def _score_combinations(shapes, options, outer_options, style, ratings):
    """Try every combination for each outfit shape, keep the valid ones, best first."""
    scored = []
    for shape in shapes:
        slot_options = [options(slot) for slot in shape]
        if not all(slot_options):
            continue
        for base in product(*slot_options):
            for outer in outer_options:
                pieces = list(base) + ([outer] if outer else [])
                pieces.sort(key=lambda p: SLOT_ORDER.index(p.slot))
                score, reasons = score_outfit(pieces, style, ratings)
                if score is not None:
                    scored.append(Outfit(tuple(pieces), style, score, reasons))
    scored.sort(key=lambda o: o.score, reverse=True)
    return scored


def generate_outfits(items, chosen_id, style, section=None, stock=None,
                     ratings=None, how_many=3, include_outer=True):
    """Build the best `how_many` outfits that include the chosen item.

    section: "men" or "women". Needed when the chosen item is unisex;
             otherwise it's taken from the chosen item."""
    chosen = items[chosen_id]
    if style not in chosen.styles:
        raise ValueError(
            f"The {chosen.label()} doesn't suit '{style}'. It suits: {', '.join(chosen.styles)}."
        )
    if chosen.section != "unisex":
        section = chosen.section

    def options(slot):
        if slot == chosen.slot:
            return [chosen]
        return _candidates(items, slot, style, section, stock)

    # Which outfit shapes can include the chosen item?
    shapes = []
    if chosen.slot in ("top", "bottom", "outer", "shoes"):
        shapes.append(["top", "bottom", "shoes"])
    if chosen.slot in ("full", "outer", "shoes"):
        shapes.append(["full", "shoes"])

    if chosen.slot == "outer":
        outer_options = [chosen]
    else:
        outer_options = [None] + (options("outer") if include_outer else [])

    scored = _score_combinations(shapes, options, outer_options, style, ratings)
    return _pick_different(scored, how_many)


def all_outfits(items, style, section, stock=None, ratings=None, include_outer=True):
    """Every valid outfit for one style and section ("men" or "women"), best first.
    Used to build the survey, where no single item has been chosen."""
    def options(slot):
        return _candidates(items, slot, style, section, stock)

    outer_options = [None] + (options("outer") if include_outer else [])
    shapes = [["top", "bottom", "shoes"], ["full", "shoes"]]
    return _score_combinations(shapes, options, outer_options, style, ratings)


def _pick_different(outfits, how_many):
    """Pick the best outfits, skipping ones that only differ by a single piece."""
    chosen = []
    for min_changes in (2, 1):          # first try to be varied; relax if we must
        for outfit in outfits:
            if len(chosen) == how_many:
                return chosen
            if outfit in chosen:
                continue
            ids = {i.item_id for i in outfit.items}
            if all(len(ids - {i.item_id for i in c.items}) >= min_changes for c in chosen):
                chosen.append(outfit)
    return chosen
