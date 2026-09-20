# Comm Loss Root Cause Engine — sprint track

A 24-week, twelve-sprint plan that builds one system — a probabilistic
root-cause engine for SCADA comm loss — while covering the ground a graduate
probabilistic-modeling and reinforcement-learning sequence assumes you already
have. Published at
**<https://barbosaricardo.github.io/book-shelf/study/commloss-root-cause.html>**.

Four milestones: represent, localize, decide, act under ignorance. Each sprint
carries what to derive, what to build, what "done" means, a ten-working-day
plan, the artifacts that should exist at the end, and reading split into books
already on the shelf (`../index.html`) and papers to go find.

Single self-contained HTML file — no build step, nothing to fetch beyond the web
fonts. Checkbox progress and per-sprint notes are kept per-browser in
`localStorage`, with export/import to JSON so the track survives a new machine
or a cleared profile.

## Layout

```
study/
  commloss-root-cause.html   the track — what GitHub Pages serves
```

## On the content

The reading list is the point of the split: "on your shelf" entries are books
in the catalogue at the repo root, so a sprint can start without buying
anything; "go find these" entries name the paper or chapter that is genuinely
better than the textbook for that sprint's work — Rabiner 1989 for the HMM
sprint, Howard 1966 for value of information, Baird 1995 for the divergence.

Two sprints are load-bearing rather than optional: Sprint 7 produces the
value-of-information table a manager can act on, and Sprint 8's write-up derives
the correspondence between forward-backward and value iteration term by term,
which is the hinge between the probabilistic half of the track and the RL half.
