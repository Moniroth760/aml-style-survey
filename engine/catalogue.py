"""
catalogue.py - loads the store's data from the CSV files in data/.

Think of this as the store's filing cabinet:
  items.csv      - every product: type, colour, pattern, which styles it suits
  stock.csv      - how many of each item, in each size, are in the store
  size_chart.csv - which size fits which height/weight range
  ratings.csv    - how many people liked / skipped each outfit (from the survey)

In a real Uniqlo setup, these would come from the store's own product system
instead of CSV files. Everything else in the program would stay the same.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Order matters: used to move up or down a size
CLOTHING_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    section: str        # men / women / unisex
    slot: str           # where it goes in an outfit: top / bottom / full (dress) / outer / shoes
    type: str           # Polo, Chinos, Sneakers...
    colour: str
    pattern: str        # plain / striped / checked / floral / graphic
    styles: tuple       # e.g. ("old money", "casual")
    fit_note: str       # true_to_size / runs_small / runs_large
    price: float

    def label(self):
        """A readable name, e.g. 'navy Piqué Polo Shirt' (no 'white White Sneakers')."""
        if self.colour.lower() in self.name.lower():
            return self.name
        return f"{self.colour} {self.name}"


def load_items(path=DATA_DIR / "items.csv"):
    """Returns {item_id: Item}."""
    items = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            items[row["item_id"]] = Item(
                item_id=row["item_id"],
                name=row["name"],
                section=row["section"],
                slot=row["slot"],
                type=row["type"],
                colour=row["colour"].lower(),
                pattern=row["pattern"].lower(),
                styles=tuple(s.strip() for s in row["styles"].split("|")),
                fit_note=row["fit_note"],
                price=float(row["price"]),
            )
    return items


def load_stock(path=DATA_DIR / "stock.csv"):
    """Returns {(item_id, size): quantity}, keeping the file's size order."""
    stock = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stock[(row["item_id"], row["size"])] = int(row["quantity"])
    return stock


def save_stock(stock, path=DATA_DIR / "stock.csv"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "size", "quantity"])
        for (item_id, size), quantity in stock.items():
            writer.writerow([item_id, size, quantity])


def sizes_for(stock, item_id):
    """Every size this item comes in (in stock or not), in order."""
    return [size for (iid, size) in stock if iid == item_id]


def in_stock(stock, item_id, size=None):
    """True if the item (in that size, or in any size) is in the store."""
    if size is not None:
        return stock.get((item_id, size), 0) > 0
    return any(qty > 0 for (iid, _), qty in stock.items() if iid == item_id)


def load_size_chart(path=DATA_DIR / "size_chart.csv"):
    """Returns {section: [rows in size order]}."""
    chart = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            chart.setdefault(row["section"], []).append({
                "size": row["size"],
                "height_max": float(row["height_max"]),
                "weight_max": float(row["weight_max"]),
            })
    return chart


def load_ratings(path=DATA_DIR / "ratings.csv"):
    """Returns {outfit_key: (likes, nexts)}. An outfit_key looks like 'T01+B01+S01'."""
    ratings = {}
    if not Path(path).exists():
        return ratings
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ratings[row["outfit_key"]] = (int(row["likes"]), int(row["nexts"]))
    return ratings
