# Controls training decks — 8–10 September 2026

Three interactive slide decks built from the three consecutive morning training
sessions. Each deck is a single self-contained HTML file: keyboard navigation
(← →, `G` for the slide index, `N` for speaker notes), per-device progress in
`localStorage`, and hands-on tools built from what the session actually covered.

| Deck | Session | File |
|---|---|---|
| Getting the Point Online | Mon 8 Sep, 07:05–09:10 — RTAC configuration & protocols | `day1-rtac-protocols.html` |
| Template to Plant | Tue 9 Sep, 07:00–08:36 — template conversion & inverter integration | `day2-template-conversion.html` |
| From Setpoint to Inverter | Wed 10 Sep, 07:04–08:36 — Grid Connect control logic & DDR | `day3-grid-connect-ddr.html` |

The decks cross-link: every slide carries the session clock time it came from,
the cover plots all three mornings on one time axis, and the second slide of
each deck links to the other two.

## Rebuilding

Source lives in `src/`. `core.css` and `core.js` are shared by all three decks
(navigation, slide index, checklists, quiz engine, SVG chart helper); each deck
has a `deckN.html` body and a `deckN.js` for its own interactions.

```
python3 src/assemble.py
```

writes the three self-contained files into this directory. Deck URLs for the
cross-links are in `URLS` at the top of `assemble.py`.

## On the content

The decks follow the sessions. Two things are marked apart from that:

- **"Outside the room"** panels carry sourced external material (DNP3 object
  groups, IEEE 2800 performance targets, meter and inverter response rates) and
  name the source.
- **Dashed "unconfirmed" chips** mark things the sessions themselves left open —
  night-time Q implementation, Grid Connect version compatibility — and the
  simulated PID/clamp curves, which show the shape of a behaviour rather than
  any particular plant's numbers.
