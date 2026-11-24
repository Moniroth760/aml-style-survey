"""
reset_survey_data.py - deletes all survey ANSWERS, e.g. your own test runs,
so the real survey starts from zero.

    python reset_survey_data.py

It clears:    responses, participants and giveaway entries
              (in Google Sheets if it's set up, otherwise the CSV files in survey/)
              plus survey/style_agreement.csv and survey/style_reasons.csv
It empties:   data/ratings.csv (so test likes stop affecting outfit scores)
It keeps:     the outfits and their pictures, your catalogue and your images
"""

from pathlib import Path

from engine.responses import TABLES, clear_table, using_google_sheets

ROOT = Path(__file__).parent
REPORT_FILES = [ROOT / "survey" / "style_agreement.csv", ROOT / "survey" / "style_reasons.csv"]
RATINGS_FILE = ROOT / "data" / "ratings.csv"


def main():
    where = "your Google Sheets" if using_google_sheets() else "the CSV files in survey/"
    print(f"This will permanently delete all saved answers in {where}:")
    for table in TABLES:
        print(f"  - {table}")
    print("and the result files (style agreement, style reasons, ratings).")
    if input("\nType yes to continue: ").strip().lower() != "yes":
        print("Cancelled. Nothing was deleted.")
        return

    for table in TABLES:
        clear_table(table)
    for path in REPORT_FILES:
        if path.exists():
            path.unlink()
    RATINGS_FILE.write_text("outfit_key,likes,nexts\n", encoding="utf-8")
    print("Done. The survey is ready for real participants.")


if __name__ == "__main__":
    main()
