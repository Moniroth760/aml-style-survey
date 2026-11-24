"""
make_secrets.py - creates .streamlit/secrets.toml from your robot's JSON key,
so you don't have to copy the key across by hand.

    python make_secrets.py ~/Downloads/aml-survey-123456-abcdef.json

It asks for your two spreadsheet addresses, then writes .streamlit/secrets.toml.
That file is your password: it's listed in .gitignore so it never goes on GitHub.
Keep the JSON file somewhere safe OUTSIDE this project folder.
"""

import json
import sys
from pathlib import Path

SECRETS_FILE = Path(__file__).parent / ".streamlit" / "secrets.toml"
NEEDED = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri"]


def ask_url(question):
    while True:
        url = input(question).strip()
        if "docs.google.com/spreadsheets/d/" in url:
            return url.split("#")[0]
        print("  That doesn't look like a Google Sheets address. Copy it from your browser's address bar.")


def toml_string(value):
    return json.dumps(value)   # JSON strings are valid TOML strings (handles the key's line breaks)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    key = json.loads(Path(sys.argv[1]).expanduser().read_text())
    missing = [field for field in NEEDED if field not in key]
    if missing or key.get("type") != "service_account":
        sys.exit(f"This doesn't look like a service account key (missing: {', '.join(missing) or 'type'}).")

    print(f"Robot account: {key['client_email']}")
    print("Make sure BOTH spreadsheets are shared with that email as Editor.\n")
    responses_url = ask_url("Address of your AML Survey Responses spreadsheet: ")
    giveaway_url = ask_url("Address of your AML Giveaway Entries spreadsheet: ")
    if giveaway_url.split("/edit")[0] == responses_url.split("/edit")[0]:
        print("\nNote: you gave the same spreadsheet for both. It works, but emails are safer in a separate file.")

    lines = [
        "# Survey storage settings. THIS FILE IS A PASSWORD - never upload it or share it.",
        f"responses_sheet_url = {toml_string(responses_url)}",
        f"giveaway_sheet_url = {toml_string(giveaway_url)}",
        "",
        "[gcp_service_account]",
        *[f"{field} = {toml_string(value)}" for field, value in key.items()],
    ]
    SECRETS_FILE.parent.mkdir(exist_ok=True)
    if SECRETS_FILE.exists() and input(f"\n{SECRETS_FILE} already exists. Replace it? (yes/no) ").strip() != "yes":
        sys.exit("Cancelled.")
    SECRETS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved {SECRETS_FILE}. Next: python test_connection.py")


if __name__ == "__main__":
    main()
