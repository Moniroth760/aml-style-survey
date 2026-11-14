"""
survey_app.py - "Love It or Leave It", the AML Studio fashion preference survey.

    python build_survey.py        # first: create the outfits and pictures
    streamlit run survey_app.py   # then: open the survey in your browser

Flow:  intro -> about you -> 5 style sections (Love it / Leave it)
       -> almost done (submit) -> thank you -> giveaway (optional email)

Where answers go (all in survey/):
  responses.csv     every Love it / Leave it, linked to a random participant ID
  participants.csv  the anonymous "About you" answers, same random ID
  giveaway.csv      giveaway emails ONLY - no participant ID, so emails can never
                    be linked to anyone's answers or end up in training data
"""

import csv
import random
import re
import time
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

from engine.responses import StorageError, save_giveaway_entry, save_participant, save_rows
from survey_style import theme_css, topbar_html

SURVEY_DIR = Path(__file__).parent / "survey"
OUTFITS_PER_STYLE = 6

# The five sections, in the order people see them. The first value is the
# style name used inside the program (items.csv, outfits.csv).
SECTIONS = [
    ("old money", "Classic / Old Money",
     "Think tailored fits, timeless silhouettes, and a touch of luxury."),
    ("casual", "Casual / Minimalist",
     "Think wardrobe staples, laid-back looks, and basics that are anything but basic."),
    ("streetwear", "Streetwear / Urban",
     "Think oversized fits, bold layers, and a little attitude."),
    ("soft", "Feminine / Romantic",
     "Think lace, ribbons, and looks straight out of a daydream."),
    ("alternative", "Alternative / Vintage",
     "Think dark palettes, vintage finds, and a touch of rebellion."),
]
SECTION_TITLES = {style: title for style, title, _ in SECTIONS}

AGE_OPTIONS = ["Under 18", "18–20", "21–23", "24–26", "27–30", "31 or above"]
GENDER_OPTIONS = ["Woman", "Man", "Non-binary", "Prefer to self-describe", "Prefer not to say"]
STYLE_MATCH_OPTIONS = ["Yes", "Somewhat", "Not really"]

# Text pages: a comfortable reading width (the card style is in survey_style.py)
BASE_CSS = """
<style>
[data-testid="stMainBlockContainer"], .block-container {padding: 1.5rem 1rem 1rem; max-width: 760px;}
</style>
"""

# Intro page: wider, so the big headline has room
INTRO_CSS = """
<style>
[data-testid="stMainBlockContainer"], .block-container {padding: 1.5rem 2rem 1rem; max-width: 1200px;}
</style>
"""

# Rating screens: use the whole screen with no scrolling.
#   Laptop / desktop: picture on the left (as tall as the screen), questions + buttons on the right.
#   Phone: picture on top (a bit under half the screen), questions + buttons underneath.
# "dvh" = a percentage of the screen's actual visible height, so it adapts to every device.
RATING_CSS = """
<style>
[data-testid="stMainBlockContainer"], .block-container {
    padding: 0.75rem 1.5rem 0.5rem; max-width: 100%;
}
[data-testid="stImage"] img {
    max-height: calc(100dvh - 4.5rem); width: auto !important; max-width: 100%;
    margin: 0 auto; display: block; object-fit: contain; border-radius: 12px;
}
h4 {margin: 0 !important; padding: 0 !important;}
[data-testid="InputInstructions"] {display: none;}   /* hides "Press Ctrl+Enter to apply" - tapping a button saves anyway */
[data-testid="stImageContainer"], [data-testid="stImage"] {display: flex; justify-content: center; width: 100%;}
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"], .block-container {padding: 0.5rem 0.75rem;}
    [data-testid="stImage"] img {max-height: 43dvh;}
    [data-testid="stTextArea"] textarea {height: 72px !important; min-height: 72px !important;}
    [data-testid="stHorizontalBlock"] {gap: 0.4rem !important;}
    [data-testid="stVerticalBlock"] {gap: 0.55rem !important;}
}
</style>
"""
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Choosing outfits for one person
# ---------------------------------------------------------------------------
@st.cache_data
def load_survey_outfits():
    path = SURVEY_DIR / "outfits.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sections_for(gender):
    """Which clothing sections to show: women's for women, men's for men, both otherwise."""
    return {"Woman": ["women"], "Man": ["men"]}.get(gender, ["men", "women"])


def build_queue(outfits, sections, rng):
    """For each style, in order: a random handful of outfits from the right sections."""
    queue = []
    for style, _, _ in SECTIONS:
        pool = [o for o in outfits if o["style"] == style and o["section"] in sections]
        rng.shuffle(pool)
        queue += pool[:OUTFITS_PER_STYLE]   # a style with no outfits (e.g. men's feminine) is skipped
    return queue


