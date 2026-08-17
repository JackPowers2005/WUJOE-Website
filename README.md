# WUJOE — Washington University Journal of Economics

The Journal's website. A static site: plain HTML, one stylesheet, one script, no
build step and no dependencies. Articles are published on a rolling basis rather
than in numbered issues.

## Running it locally

```bash
python3 serve.py
```

Then open http://localhost:8765/. **Do not open the `.html` files directly**
(`file://`) — Safari sandboxes a `file://` page to its own folder, so an article
inside `articles/` cannot reach `../styles.css` and every link back to the site
root fails with "Ignoring request to load this main resource because it is
outside the sandbox."

`serve.py` is not just a file server. It sends `Cache-Control: no-store` and
rewrites internal links to `page.html?b=<hash-of-that-file>` as it serves them.
Both exist because a plain `python3 -m http.server` sends only `Last-Modified`,
which lets Safari apply "heuristic freshness" and reuse a stored page without
asking the server whether it changed. That produced two genuinely confusing
bugs during development — a replaced headshot that kept rendering the previous
photo, and a withdrawn article that kept appearing on the homepage — because the
browser was showing HTML that no longer existed on disk. The link stamping is
what actually fixes it: no-store stops new stale copies being stored, but
nothing sent from a server can invalidate a response the browser has already
decided not to re-request, whereas a URL that changes with the file's contents
can never match a stale entry. Stamping happens in-flight only; the files on
disk keep clean `href`s.

## Layout

```
index.html          home
articles.html       article index, with client-side category filters
leadership.html     executive board and former members
articles/           one file per published review
  paper.js          shared article behaviour (table of contents, footnotes)
styles.css          all styling, design tokens at the top
script.js           navigation, scroll reveals, homepage hero animation
assets/
  team/             headshots, 840x1120
  topics/           article cover images
  *fig*.png         figures extracted from the authors' original PDFs
tools/              see below — not needed to run or edit the site
```

### Asset URLs carry a content hash

Image `src`s look like `assets/team/jack-powers.jpg?v=1ef89c5b`, and
`styles.css` / `script.js` are versioned the same way. The hash is the first 8
characters of the file's MD5. **When you replace an image or edit the CSS, update
the hash** (or drop the query entirely) — otherwise browsers that already hold
the old file will keep serving it. This is the same staleness problem described
above, and the reason the site is explicit about it.

## Editing

Design tokens — colours, fonts, spacing scale, easing curves — are CSS custom
properties at the top of `styles.css`. The navy is `--navy`, the gold accent is
`--gold`.

The homepage hero animation deserves a warning, because it broke twice in Safari
in ways that were hard to diagnose:

- **Every element's base style must be its finished, visible state.** The hidden
  state belongs only inside `@keyframes`, reached with
  `animation-fill-mode: backwards`. If an animation never runs, the element is
  simply already correct.
- **Never gate visibility on JavaScript**, and never animate `visibility` —
  Safari does not reliably run a zero-second `visibility` animation, so using one
  as a failsafe leaves text permanently invisible.
- The rising trend line is an SVG `stroke-dasharray` / `stroke-dashoffset` draw.
  Do not add `vector-effect="non-scaling-stroke"` to it: that makes the dash
  lengths screen-relative rather than path-relative, so the dash no longer
  covers the stretched path and the last stretch of the line never draws.
- The line's route is not eyeballed. It threads a measured gap between the
  volume strip's first and second items and a narrow corridor between the
  "Recent coverage" block and that strip. Regenerate it with
  `tools/gen_hero_line.py`, which documents each constraint, then paste the new
  `d` attribute into `index.html` and the new dash length into `styles.css`.
  Verify afterwards at several widths — the graphic is hidden below 960px, where
  the hero collapses to a single column and there is no free space for it.

## Temporarily withdrawn content

Search the project for `TEMPORARILY WITHDRAWN`. Blocks marked that way are
commented out rather than deleted — currently the school-funding review, which
is unlinked from the site while its authors revise it. The article itself is
intact at `articles/stl-school-funding.html` and still loads at its own URL; only
the links to it are commented out. To restore it, delete the comment wrappers
and re-enable the matching route in `tools/bundle.py`.

## tools/

Not required to run or edit the site.

- `bundle.py` — collapses the whole site into one self-contained HTML file, with
  every page as a hash route (`#/home`, `#/articles`, …) and the stylesheet,
  fonts and images inlined. Used to publish a single-file shareable copy. It
  strips `TEMPORARILY WITHDRAWN` blocks, so unpublished drafts do not travel
  inside the shared file. Run `fetch_fonts.py` first — it needs `fonts.css`.
- `fetch_fonts.py` — downloads the web fonts and writes `tools/fonts.css`
  (latin + greek subsets only). Needs network access. Not committed, since it is
  generated.
- `gen_hero_line.py` — regenerates the homepage trend-line path and its dash
  length.

## Deploying to GitHub Pages

The site lives at the repository root, so Pages can serve it as-is: repository
Settings → Pages → Source "Deploy from a branch", branch `main`, folder `/`.

One thing to fix after the domain is known: the link-preview tags in each page's
`<head>` (`og:image` and `twitter:image`) point at a relative path. LinkedIn,
Slack and iMessage need an absolute URL, so change them to
`https://<your-domain>/assets/og-cover.png`.

## Note on images

`assets/topics/hb3231.jpg` is an aerial rendering of the Cortex Innovation
Community. Confirm the Journal has permission to publish it — renderings like
this are normally owned by the developer or the design firm.

`assets/brookings-hall.jpg` and `assets/og-cover-square.png` are currently
unreferenced. `brookings-hall.jpg` was the original hero photograph, replaced by
the animated trend line. Both are kept here rather than deleted; remove them if
you do not want them.
