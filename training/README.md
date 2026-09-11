# Controls training decks — 8–10 September 2026

Three interactive slide decks built from three consecutive morning training
sessions. Published at
**<https://barbosaricardo.github.io/book-shelf/training/>**.

| Deck | Session | Page |
|---|---|---|
| Getting the Point Online | Mon 8 Sep, 07:05–09:10 — RTAC configuration & protocols | [`day1-rtac-protocols.html`](day1-rtac-protocols.html) |
| Template to Plant | Tue 9 Sep, 07:00–08:36 — template conversion & inverter integration | [`day2-template-conversion.html`](day2-template-conversion.html) |
| From Setpoint to Inverter | Wed 10 Sep, 07:04–08:36 — Grid Connect control logic & DDR | [`day3-grid-connect-ddr.html`](day3-grid-connect-ddr.html) |

Each deck is a single self-contained HTML file — no build step, no assets to
fetch beyond the web fonts, works offline once loaded. Keyboard navigation
(← →, `G` for the slide index, `N` for speaker notes), a light/dark toggle, and
progress, checklists and quiz answers kept per-browser in `localStorage`.

The decks cross-link: every slide carries the session clock time it came from,
the landing page plots all three mornings on one time axis, and the second slide
of each deck maps how the three days depend on each other.

## Layout

```
training/
  index.html            landing page
  day*.html             the three decks, standalone — what GitHub Pages serves
  artifact/             the same decks as body fragments for Claude Artifacts,
                        which supply their own document skeleton
  src/                  source
    core.css core.js    shared by all three: navigation, slide index, checklists,
                        quiz engine, SVG chart helper
    timeline.js         the three-mornings time axis, shared with the landing page
    deckN.html deckN.js each deck's slides and its own interactions
    index.css index.body.html
    assemble.py         builds both variants
```

## Rebuilding

```
python3 training/src/assemble.py
```

Writes `index.html`, the three standalone decks, and `artifact/`. Cross-deck
links differ per variant — relative filenames on the site, Artifact URLs in the
Artifact build — and both sets live in `assemble.py`.

Deployment is the repo's existing `.github/workflows/pages.yml`, which uploads
the repo root on every push to `main`.

## On the content

The decks follow the sessions. Two things are marked apart from that:

- **"Outside the room"** panels carry sourced external material (DNP3 object
  groups, IEEE 2800 performance targets, meter and inverter response rates) and
  name the source.
- **Dashed "unconfirmed" chips** mark what the sessions left open — night-time Q
  implementation, Grid Connect version compatibility — and the simulated PID and
  clamp curves, which show the shape of a behaviour rather than any particular
  plant's numbers.
