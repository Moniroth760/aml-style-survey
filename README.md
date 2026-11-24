# AML Studio Store Assistant

An in-store shopping assistant: a customer picks one item on a screen, chooses a style, and gets complete outfits from what's in stock, a size recommendation for each piece, and an order number to collect everything at the checkout counter.

## Run it

```bash
python main.py      # try the full customer journey in the terminal
pip install pytest
pytest              # run the tests
```

Needs Python 3.10+ and Pillow (`pip install pillow`) for the pictures.

```bash
python check_images.py              # every item has a matching, square image?
python make_square.py               # fix images that aren't square
python preview.py T01 "old money"   # outfit pictures for one item, saved in previews/
python build_survey.py              # outfits + pictures for the Like / Next survey, saved in survey/
```

## How it's organised

| File | What it does |
|---|---|
| `engine/catalogue.py` | Loads the store's data (items, stock, size chart, ratings) |
| `engine/outfits.py` | Builds and scores outfits around the chosen item |
| `engine/sizing.py` | Recommends a size from height, weight and fit preference |
| `engine/orders.py` | Reserves stock and creates pick-up orders (AML-0001, …) |
| `engine/visuals.py` | Puts an outfit's item images together into one picture |
| `build_survey.py` | Picks outfits for the survey (70% top picks, 30% explore) and saves their pictures |
| `main.py` | The customer journey, in the terminal |
| `tests/` | Checks each promise the engine makes |
| `data/` | Sample catalogue (placeholder data, not real Uniqlo products) |

## How outfits are chosen

1. Keep items that suit the style, are in stock, and match the section (men's / women's / unisex).
2. Try every top + bottom + shoes (or dress + shoes), with and without a jacket.
3. Reject outfits with two bright colours or two patterns.
4. Score the rest: classic colour pairs, a style bonus, and survey ratings.
5. Return the best 3, making sure they're genuinely different.

## Notes

- `data/size_chart.csv` is a general placeholder, not Uniqlo's official chart.
- Placing an order really changes `data/stock.csv`. To reset, restore it from Git.
