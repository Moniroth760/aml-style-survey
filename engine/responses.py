"""
responses.py - saves survey answers, and turns them into ratings.

Where answers go:
  - GOOGLE SHEETS, if .streamlit/secrets.toml (or Streamlit Cloud's Secrets) has
    your robot's key and the two spreadsheet addresses. This is what the online
    survey uses, because Streamlit Community Cloud doesn't keep files.
  - CSV FILES in survey/, if there's no key. Handy for testing on your laptop.

Google Sheets layout (tabs are created automatically, with a header row):
  AML Survey Responses file:  "responses" tab, "participants" tab
  AML Giveaway Entries file:  "giveaway" tab   <- emails only, never linked to answers
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURVEY_DIR = ROOT / "survey"
RATINGS_FILE = ROOT / "data" / "ratings.csv"

FIELDS = [
    "timestamp", "participant_id", "survey_id", "outfit_key", "section", "style",
    "group", "answer", "style_match", "style_reason", "position", "seconds",
]
PARTICIPANT_FIELDS = ["timestamp", "participant_id", "age_range", "gender", "gender_self_described",
                      "outfits_shown", "answers_given"]
GIVEAWAY_FIELDS = ["timestamp", "email", "agreed_to_contact"]

# (tab name in Google Sheets, CSV file, columns, which secret holds the spreadsheet address)
TABLES = {
    "responses":    ("responses",    SURVEY_DIR / "responses.csv",    FIELDS,             "responses_sheet_url"),
    "participants": ("participants", SURVEY_DIR / "participants.csv", PARTICIPANT_FIELDS, "responses_sheet_url"),
    "giveaway":     ("giveaway",     SURVEY_DIR / "giveaway.csv",     GIVEAWAY_FIELDS,    "giveaway_sheet_url"),
}

# Kept for older scripts that refer to these names
RESPONSES_FILE = TABLES["responses"][1]
PARTICIPANTS_FILE = TABLES["participants"][1]
GIVEAWAY_FILE = TABLES["giveaway"][1]


class StorageError(Exception):
    """Saving or reading failed (e.g. no internet, or the sheet isn't shared with the robot)."""


# ---------------------------------------------------------------------------
# Which storage are we using?
# ---------------------------------------------------------------------------
def _secrets():
    """Reads .streamlit/secrets.toml (on your laptop) or the Secrets box (on Streamlit Cloud)."""
    try:
        import streamlit as st
        return {key: st.secrets[key] for key in st.secrets}
    except Exception:
        return {}


def using_google_sheets():
    s = _secrets()
    return bool(s.get("gcp_service_account") and s.get("responses_sheet_url") and s.get("giveaway_sheet_url"))


_worksheets = {}   # remembered between saves, so we don't reconnect every time


def _worksheet(table):
    """Open (and if needed create) the Google Sheets tab for a table, with its header row."""
    if table in _worksheets:
        return _worksheets[table]
    try:
        import gspread
        s = _secrets()
        client = gspread.service_account_from_dict(dict(s["gcp_service_account"]))
        tab, _, fields, url_key = TABLES[table]
        spreadsheet = client.open_by_url(s[url_key])
        try:
            worksheet = spreadsheet.worksheet(tab)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=tab, rows=1000, cols=len(fields))
        header = worksheet.row_values(1)
        if not header:
            worksheet.append_row(fields, value_input_option="RAW")
        elif header != fields:
            raise StorageError(
                f"The '{tab}' tab has different columns than expected. "
                f"Delete that tab in Google Sheets and it will be recreated."
            )
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Couldn't open the Google Sheet for {table}: {e}") from e
    _worksheets[table] = worksheet
    return worksheet


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------
def save_rows(table, rows):
    """Save several rows at once (a whole person's answers = one request to Google)."""
    if not rows:
        return
    _, csv_path, fields, _ = TABLES[table]
    values = [[str(row.get(field, "")) for field in fields] for row in rows]

    if using_google_sheets():
        try:
            _worksheet(table).append_rows(values, value_input_option="RAW")
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Couldn't save to Google Sheets: {e}") from e
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(fields)
        writer.writerows(values)


def save_response(row):
    save_rows("responses", [row])


def save_participant(row):
    """Anonymous 'About you' answers, linked to responses by a random participant_id."""
    save_rows("participants", [row])


def save_giveaway_entry(email):
    """Giveaway emails go to their own file with NO participant_id,
    so they can never be linked back to someone's answers or used for training."""
    save_rows("giveaway", [{"timestamp": datetime.now().isoformat(timespec="seconds"),
                            "email": email, "agreed_to_contact": "yes"}])


# ---------------------------------------------------------------------------
# Reading and clearing
# ---------------------------------------------------------------------------
def load_table(table):
    """All saved rows of a table, as a list of dicts (all values as text)."""
    _, csv_path, fields, _ = TABLES[table]
    if using_google_sheets():
        try:
            return _worksheet(table).get_all_records(numericise_ignore=["all"])
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Couldn't read from Google Sheets: {e}") from e
    if not csv_path.exists():
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_responses():
    return load_table("responses")


def clear_table(table):
    """Delete every saved row (keeps the header row in Google Sheets)."""
    _, csv_path, _, _ = TABLES[table]
    if using_google_sheets():
        _worksheet(table).batch_clear(["A2:ZZ"])
    elif csv_path.exists():
        csv_path.unlink()


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------
def responses_to_ratings(responses):
    """Count likes and nexts per outfit: {outfit_key: [likes, nexts]}."""
    counts = defaultdict(lambda: [0, 0])
    for r in responses:
        if r["answer"] == "like":
            counts[r["outfit_key"]][0] += 1
        elif r["answer"] == "next":
            counts[r["outfit_key"]][1] += 1
    return dict(counts)


def write_ratings(counts, path=RATINGS_FILE):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["outfit_key", "likes", "nexts"])
        for key, (likes, nexts) in sorted(counts.items()):
            writer.writerow([key, likes, nexts])