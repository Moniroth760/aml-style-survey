"""
orders.py - "pick on screen, collect at checkout".

When a customer confirms an outfit:
  1. Check every piece is in stock in the chosen size.
  2. Reserve them (take them off the shelf count), so nobody else can take them.
  3. Create an order number, e.g. AML-0007, for staff to prepare.

Order statuses:  preparing -> ready -> collected
                 (or cancelled, which puts the items back in stock)
"""

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from .catalogue import DATA_DIR, save_stock

ORDERS_FILE = DATA_DIR / "orders.csv"
FIELDS = ["order_id", "created_at", "customer_name", "item_id", "item_name", "size", "price", "status"]
STATUSES = ["preparing", "ready", "collected", "cancelled"]


class OutOfStock(Exception):
    pass


def _read_rows(path):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _next_order_id(rows):
    numbers = [int(r["order_id"].split("-")[1]) for r in rows]
    return f"AML-{(max(numbers) + 1) if numbers else 1:04d}"


def place_order(lines, items, stock, customer_name,
                orders_path=ORDERS_FILE, stock_path=DATA_DIR / "stock.csv"):
    """lines = [(item_id, size), ...]. Returns {"order_id", "total", "lines"}.
    Raises OutOfStock (and changes nothing) if any piece isn't available."""
    if not lines:
        raise ValueError("An order needs at least one item.")

    # 1. Check everything first, so we never reserve half an outfit
    wanted = Counter(lines)
    problems = [
        f"{items[item_id].label()} in {size}"
        for (item_id, size), count in wanted.items()
        if stock.get((item_id, size), 0) < count
    ]
    if problems:
        raise OutOfStock("Not enough stock for: " + ", ".join(problems))

    # 2. Reserve
    for (item_id, size), count in wanted.items():
        stock[(item_id, size)] -= count
    save_stock(stock, stock_path)

    # 3. Record the order
    rows = _read_rows(orders_path)
    order_id = _next_order_id(rows)
    now = datetime.now().isoformat(timespec="seconds")
    for item_id, size in lines:
        rows.append({
            "order_id": order_id, "created_at": now, "customer_name": customer_name,
            "item_id": item_id, "item_name": items[item_id].label(), "size": size,
            "price": f"{items[item_id].price:.2f}", "status": "preparing",
        })
    _write_rows(rows, orders_path)

    total = sum(items[item_id].price for item_id, _ in lines)
    return {"order_id": order_id, "total": round(total, 2), "lines": lines}


def get_order(order_id, orders_path=ORDERS_FILE):
    return [r for r in _read_rows(orders_path) if r["order_id"] == order_id]


def update_status(order_id, status, stock=None, orders_path=ORDERS_FILE,
                  stock_path=DATA_DIR / "stock.csv"):
    """Change an order's status. Cancelling puts its items back in stock (pass `stock`)."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    rows = _read_rows(orders_path)
    mine = [r for r in rows if r["order_id"] == order_id]
    if not mine:
        raise ValueError(f"No order called {order_id}.")
    if mine[0]["status"] in ("collected", "cancelled"):
        raise ValueError(f"{order_id} is already {mine[0]['status']}.")

    if status == "cancelled":
        if stock is None:
            raise ValueError("Pass the stock so cancelled items can be put back.")
        for r in mine:
            stock[(r["item_id"], r["size"])] = stock.get((r["item_id"], r["size"]), 0) + 1
        save_stock(stock, stock_path)

    for r in mine:
        r["status"] = status
    _write_rows(rows, orders_path)
