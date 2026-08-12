# The Stack

A personal book catalogue — reading list filtered by format, retailer, price, and rating.
Single static file, no build step. Data lives in the browser's `localStorage`.

## Run locally

Open `index.html` in a browser, or:

    python3 -m http.server 8000

## Deploy to GitHub Pages

Push this directory to a repo, then in **Settings → Pages** set:

- Source: *Deploy from a branch*
- Branch: `main`, folder: `/ (root)`

The site publishes at `https://<user>.github.io/<repo>/` within a minute or two.

## Notes

- React and Babel load from unpkg CDN and JSX compiles in the browser. Fine for a
  personal tool; if load time ever matters, port to Vite and build a bundle.
- Seeded prices and Goodreads ratings are rough estimates, meant to be edited.
- `.nojekyll` keeps Pages from running the file through Jekyll.
