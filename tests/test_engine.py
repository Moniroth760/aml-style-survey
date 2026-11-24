"""
Tests for the engine. Run from the project folder:

    pip install pytest
    pytest

Each test checks one promise the program makes. If someone changes the code
later and breaks a promise, the matching test fails and tells them.
The tests use their own small, fixed catalogue in tests/fixtures/, so changing
the real catalogue in data/ never breaks them. Orders and stock are written to a
temporary folder, so tests never touch data/.
"""

import shutil
from pathlib import Path

import pytest

from engine.catalogue import load_items, load_ratings, load_size_chart, load_stock
from engine.orders import OutOfStock, get_order, place_order, update_status
from engine.outfits import all_outfits, generate_outfits, score_outfit
from engine.visuals import outfit_image
from engine.sizing import recommend_size


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def data():
    return (load_items(FIXTURES / "items.csv"), load_stock(FIXTURES / "stock.csv"),
            load_size_chart(FIXTURES / "size_chart.csv"), load_ratings(FIXTURES / "ratings.csv"))


# ---------- outfits ----------

def test_outfits_include_chosen_item_and_match_style(data):
    items, stock, _, ratings = data
    for outfit in generate_outfits(items, "T01", "old money", stock=stock, ratings=ratings):
        assert "T01" in [i.item_id for i in outfit.items]
        assert all("old money" in i.styles for i in outfit.items)


def test_outfits_are_complete(data):
    items, stock, _, _ = data
    for outfit in generate_outfits(items, "T08", "streetwear", section="men", stock=stock):
        slots = [i.slot for i in outfit.items]
        assert "shoes" in slots
        assert ("top" in slots and "bottom" in slots) or "full" in slots


def test_never_mixes_mens_and_womens_items(data):
    items, stock, _, _ = data
    for outfit in generate_outfits(items, "S02", "casual", section="women", stock=stock):
        assert "men" not in {i.section for i in outfit.items}


def test_two_patterns_are_rejected(data):
    items, *_ = data
    score, reason = score_outfit([items["T03"], items["B11"], items["S02"]], "old money")
    assert score is None and "pattern" in reason


def test_wrong_style_gives_clear_error(data):
    items, stock, _, _ = data
    with pytest.raises(ValueError, match="doesn't suit"):
        generate_outfits(items, "T07", "old money", stock=stock)


def test_liked_outfit_ranks_higher(data):
    items, *_ = data
    pieces = [items["T01"], items["B01"], items["S01"]]
    without, _ = score_outfit(pieces, "old money")
    with_likes, _ = score_outfit(pieces, "old money", {"T01+B01+S01": (18, 4)})
    assert with_likes > without


# ---------- sizing ----------

def test_size_matches_chart(data):
    items, stock, chart, _ = data
    assert recommend_size(items["T01"], 175, 70, chart, stock).size == "M"


def test_runs_small_goes_up_a_size(data):
    items, stock, chart, _ = data
    assert recommend_size(items["T03"], 175, 70, chart, stock).size == "L"


def test_sold_out_size_suggests_nearest(data):
    items, stock, chart, _ = data
    stock = dict(stock)
    stock[("T01", "M")] = 0
    advice = recommend_size(items["T01"], 175, 70, chart, stock)
    assert not advice.in_stock and advice.alternative in ("S", "L")


def test_shoes_are_refused(data):
    items, stock, chart, _ = data
    with pytest.raises(ValueError):
        recommend_size(items["S01"], 175, 70, chart, stock)


# ---------- orders ----------

@pytest.fixture
def temp_files(tmp_path):
    stock_path = tmp_path / "stock.csv"
    shutil.copy(FIXTURES / "stock.csv", stock_path)
    return tmp_path / "orders.csv", stock_path


def test_order_reserves_stock_and_numbers_orders(data, temp_files):
    items, _, _, _ = data
    orders_path, stock_path = temp_files
    stock = load_stock(stock_path)
    before = stock[("T01", "M")]
    first = place_order([("T01", "M")], items, stock, "Momo", orders_path, stock_path)
    second = place_order([("T01", "M")], items, stock, "Alex", orders_path, stock_path)
    assert (first["order_id"], second["order_id"]) == ("AML-0001", "AML-0002")
    assert load_stock(stock_path)[("T01", "M")] == before - 2


def test_out_of_stock_changes_nothing(data, temp_files):
    items, _, _, _ = data
    orders_path, stock_path = temp_files
    stock = load_stock(stock_path)
    stock[("B01", "M")] = 0
    before = dict(stock)
    with pytest.raises(OutOfStock):
        place_order([("T01", "M"), ("B01", "M")], items, stock, "Momo", orders_path, stock_path)
    assert stock == before                 # nothing half-reserved
    assert not orders_path.exists()


def test_cancel_puts_items_back(data, temp_files):
    items, _, _, _ = data
    orders_path, stock_path = temp_files
    stock = load_stock(stock_path)
    before = stock[("T01", "M")]
    order = place_order([("T01", "M")], items, stock, "Momo", orders_path, stock_path)
    update_status(order["order_id"], "cancelled", stock, orders_path, stock_path)
    assert load_stock(stock_path)[("T01", "M")] == before
    assert get_order(order["order_id"], orders_path)[0]["status"] == "cancelled"


# ---------- survey + pictures ----------

def test_all_outfits_are_valid_and_sorted(data):
    items, stock, _, _ = data
    outfits = all_outfits(items, "old money", "men", stock=stock)
    assert outfits
    assert all(a.score >= b.score for a, b in zip(outfits, outfits[1:]))
    assert all("women" not in {i.section for i in o.items} for o in outfits)


def test_outfit_picture_works_even_without_images(data, tmp_path):
    items, stock, _, _ = data
    outfit = generate_outfits(items, "T01", "old money", stock=stock)[0]
    picture = outfit_image(outfit, images_dir=tmp_path)   # empty folder: placeholders are used
    assert picture.size == (1000, 1000)