# ---------------------------------------------------------------------------
# Button actions (they run before the page redraws)
# ---------------------------------------------------------------------------
def go(screen):
    st.session_state.screen = screen


def start_rating(outfits):
    # Copy the "About you" answers somewhere safe: Streamlit forgets a widget's value
    # once that widget is no longer on the screen.
    gender = st.session_state.gender
    st.session_state.profile = {
        "age_range": st.session_state.age,
        "gender": gender,
        "gender_self_described": st.session_state.get("gender_self", "").strip()
        if gender == "Prefer to self-describe" else "",
    }
    st.session_state.participant_id = uuid.uuid4().hex[:10]
    st.session_state.queue = build_queue(outfits, sections_for(gender), random.Random())
    st.session_state.position = 0
    st.session_state.answers = []
    st.session_state.shown_at = time.time()
    go("rating")


def answer(choice):
    """choice is 'like' (Love it) or 'next' (Leave it) - the names the rest of the program uses."""
    position = st.session_state.position
    outfit = st.session_state.queue[position]
    style_match = st.session_state.get(f"match_{position}") or ""
    reason = (st.session_state.get(f"why_{position}") or "").strip()
    st.session_state.answers.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "participant_id": st.session_state.participant_id,
        "survey_id": outfit["survey_id"],
        "outfit_key": outfit["outfit_key"],
        "section": outfit["section"],
        "style": outfit["style"],
        "group": outfit["group"],
        "answer": choice,
        "style_match": style_match,
        "style_reason": reason if style_match == "Not really" else "",
        "position": st.session_state.position + 1,
        "seconds": round(time.time() - st.session_state.shown_at, 1),
    })
    st.session_state.position += 1
    st.session_state.shown_at = time.time()
    if st.session_state.position >= len(st.session_state.queue):
        go("almost_done")


def submit_responses():
    """Answers are only saved when the person presses Submit.
    If saving fails (e.g. no internet), they stay on this page and can try again."""
    try:
        save_rows("responses", st.session_state.answers)   # one request for all their answers
        save_participant({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "participant_id": st.session_state.participant_id,
            **st.session_state.profile,
            "outfits_shown": len(st.session_state.queue),
            "answers_given": len(st.session_state.answers),
        })
    except StorageError as e:
        print(f"Saving failed: {e}")          # shows in the server log
        st.session_state.save_failed = True
        return
    st.session_state.save_failed = False
    go("thanks")


def enter_giveaway():
    try:
        save_giveaway_entry(st.session_state.email.strip())
    except StorageError as e:
        print(f"Saving giveaway entry failed: {e}")
        st.session_state.save_failed = True
        return
    st.session_state.save_failed = False
    go("giveaway_done")


def restart():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def intro_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    st.markdown("""
<div class='hero'>
  <div class='tag'>A FASHION PREFERENCE EXPERIMENT</div>
  <h1>Love it<br>or leave it</h1>
  <div class='sub'>Five styles. Your taste. No wrong answers.</div>
  <p>We've put together a collection of looks across five different categories.
     Swipe through, pick your favourites, and show us what makes the cut!
     There's no right or wrong. We're interested in <b>YOUR</b> personal taste.</p>
  <div class='pills'><span>⏱ 5–10 minutes</span><span>✨ No right or wrong</span>
     <span>🎁 One lucky participant wins $25</span></div>
</div>
""", unsafe_allow_html=True)

    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        agreed = st.checkbox(
            "I agree that my anonymous answers can be used to research outfit preferences "
            "and improve AI outfit suggestions."
        )
        st.button("Let's go  ›", type="primary", width="stretch", disabled=not agreed,
                  on_click=go, args=("about",))


def about_screen(outfits):
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.header("About you")
        age = st.radio("Age", AGE_OPTIONS, index=None, key="age")
        if age == "Under 18":
            st.warning("Thanks for your interest! This survey is only open to people aged 18 and over.")
            return

        gender = st.radio("Gender", GENDER_OPTIONS, index=None, key="gender")
        if gender == "Prefer to self-describe":
            st.text_input("Please describe (optional)", key="gender_self")

        ready = age and gender
        st.button("Start", type="primary", width="stretch", disabled=not ready,
                  on_click=start_rating, args=(outfits,))


