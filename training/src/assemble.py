"""Build the training decks in two variants.

  training/*.html   standalone HTML for GitHub Pages (own <html>/<head>, theme
                    toggle, cross-deck links relative to each other)
  training/artifact/ body fragments for the Claude Artifact platform, which
                    supplies its own document skeleton and stamps the theme itself

Run:  python3 training/src/assemble.py
"""
import pathlib, json

ROOT = pathlib.Path(__file__).resolve().parents[1]     # training/
B = pathlib.Path(__file__).parent                       # training/src/

CSS = (B / "core.css").read_text()
TIMELINE = (B / "timeline.js").read_text()
SIM = (B / "sim.js").read_text()
JS = (B / "core.js").read_text() + "\n" + TIMELINE + "\n" + SIM
INDEX_CSS = (B / "index.css").read_text()

SITE = "https://barbosaricardo.github.io/book-shelf/training/"

DECKS = [
    dict(n=1, title="Getting the Point Online", date="8 Sep 2026", day="Monday 8 September 2026",
         topic="RTAC configuration &amp; protocols", dur="2h 04m", file="day1-rtac-protocols.html",
         body="deck1.html", js="deck1.js",
         desc="RTAC access, protecting a project through a firmware update, libraries and "
              "extensions, and DNP3, Modbus and C37.118 configured to carry correct values fast enough."),
    dict(n=2, title="Template to Plant", date="9 Sep 2026", day="Tuesday 9 September 2026",
         topic="Template conversion &amp; inverter integration", dur="1h 36m", file="day2-template-conversion.html",
         body="deck2.html", js="deck2.js",
         desc="Choosing the closest existing project, cloning it safely, and converting it to a "
              "different inverter model without leaving broken cross-references behind."),
    dict(n=3, title="From Setpoint to Inverter", date="10 Sep 2026", day="Wednesday 10 September 2026",
         topic="Grid Connect control logic &amp; DDR", dur="1h 32m", file="day3-grid-connect-ddr.html",
         body="deck3.html", js="deck3.js",
         desc="The Grid Connect control chain end to end, the timing budget behind it, PID and "
              "clamping behaviour, and DDR for proving the plant responded."),
]

ARTIFACT_URLS = {
    1: "https://claude.ai/code/artifact/65d204b8-174d-4bad-990c-3ea81fd14555",
    2: "https://claude.ai/code/artifact/b460dbde-c6da-402a-bc43-12db1d1b3a5b",
    3: "https://claude.ai/code/artifact/ffc7b1ac-d8dd-4d61-805f-dd31c73dcf38",
}
PAGE_URLS = {d["n"]: d["file"] for d in DECKS}

INNER = """<script>
document.body.setAttribute("data-deck","{n}");
document.body.setAttribute("data-pen","{n}");
window.DECK_URLS={urls};
</script>

<header class="rail rail--top">
  <span class="rail-id"><b>{title}</b><span>Day {n} &middot; {date}</span></span>
  <span class="spacer"></span>
  <nav class="pens" aria-label="Other decks in this series">
    <a class="pen-dot" data-p="1" {h1} {c1} title="Day 1 &mdash; RTAC Configuration &amp; Protocols">1</a>
    <a class="pen-dot" data-p="2" {h2} {c2} title="Day 2 &mdash; Template Conversion &amp; Inverter Integration">2</a>
    <a class="pen-dot" data-p="3" {h3} {c3} title="Day 3 &mdash; Grid Connect Control Logic &amp; DDR">3</a>
  </nav>
  <span class="count" id="count">01 / {slides}</span>
</header>
<div class="progress" id="prog"></div>

<main>
{body}
</main>

<footer class="rail rail--bot">
  <button class="rbtn" id="ovBtn" type="button">All slides <kbd>G</kbd></button>
  <button class="rbtn" id="notesBtn" type="button" aria-pressed="false">Notes <kbd>N</kbd></button>
  {extrabtns}
  <span class="spacer"></span>
  <span class="hint">&larr; &rarr; to move</span>
  <button class="rbtn" id="prev" type="button">&larr;</button>
  <button class="rbtn" id="next" type="button">&rarr;</button>
</footer>

<div class="ov" id="ov" hidden>
  <div class="ov-h">
    <h3>{title}</h3>
    <button class="rbtn" id="ovClose" type="button">Close <kbd>Esc</kbd></button>
  </div>
  <div class="ov-grid" id="ovGrid"></div>
</div>

<script>
{js}
</script>
<script>
{deckjs}
</script>
{extrajs}
"""

