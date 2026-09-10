import sys, pathlib, json

URLS = {
    1: "https://claude.ai/code/artifact/65d204b8-174d-4bad-990c-3ea81fd14555",
    2: "https://claude.ai/code/artifact/b460dbde-c6da-402a-bc43-12db1d1b3a5b",
    3: "https://claude.ai/code/artifact/ffc7b1ac-d8dd-4d61-805f-dd31c73dcf38",
}
B = pathlib.Path(__file__).parent
OUT = pathlib.Path("/home/user/book-shelf/training")
OUT.mkdir(parents=True, exist_ok=True)

CSS = (B/"core.css").read_text()
JS  = (B/"core.js").read_text()

SHELL = """<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap">
<style>
{css}
</style>
<script>
document.body.setAttribute("data-deck","{n}");
document.body.setAttribute("data-pen","{n}");
window.DECK_URLS={urls};
</script>

<header class="rail rail--top">
  <span class="rail-id"><b>{railname}</b><span>Day {n} · {date}</span></span>
  <span class="spacer"></span>
  <nav class="pens" aria-label="Other decks in this series">
    <a class="pen-dot" data-p="1" {h1} {c1} title="Day 1 — RTAC Configuration &amp; Protocols">1</a>
    <a class="pen-dot" data-p="2" {h2} {c2} title="Day 2 — Template Conversion &amp; Inverter Integration">2</a>
    <a class="pen-dot" data-p="3" {h3} {c3} title="Day 3 — Grid Connect Control Logic &amp; DDR">3</a>
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
  <span class="spacer"></span>
  <span class="hint">← → to move</span>
  <button class="rbtn" id="prev" type="button">←</button>
  <button class="rbtn" id="next" type="button">→</button>
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
"""

def build(n, title, railname, date, bodyfile, jsfile, outfile):
    body = (B/bodyfile).read_text()
    deckjs = (B/jsfile).read_text() if (B/jsfile).exists() else ""
    slides = body.count('class="slide"')
    cur = {i: ('aria-current="page"' if i == n else '') for i in (1,2,3)}
    href = {i: ('' if i == n else 'href="%s" target="_blank" rel="noopener"' % URLS[i]) for i in (1,2,3)}
    html = SHELL.format(title=title, css=CSS, js=JS, deckjs=deckjs, body=body, n=n,
                        railname=railname, date=date, slides=f"{slides:02d}",
                        c1=cur[1], c2=cur[2], c3=cur[3],
                        h1=href[1], h2=href[2], h3=href[3],
                        urls=json.dumps({str(k): v for k, v in URLS.items()}))
    (OUT/outfile).write_text(html)
    print(outfile, slides, "slides,", len(html)//1024, "KB")

if __name__ == "__main__":
    build(1, "Getting the Point Online", "Getting the Point Online", "8 Sep 2026", "deck1.html", "deck1.js", "day1-rtac-protocols.html")
    build(2, "Template to Plant", "Template to Plant", "9 Sep 2026", "deck2.html", "deck2.js", "day2-template-conversion.html")
    build(3, "From Setpoint to Inverter", "From Setpoint to Inverter", "10 Sep 2026", "deck3.html", "deck3.js", "day3-grid-connect-ddr.html")
