"""
main.py - try the whole program in the terminal.

    python main.py

It walks through what a customer would do on the in-store screen:
pick an item -> pick a style -> see outfits -> get sizes -> send to checkout.
Press Enter at any question to accept the default shown in [brackets].
"""

from engine.catalogue import load_items, load_ratings, load_size_chart, load_stock, in_stock
from engine.orders import OutOfStock, place_order
from engine.outfits import generate_outfits
from engine.sizing import FIT_PREFERENCES, recommend_size


def ask(question, default, choices=None, cast=str):
    """Ask a question, accept Enter for the default, and re-ask on bad input."""
    while True:
        answer = input(f"{question} [{default}]: ").strip() or str(default)
        try:
            value = cast(answer)
        except ValueError:
            print("  Please enter a valid value.")
            continue
        if choices and value not in choices:
            print(f"  Please choose one of: {', '.join(map(str, choices))}")
            continue
        return value


def main():
    items, stock = load_items(), load_stock()
    chart, ratings = load_size_chart(), load_ratings()

    print("\n=== AML Studio store assistant ===\n")
    section = ask("Shopping in men or women?", "men", ["men", "women"])

    # 1. Pick an item
    print(f"\nItems for {section}:")
    choices = [i for i in items.values() if i.section in (section, "unisex") and in_stock(stock, i.item_id)]
    for slot in ["top", "full", "bottom", "outer", "shoes"]:
        for item in (i for i in choices if i.slot == slot):
            print(f"  {item.item_id}  {item.label():32} ${item.price:6.2f}   ({slot})")
    default_item = "T01" if section == "men" else "T21"
    chosen = items[ask("\nWhich item caught your eye? (ID)", default_item, [i.item_id for i in choices])]

    # 2. Pick a style
    style = ask(f"Style ({' / '.join(chosen.styles)})", chosen.styles[0], list(chosen.styles))

    # 3. Outfits
    outfits = generate_outfits(items, chosen.item_id, style, section=section, stock=stock, ratings=ratings)
    if not outfits:
        print("\nSorry, no complete outfits are in stock for that style right now.")
        return
    print(f"\nTop {len(outfits)} {style} outfits with the {chosen.label()}:\n")
    for n, outfit in enumerate(outfits, 1):
        print(f"  {n}. " + " + ".join(i.label() for i in outfit.items) + f"   (${outfit.total_price:.2f})")
        for reason in outfit.reasons[:3]:
            print(f"       - {reason}")
    pick = outfits[ask("\nWhich outfit?", 1, list(range(1, len(outfits) + 1)), int) - 1]

    # 4. Sizes
    height = ask("Your height in cm", 175, cast=float)
    weight = ask("Your weight in kg", 70, cast=float)
    fit = ask(f"How do you like clothes to fit? ({' / '.join(FIT_PREFERENCES)})", "regular", FIT_PREFERENCES)

    lines = []
    print()
    for item in pick.items:
        if item.slot == "shoes":
            sizes = [s for (iid, s) in stock if iid == item.item_id and stock[(iid, s)] > 0]
            if not sizes:
                print(f"  {item.label()}: sold out, skipped.")
                continue
            size = ask(f"  Shoe size for the {item.label()} (in stock: {', '.join(sizes)})", sizes[len(sizes) // 2], sizes)
        else:
            advice = recommend_size(item, height, weight, chart, stock, fit)
            size = advice.size if advice.in_stock else advice.alternative
            print(f"  {item.label()}: size {size or 'none available'}")
            for reason in advice.reasons:
                print(f"       - {reason}")
            if size is None:
                continue
        lines.append((item.item_id, size))

    # 5. Send to checkout
    if not lines:
        print("\nNothing left to order.")
        return
    total = sum(items[i].price for i, _ in lines)
    print(f"\nTotal: ${total:.2f}")
    if ask("Send this to the checkout counter? (y/n)", "n", ["y", "n"]) == "y":
        name = ask("First name for the order", "Guest")
        try:
            order = place_order(lines, items, stock, name)
            print(f"\nDone! Order {order['order_id']} is being prepared. "
                  f"Show this number at the checkout counter.")
        except OutOfStock as e:
            print(f"\nSorry: {e}")
    else:
        print("\nNo order placed. (Stock was not changed.)")


if __name__ == "__main__":
    main()
