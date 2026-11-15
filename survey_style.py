"""
survey_style.py - the look of the survey: a warm beige background on every page,
big bold headings and pill-shaped buttons.

The background is made from YOUR item images: a wall of your catalogue,
darkened and tinted burgundy (the AML Studio colour), so there are no copyright worries.
To use a different background (e.g. a fashion photo you generated),
save it as survey_assets/hero.jpg and it will be used instead.

The picture is saved to static/hero.jpg, which Streamlit serves as a normal file
(see .streamlit/config.toml), so the browser downloads it once instead of on every tap.
"""

import random
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "images"
ASSETS_DIR = ROOT / "survey_assets"
CUSTOM_HERO = ASSETS_DIR / "hero.jpg"
STATIC_DIR = ROOT / "static"
SERVED_HERO = STATIC_DIR / "hero.jpg"

BURGUNDY = "#9E2B3A"
FONTS = "https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600;700&display=swap"


# ---------------------------------------------------------------------------
# Background picture
# ---------------------------------------------------------------------------
def _make_catalogue_wall(columns=6, rows=4, tile=340, seed=7):
    """A grid of your item photos, slightly tilted, darkened and softly blurred."""
    files = sorted(p for p in IMAGES_DIR.iterdir()
                   if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    if not files:
        return Image.new("RGB", (columns * tile, rows * tile), (20, 12, 14))
    rng = random.Random(seed)
    rng.shuffle(files)

    wall = Image.new("RGB", (columns * tile, rows * tile), (235, 232, 228))
    for i in range(columns * rows):
        with Image.open(files[i % len(files)]) as raw:
            piece = raw.convert("RGB").resize((tile - 24, tile - 24), Image.LANCZOS)
        piece = piece.rotate(rng.uniform(-6, 6), expand=False, fillcolor=(235, 232, 228))
        wall.paste(piece, ((i % columns) * tile + 12, (i // columns) * tile + 12))

    wall = wall.filter(ImageFilter.GaussianBlur(1.5))
    wall = ImageEnhance.Brightness(wall).enhance(0.55)
    tint = Image.new("RGB", wall.size, (90, 20, 32))          # burgundy wash
    return Image.blend(wall, tint, 0.35)


def prepare_background():
    """Make sure static/hero.jpg exists, and return the web address the page uses for it."""
    STATIC_DIR.mkdir(exist_ok=True)
    if CUSTOM_HERO.exists():
        with Image.open(CUSTOM_HERO) as img:
            img = img.convert("RGB")
    else:
        img = _make_catalogue_wall()
    img.thumbnail((1920, 1920))
    img.save(SERVED_HERO, quality=80)
    return "/app/static/hero.jpg"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
# The survey's background colour, used on every page
PAGE_COLOUR = "#E8D4B6"     # warm beige
INK = "#2B2627"             # main text colour (soft charcoal)
MUTED = "#6E5F4F"           # small/secondary text


def theme_css():
    """The survey's look: a warm beige background on every page, charcoal text,
    burgundy for the main buttons, and white cards for forms and outfit pictures."""
    return f"""
<style>
@import url('{FONTS}');

.stApp {{background: {PAGE_COLOUR}; color: {INK}; font-family: 'Inter', sans-serif;}}
header[data-testid="stHeader"] {{display: none;}}

/* Big bold headings, like a fashion campaign */
h1, h2, h3 {{font-family: 'Anton', 'Inter', sans-serif !important; letter-spacing: 0.02em;
             text-transform: uppercase; color: {INK} !important;}}
h4 {{color: {INK} !important;}}
p, li, label, .stMarkdown {{color: {INK};}}
[data-testid="stCaptionContainer"], .stCaption, small {{color: {MUTED} !important;}}

/* Pill buttons */
.stButton > button {{
    border-radius: 999px; padding: 0.75rem 1.8rem; font-weight: 600; letter-spacing: 0.03em;
    background: #FFFFFF; color: {INK}; border: 1px solid #CDB89A;
    box-shadow: 0 2px 8px rgba(43,38,39,0.08); transition: all 0.2s ease;
}}
.stButton > button:hover {{background: #FBF6EF; border-color: #A69B8D; color: {INK};}}
.stButton > button[kind="primary"] {{background: {BURGUNDY}; border-color: {BURGUNDY}; color: #FFFFFF;}}
.stButton > button[kind="primary"]:hover {{background: #B8384A; border-color: #B8384A; color: #FFFFFF;}}
.stButton > button[kind="primary"] p {{color: #FFFFFF !important;}}
.stButton > button:disabled {{opacity: 0.45;}}

/* Top bar: brand on the left, styles on the right */
.topbar {{display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;}}
.brand {{font-family: 'Anton', sans-serif; font-size: 1.5rem; letter-spacing: 0.08em; color: {INK};}}
.brand span {{color: {BURGUNDY};}}
.nav {{display: flex; gap: 1.6rem; font-size: 0.95rem; color: {MUTED};}}

/* Cover page headline */
.hero {{text-align: center; padding: 2vh 0 0.5rem;}}
.hero .tag {{display: inline-block; font-weight: 700; letter-spacing: 0.2em; font-size: 0.8rem; color: {INK};
            border: 1px solid {INK}; border-radius: 999px; padding: 0.35rem 1rem; margin-bottom: 0.8rem;}}
.hero h1 {{font-size: clamp(2.8rem, min(10vw, 13vh), 7.5rem); line-height: 0.95; margin: 0; color: {INK} !important;}}
.hero .sub {{font-family: 'Anton', sans-serif; font-size: clamp(1.1rem, 3vw, 1.9rem); letter-spacing: 0.06em;
            margin-top: 0.5rem; color: {BURGUNDY};}}
.hero p {{max-width: 640px; margin: 0.8rem auto 0; color: {INK}; font-size: 1.05rem;}}
.pills {{display: flex; justify-content: center; gap: 0.8rem; flex-wrap: wrap; margin: 1rem 0 0.6rem;}}
.pills span {{border: 1px solid #CDB89A; border-radius: 999px; padding: 0.4rem 1rem; font-size: 0.9rem;
             background: rgba(255,255,255,0.55); color: {INK};}}

/* White cards for the form pages */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: rgba(255,255,255,0.7); border: 1px solid #D9C6A8 !important; border-radius: 20px !important;
    box-shadow: 0 10px 40px rgba(43,38,39,0.08);
}}

/* Yes / Somewhat / Not really: always readable, whatever the browser or theme */
[data-testid="stButtonGroup"] button {{
    background: #FFFFFF !important; border: 1px solid #CDB89A !important; color: {INK} !important;
}}
[data-testid="stButtonGroup"] button p {{color: {INK} !important;}}
[data-testid="stButtonGroup"] button:hover {{background: #F3E7D4 !important; border-color: #A69B8D !important;}}
[data-testid="stButtonGroup"] button[aria-checked="true"] {{
    background: {BURGUNDY} !important; border-color: {BURGUNDY} !important; color: #FFFFFF !important;
}}
[data-testid="stButtonGroup"] button[aria-checked="true"] p {{color: #FFFFFF !important;}}

/* Text boxes */
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {{background: #FFFFFF; color: {INK};}}

/* Let long checkbox sentences wrap onto several lines instead of being cut off */
[data-testid="stCheckbox"] label, [data-testid="stCheckbox"] p, [data-testid="stCheckbox"] div {{
    white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}

/* Outfit picture as a clean white card */
[data-testid="stImage"] img {{border-radius: 18px; box-shadow: 0 12px 36px rgba(43,38,39,0.15);}}

@media (max-width: 640px) {{
    .nav {{display: none;}}
    .hero {{padding-top: 1vh;}}
    .hero .sub {{display: none;}}
}}
</style>
"""


def topbar_html():
    return ("<div class='topbar'><div class='brand'>AML <span>STUDIO</span></div>"
            "<div class='nav'><span>Old Money</span><span>Casual</span><span>Streetwear</span>"
            "<span>Feminine</span><span>Alternative</span></div></div>")