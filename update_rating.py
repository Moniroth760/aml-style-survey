"""
update_ratings.py - turns survey answers into ratings the outfit engine uses.

    python update_ratings.py

Reads every Love it / Leave it answer (from Google Sheets if it's set up,
otherwise from survey/responses.csv) and writes:
  data/ratings.csv            likes and nexts per outfit - outfits people loved now score higher
  survey/style_agreement.csv  how much people agreed each outfit fits its style label
  survey/style_reasons.csv    every "Not really" reason, grouped by style
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

from engine.responses import (RATINGS_FILE, StorageError, load_responses, responses_to_ratings,
                              using_google_sheets, write_ratings)

AGREEMENT_FILE = Path(__file__).parent / "survey" / "style_agreement.csv"
REASONS_FILE = Path(__file__).parent / "survey" / "style_reasons.csv"
POINTS = {"Yes": 1.0, "Somewhat": 0.5, "Not really": 0.0}


def style_agreement(responses):
    """How much people agreed with each style label: 100% = everyone said Yes."""
    per_outfit = defaultdict(list)
    per_style = defaultdict(list)
    for r in responses:
        if r.get("style_match") in POINTS:
            per_outfit[(r["outfit_key"], r["style"])].append(r["style_match"])
            per_style[r["style"]].append(POINTS[r["style_match"]])

    with open(AGREEMENT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["outfit_key", "style", "yes", "somewhat", "not_really", "agreement"])
        for (key, style), answers in sorted(per_outfit.items()):
            counts = Counter(answers)
            score = sum(POINTS[a] for a in answers) / len(answers)
            writer.writerow([key, style, counts["Yes"], counts["Somewhat"], counts["Not really"], f"{score:.0%}"])

    print("\nDo people agree with our style labels? (100% = everyone said Yes)")
    for style, points in sorted(per_style.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        print(f"  {style:12} {sum(points) / len(points):4.0%}   ({len(points)} answers)")
    print(f"Per-outfit details saved to {AGREEMENT_FILE}")


def style_reasons(responses):
    """Every 'Not really' reason, so you can read why people disagreed with a style label."""
    rows = [r for r in responses if r.get("style_reason", "").strip()]
    with open(REASONS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["style", "outfit_key", "survey_id", "reason"])
        for r in sorted(rows, key=lambda r: (r["style"], r["outfit_key"])):
            writer.writerow([r["style"], r["outfit_key"], r["survey_id"], r["style_reason"].strip()])
    print(f"\n{len(rows)} 'Not really' reasons saved to {REASONS_FILE}")
    for r in rows[:5]:
        print(f"  [{r['style']}] {r['style_reason'].strip()}")


def main():
    source = "Google Sheets" if using_google_sheets() else "survey/responses.csv"
    try:
        responses = load_responses()
    except StorageError as e:
        print(f"Couldn't read the answers: {e}")
        return
    if not responses:
        print(f"No survey answers yet ({source} is empty).")
        return
    print(f"Reading answers from {source}...")
    counts = responses_to_ratings(responses)
    write_ratings(counts)
    people = len({r["participant_id"] for r in responses})
    likes = sum(1 for r in responses if r["answer"] == "like")
    print(f"{len(responses)} answers from {people} people ({likes / len(responses):.0%} likes)")
    print(f"Ratings for {len(counts)} outfits saved to {RATINGS_FILE}")
    style_agreement(responses)
    style_reasons(responses)


if __name__ == "__main__":
    main()