# --- Artifact variant: the platform supplies <html>, <head> and the theme stamp ---
FRAGMENT = """<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>
{css}
</style>
{inner}"""

# --- Pages variant: everything the Artifact wrapper would otherwise provide ---
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &mdash; controls training</title>
<meta name="description" content="{desc_plain}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc_plain}">
<meta property="og:type" content="article">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%23{fav}'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>
/* the document skeleton the Artifact host supplies; replicated for a plain web server */
:root{{color-scheme:dark}}
html,body{{margin:0}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
<style>
{css}
</style>
</head>
<body>
{inner}
</body>
</html>
"""

FONTS = ("https://fonts.googleapis.com/css2?family=Saira:wght@400;500;600;700"
         "&family=IBM+Plex+Mono:wght@400;500;600&display=swap")

THEME_BTN = ""   # the console commits to one visual world; there is nothing to toggle

THEME_JS = ""

FAVS = {1: "B87A12", 2: "0A76B0", 3: "AE2E6E"}


def inner_for(d, urls, extrabtns, extrajs):
    body = (B / d["body"]).read_text()
    deckjs = (B / d["js"]).read_text()
    slides = body.count('class="slide"')
    cur = {i: ('aria-current="page"' if i == d["n"] else "") for i in (1, 2, 3)}
    href = {}
    for i in (1, 2, 3):
        if i == d["n"]:
            href[i] = ""
        elif urls is PAGE_URLS:
            href[i] = 'href="%s"' % urls[i]
        else:
            href[i] = 'href="%s" target="_blank" rel="noopener"' % urls[i]
    return INNER.format(
        n=d["n"], title=d["title"], date=d["date"], body=body, js=JS, deckjs=deckjs,
        slides="%02d" % slides, urls=json.dumps({str(k): v for k, v in urls.items()}),
        c1=cur[1], c2=cur[2], c3=cur[3], h1=href[1], h2=href[2], h3=href[3],
        extrabtns=extrabtns, extrajs=extrajs), slides


INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Three Mornings on the RTAC</title>
<meta name="description" content="Three interactive training decks built from the 8-10 September 2026 morning sessions: RTAC configuration and protocols, project template conversion, and Grid Connect control logic.">
<meta property="og:title" content="Three Mornings on the RTAC">
<meta property="og:description" content="Three interactive training decks: RTAC configuration and protocols, project template conversion, and Grid Connect control logic.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%230A76B0'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>
:root{{color-scheme:dark}}
html,body{{margin:0}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
<style>
{css}
</style>
<style>
{indexcss}
</style>
</head>
<body>
<script>
document.body.setAttribute("data-pen","0");
window.DECK_LINKS={links};
</script>
{body}
<script>
{timeline}
</script>
{themejs}
</body>
</html>
"""


def build():
    (ROOT / "artifact").mkdir(exist_ok=True)
    for d in DECKS:
        inner, slides = inner_for(d, ARTIFACT_URLS, "", "")
        (ROOT / "artifact" / d["file"]).write_text(
            FRAGMENT.format(title=d["title"], css=CSS, inner=inner, fonts=FONTS))

        inner, slides = inner_for(d, PAGE_URLS, THEME_BTN, THEME_JS)
        (ROOT / d["file"]).write_text(
            PAGE.format(title=d["title"], css=CSS, inner=inner, fonts=FONTS,
                        desc_plain=d["desc"].replace('"', "&quot;"), fav=FAVS[d["n"]]))
        print("%-34s %2d slides" % (d["file"], slides))

    (ROOT / "index.html").write_text(INDEX.format(
        css=CSS, indexcss=INDEX_CSS, fonts=FONTS, timeline=TIMELINE, themejs=THEME_JS,
        body=(B / "index.body.html").read_text(),
        links=json.dumps({str(k): v for k, v in PAGE_URLS.items()})))
    print("%-34s landing page" % "index.html")


if __name__ == "__main__":
    build()
