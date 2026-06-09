# Pages Reference

The site has 7 active HTML pages at the project root. This document describes the anatomy of each.

Every page shares the same outer skeleton:

- `<head>` loads Google Fonts, then `CSS/style.css`, then a page-specific stylesheet (if any).
- `<body>` contains `<site-header></site-header>` (rendered by `JS/layout.js`), the page-specific `<main>`, and `<site-footer></site-footer>` (also from `JS/layout.js`).
- The script tags at the bottom of `<body>` always start with `JS/site-config.js`, then `JS/layout.js`, then page-specific data scripts (if any), and finally `JS/script.js`.

When this document refers to "mount points," it means empty containers in the static HTML that the data scripts fill at runtime.

---

## `index.html` — Home

| Aspect | Value |
|---|---|
| `<main>` class | none — the page uses several top-level `<section>` elements directly inside `<body>` |
| Page-specific CSS | `CSS/events-home.css` |
| Page-specific JS | `JS/team-data.js`, `JS/project-data.js`, `JS/events-data.js` |

Major sections, in order:

1. **Hero slider** — `#heroSlider` with social rail and `#featuredSlidesMount` (replaced by featured project slides from `Projects/Featured/`).
2. **Quick actions** strip — desktop-only; hidden under a small breakpoint.
3. **About / Mission** band.
4. **Radiant's Impact** stats panel — three count-up `metric-value` boxes (Core Researchers, Academic Disciplines, Active Grants).
5. **Meet the Team** — six carousel sections, one per People group. Each has a card-wrapper with an `id` like `leadershipContainer`, `facultyContainer`, `affiliationContainer`, `staffContainer`, `postDocContainer`, `gradContainer`. Filled by `team-data.js`.
6. **Events** — `#homeEventsSection` and `#homeEventsMount`. If no events, the section auto-removes itself.

Mount points populated by JS:

| Mount | Filled by |
|---|---|
| `#featuredSlidesMount` | `project-data.js` (homepage hero slides) |
| `#leadershipContainer` and the other five `*Container` IDs | `team-data.js` |
| `#homeEventsMount` | `events-data.js` |

---

## `Capabilities.html`

| Aspect | Value |
|---|---|
| `<main>` class | `cap-page` |
| Page-specific CSS | `CSS/capabilities.css` |
| Page-specific JS | none |

Major sections: hero (`.cap-hero`) and a lab grid of `.lab-cap-card` articles. This page is fully static — it doesn't load any JSON.

---

## `Contact_Us.html`

| Aspect | Value |
|---|---|
| `<main>` class | `contact-main` |
| Page-specific CSS | `CSS/contact.css` |
| Page-specific JS | none |

Major sections:

1. Hero (`.contact-hero-section`) with image background and gradient overlay.
2. `.contact-page` containing `.contact-grid` (the contact card and embedded map).
3. `.contact-connect` block with social/directory cards.

`script.js` wires the contact form's `submit` event to a placeholder `alert()` — replace with a real `fetch()` call when wiring a backend.

---

## `Donate.html`

| Aspect | Value |
|---|---|
| `<main>` class | `donate-page` |
| Page-specific CSS | `CSS/donate.css` |
| Page-specific JS | none |

Major sections:

1. `.donate-hero` — full-bleed hero with image (`Images/donation_banner.jpg`) and overlay.
2. `.donate-mission` — centered mission copy.
3. `.donate-impact` — four-card grid of "where your gift goes."
4. `.donate-cta` — closing call-to-action card.

---

## `Jobs.html`

| Aspect | Value |
|---|---|
| `<main>` class | `jobs-page` |
| Page-specific CSS | `CSS/jobs-page.css` |
| Page-specific JS | `JS/jobs-data.js` |

Major sections:

1. Hero — image-backed (`Images/News/visions-spaceflight-hardware.jpg`).
2. `.jobs-intro` — short intro paragraph.
3. `#jobsBoard` — empty mount filled by `jobs-data.js` from `Jobs/manifest.json`.
4. `.jobs-footnote-band` — closing note.

