"""
test_connection.py - checks the survey can reach your Google Sheets.

    python test_connection.py

It opens both spreadsheets, creates the tabs it needs (with header rows) if they
don't exist yet, and counts what's already saved. It doesn't add any answers.
"""

from engine.responses import TABLES, StorageError, load_table, using_google_sheets


def main():
    if not using_google_sheets():
        print("No Google Sheets settings found, so answers are saved to CSV files in survey/.")
        print("To use Google Sheets, run: python make_secrets.py path/to/your-key.json")
        return
    ok = True
    for table, (tab, _, _, _) in TABLES.items():
        try:
            rows = load_table(table)
            print(f"  OK  '{tab}' tab: {len(rows)} saved row(s)")
        except StorageError as e:
            ok = False
            print(f"  PROBLEM with '{tab}': {e}")
    if ok:
        print("\nAll good! The survey will save answers to Google Sheets.")
    else:
        print("\nMost common fixes:")
        print("  - Share the spreadsheet with the robot's email (in secrets.toml, client_email) as Editor")
        print("  - Turn on the Google Sheets API in your Google Cloud project")
        print("  - Check the spreadsheet addresses in .streamlit/secrets.toml")


if __name__ == "__main__":
    main()