def rating_screen():
    queue, position = st.session_state.queue, st.session_state.position
    outfit = queue[position]
    style = outfit["style"]
    title, description = next((t, d) for s, t, d in SECTIONS if s == style)
    in_style = [o for o in queue if o["style"] == style]
    number_in_style = position - queue.index(in_style[0]) + 1

    st.markdown(RATING_CSS, unsafe_allow_html=True)
    picture, controls = st.columns([3, 2], gap="large", vertical_alignment="center")

    with picture:
        st.image(str(SURVEY_DIR / outfit["image"]), width="stretch")

    with controls:
        st.progress(position / len(queue), text=f"{position + 1} of {len(queue)}")
        st.markdown(f"#### {title}")
        st.caption(f"{description} · Look {number_in_style} of {len(in_style)}")

        # Q1: does the look match the style we labelled it as?
        match = st.segmented_control(
            f"Does this look feel **{title}** to you?",
            STYLE_MATCH_OPTIONS, key=f"match_{position}",
        )

        # Q2: Love it or Leave it (only after Q1 is answered)
        st.markdown("**Love it or Leave it?**")
        love_col, leave_col = st.columns(2, wrap=False)   # stay side by side, even on phones
        love_col.button("❤️ Love it", type="primary", width="stretch", disabled=match is None,
                        on_click=answer, args=("like",))
        leave_col.button("👋 Leave it", width="stretch", disabled=match is None,
                         on_click=answer, args=("next",))
        if match is None:
            st.caption("Answer the style question first 👆")

        # Only for "Not really": an optional box asking why
        if match == "Not really":
            st.text_area(
                f"Why doesn't this feel {title} to you? (optional)",
                key=f"why_{position}", height=110,
                placeholder="e.g. too casual, the colours feel more streetwear, the shoes don't fit the look…",
            )


def almost_done_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.header("You're almost done!")
        st.write(
            "After submitting your responses, you'll have the opportunity to enter our **$25 giveaway**. "
            "Simply click the giveaway link on the next screen to enter. Don't miss it!"
        )
        if st.session_state.get("save_failed"):
            st.error("Sorry, we couldn't save your answers just now. Please check your internet and press Submit again.")
        st.button("Submit", type="primary", width="stretch", on_click=submit_responses)


def thanks_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.title("Thank you! 🎉")
        st.write("Your responses have been submitted.")
        loved = [a["style"] for a in st.session_state.get("answers", []) if a["answer"] == "like"]
        if loved:
            style, _ = Counter(loved).most_common(1)[0]
            st.write(f"Your top style: **{SECTION_TITLES[style]}**")
        st.button("Enter the $25 giveaway →", type="primary", width="stretch", on_click=go, args=("giveaway",))


def giveaway_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.header("Enter the $25 giveaway!")
        st.write("Enter your email below for a chance to win $25! One winner will be randomly selected.")
        st.caption("Your email will only be used for the giveaway and will not be included in our AI training dataset.")

        email = st.text_input("Email address (optional)", key="email")
        agreed = st.checkbox("I agree to my email being used to administer the prize draw and contact me if I win.")

        valid = bool(EMAIL_PATTERN.match(email.strip()))
        if email.strip() and not valid:
            st.caption("Please check your email address.")
        if st.session_state.get("save_failed"):
            st.error("Sorry, we couldn't save your entry just now. Please try again.")
        st.button("Submit", type="primary", width="stretch", disabled=not (valid and agreed), on_click=enter_giveaway)
        st.button("No thanks, I'm done", type="tertiary", on_click=go, args=("finished",))


def giveaway_done_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.title("You're in! 🍀")
        st.write("Good luck! We'll contact you by email if you win.")
        st.button("Start again (new person)", on_click=restart)


def finished_screen():
    st.markdown(topbar_html(), unsafe_allow_html=True)
    with st.container(border=True):
        st.title("All done! 👋")
        st.write("Thanks again for taking part.")
        st.button("Start again (new person)", on_click=restart)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Love It or Leave It", page_icon="👗", layout="wide")

outfits = load_survey_outfits()
if not outfits:
    st.error("No survey outfits found. Run `python build_survey.py` first, then refresh this page.")
    st.stop()

screens = {
    "intro": intro_screen,
    "about": lambda: about_screen(outfits),
    "rating": rating_screen,
    "almost_done": almost_done_screen,
    "thanks": thanks_screen,
    "giveaway": giveaway_screen,
    "giveaway_done": giveaway_done_screen,
    "finished": finished_screen,
}
screen = st.session_state.get("screen", "intro")
# Every page uses the same beige background (see survey_style.py)
st.markdown(theme_css(), unsafe_allow_html=True)
if screen == "intro":
    st.markdown(INTRO_CSS, unsafe_allow_html=True)
elif screen != "rating":
    st.markdown(BASE_CSS, unsafe_allow_html=True)
screens[screen]()