Sort order: newest `posted` date first.

---

## `Our_Team.html`

| Aspect | Value |
|---|---|
| `<main>` class | `team-page` |
| Page-specific CSS | `CSS/teams.css` |
| Page-specific JS | `JS/team-data.js` |

Major sections:

1. `.team-hero` — title and intro.
2. `.team-tools` — search input (`#teamSearch`) and group filter (`#teamSectionFilter`).
3. Six `.team-section` blocks, each with an empty `.person-stack` mount:

| Section `id` | Mount filled with |
|---|---|
| `#leadership` | leadership group from `People/manifest.json` |
| `#faculty` | core-researcher group |
| `#affiliation` | affiliate-researcher group |
| `#staff` | staff group |
| `#postdocs` | postdoc group |
| `#graduate` | graduate-student group |

4. `#teamFilterEmpty` — hidden by default; shown when search/filter has no matches.

Section behavior:

- All groups except `leadership` collapse to `TEAM_SECTION_PREVIEW_COUNT = 3` cards with a "Show all" button. Searching or filtering disables collapse so all matching cards are visible.
- Cards on the page have `id="<first-last>"` (e.g. `id="kristen-bennett"`) and optionally `data-person-legacy-keys` for older naming. The home page links to these with `Our_Team.html#first-last`.

---

## `Projects.html`

| Aspect | Value |
|---|---|
| `<main>` class | `projects-page` |
| Page-specific CSS | `CSS/projects.css` |
| Page-specific JS | `JS/project-data.js` |

Major sections:

1. `.projects-hero-section` — image-backed hero with gold "Projects & Impact" eyebrow. Hidden on screens narrower than 500px (the page uses `padding-top` instead at that size).
2. `#projectPageGrid` — empty mount filled with `.project-card` articles by `project-data.js` from the `page` array in `Projects/manifest.json`.

---

## Page-asset version reference (cache busters)

The current cache-buster value on each page is shown below at the time of writing. Bump these per [`CONVENTIONS.md`](CONVENTIONS.md#cache-busters) whenever you change `style.css`, `layout.js`, or any other shared file.

| Page | `style.css` | Page CSS | `layout.js` | Page JS |
|---|---|---|---|---|
| `index.html` | `2026-04-29-2` | `events-home.css?v=2026-04-27-2` | `2026-04-29-2` | `team-data.js?v=2026-04-28-6`, `project-data.js?v=2026-04-28-1`, `events-data.js?v=2026-04-27-1`, `script.js?v=2026-04-27-1` |
| `Capabilities.html` | `2026-04-29-2` | `capabilities.css?v=2026-04-10-1` | `2026-04-29-2` | `script.js?v=2026-04-10-1` |
| `Contact_Us.html` | `2026-04-29-2` | `contact.css?v=2026-04-28-3` | `2026-04-29-2` | `script.js?v=2026-04-10-1` |
| `Donate.html` | `2026-04-29-2` | `donate.css?v=2026-04-28-2` | `2026-04-29-2` | `script.js?v=2026-04-10-1` |
| `Jobs.html` | `2026-04-29-2` | `jobs-page.css?v=2026-04-28-2` | `2026-04-29-2` | `jobs-data.js?v=2026-04-10-1`, `script.js?v=2026-04-10-1` |
| `Our_Team.html` | `2026-04-29-2` | `teams.css?v=2026-04-28-5` | `2026-04-29-2` | `team-data.js?v=2026-04-28-6`, `script.js?v=2026-04-10-1` |
| `Projects.html` | `2026-04-29-2` | `projects.css?v=2026-04-28-3` | `2026-04-29-2` | `project-data.js?v=2026-04-28-1`, `script.js?v=2026-04-10-1` |

The values across pages are not always synchronized — when you bump a shared file (`style.css`, `layout.js`, or `script.js`), bump it on **every** HTML page that loads it.
