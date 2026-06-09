# JS Guide

There are 7 active scripts in `JS/`. They use plain `<script>` tags (no ES modules), share state through a few `window.*` globals, and are orchestrated by `JS/script.js` after `DOMContentLoaded`.

## Loading order

Every page loads scripts in this order, ending with `script.js`:

```
JS/site-config.js       (sets window.RadiantSiteConfig)
JS/layout.js            (defines <site-header>, <site-footer>)
JS/team-data.js         (only on index.html and Our_Team.html)
JS/project-data.js      (only on index.html and Projects.html)
JS/events-data.js       (only on index.html)
JS/jobs-data.js         (only on Jobs.html)
JS/script.js            (always last)
```

`site-config.js` must come before any `*-data.js` because the data scripts read `RadiantSiteConfig.assetVersion` at module top.

## Global integration pattern

Each "data" script (except jobs-data) registers a `renderPageData()` entry point on `window`:

| Script | Global | Used by `script.js` |
|---|---|---|
| `team-data.js` | `window.TeamData = { renderPageData, personKeyFromName, legacyPersonKeysFromName }` | yes |
| `project-data.js` | `window.ProjectData = { renderPageData }` | yes |
| `events-data.js` | `window.EventsData = { renderPageData }` | yes |
| `jobs-data.js` | nothing on window | no — runs its own `DOMContentLoaded` |

`script.js` looks for whichever globals are present and `Promise.all`s their `renderPageData()` calls before continuing with carousel-arrow visibility, fade-ins, and team hash deep-link scrolling.

---

## `JS/site-config.js`

A single frozen object that lives on `window`:

```js
window.RadiantSiteConfig = Object.freeze({
  assetVersion: "2026-04-27-1"
});
```

`assetVersion` is the cache-buster query string appended to every JSON fetch by the data scripts. Bump it whenever you ship significant data changes that need to invalidate the browser cache. Values look like `YYYY-MM-DD-N`.

---

## `JS/layout.js`

Defines two custom elements:

### `<site-header>`

Injects the sticky header containing the NAU logo, the brand title ("NAU RADIANT CENTER FOR REMOTE SENSING"), the hamburger toggle, and the navigation menu. The menu is hardcoded in this file, so to add or rename a nav link, edit the template string here and bump the `layout.js` cache buster on every HTML page.

Active link highlighting (`highlightActiveLink`): compares `window.location.pathname`'s last segment to each link's `data-path` and adds the `.active` class.

Mobile menu (`initMobileMenu`):

- `matchMedia('(max-width: 1170px)')` decides whether the layout is "mobile."
- Toggle button click flips the `#site-nav-menu` between hidden and visible (`.open` class + `aria-expanded`).
- Document-level handlers close the menu on outside `pointerdown`, on `Escape`, on a nav-link click, and when the media query changes.

### `<site-footer>`

Injects the multi-column footer (Explore links, social icons, copyright bar). Edit the template string in `layout.js` to change footer content.

---

## `JS/script.js`

The "app" script. Wraps everything in a single `DOMContentLoaded` listener and runs the following in order.

1. **Async data render** (lines roughly 50-61): `Promise.all` over whichever of `TeamData.renderPageData`, `ProjectData.renderPageData`, `EventsData.renderPageData` are present. This means follow-up logic (e.g. carousel arrow visibility) only runs after data has populated the DOM.

2. **Team-page deep-link scrolling** (only when `document.querySelector('.team-page')`):
   - Walks every `.person-feature` card, sets `id` and `data-person-key` (and optional `data-person-legacy-keys`) so URL hashes resolve.
   - `resolveTeamHashTarget`: matches by element `id`, then `data-person-key`, then by any of the pipe-separated legacy keys.
   - `scrollTargetToTop`: scrolls so the target sits below the sticky header height plus 16 px of breathing room.
   - `scrollToTeamHashTarget`: triggers on `hashchange`, `load`, and the initial run; uses double `requestAnimationFrame`, a 180 ms retry, and a wait-for-images pass to defeat layout shift. Sets `history.scrollRestoration = 'manual'`.

3. **Hero slider** (`#heroSlider`): prev/next buttons, auto-advance, dots built from `.slide` count.

4. **Horizontal card carousels** (`.nav-btn` with `data-target="<containerId>"`): scroll by one card width using `getCarouselStep`. `ResizeObserver` plus a `resize` listener hide arrows when there's no overflow.

5. **Education strip carousel**: fixed 360-px scroll steps.

6. **Fade-in observer**: `IntersectionObserver` on `.card`, `.featured-story`, and similar; adds `.fade-in` when 10% visible. A 1.5 s opacity fallback ensures content shows even without IO support.

7. **Stats counter**: `IntersectionObserver` on `.metric-value` triggers count-up animation when half-visible. Preserves prefix (`$`) and suffix (`%`, `+`).

8. **Contact form** (`#contactForm`): submit listener calls `preventDefault()`, `alert("Thanks!")`, then `form.reset()`. Replace the alert with a real `fetch()` call when wiring a backend.

---

## `JS/team-data.js`

The largest data script. An IIFE that exposes `window.TeamData = { legacyPersonKeysFromName, personKeyFromName, renderPageData }`.

### Constants worth knowing

| Constant | Value | Meaning |
|---|---|---|
| `MANIFEST_PATH` | `"People/manifest.json"` | Source of truth |
| `RANDOMIZED_SECTIONS` | `{faculty, affiliation, postdocs, graduate}` | Homepage shuffles these; team page sorts them by last name |
| `TEAM_SECTION_PREVIEW_COUNT` | `3` | Number of cards shown when a team section is collapsed |
| `SECTIONS_WITHOUT_COLLAPSE` | `{leadership}` | Sections that never collapse |
| `LOW_RES_ENTER_SCALE` / `LOW_RES_EXIT_SCALE` | `1.08` / `1.18` | Hysteresis for the `.is-low-res` class on overscaled headshots |
| `TEAM_BIO_MIN_HEIGHT` | px | Minimum bio height before the "Show more" toggle appears |
| `TEAM_BIO_MOBILE_PREVIEW_LINES` | int | Lines of bio shown when collapsed on mobile |

### Public functions

- `personKeyFromName(name)` — produces the canonical `first-last` slug used as a card `id` and URL hash.
- `legacyPersonKeysFromName(name)` — produces older slug variants for backward compatibility (used as `data-person-legacy-keys` so old links still resolve).
- `renderPageData()` — top-level entry point. Detects whether it's running on the homepage (looks for `#leadershipContainer`) or the team page (looks for `main.team-page`) and dispatches accordingly.

### Rendering pipeline

1. `loadManifest()` fetches `People/manifest.json` once and caches the result.
2. `loadSectionPeople(key)` reads the array under `manifest[key]` and `Promise.all`s `fetchJson()` for each entry. `fetchJson` caches by versioned URL.
3. **Homepage path**: `renderHomepageTeam` shuffles the four randomized sections, then fills each `*Container` with `renderHomePerson` HTML.
4. **Team page path**: `renderTeamPage` sorts the four randomized sections by last name, then fills each `.person-stack` with `renderTeamProfile` HTML.
5. After render: `initTeamFilters` (search + group filter), `applySectionCollapse` (Show all toggles), `markLowResolutionHeadshots`, `initTeamBioToggles`, `expandSectionForHash` (deep linking).

### Collapse/expand behavior

`applySectionCollapse` decides per-section whether to show the "Show all" footer. It's disabled if:

- The section is in `SECTIONS_WITHOUT_COLLAPSE` (just leadership).
- The section has fewer than `TEAM_SECTION_PREVIEW_COUNT + 1` matching cards.
- The user is searching or filtering (so all matches stay visible).

When collapsed, the last visible card gets `.is-collapse-fade` (blur-out gradient), and `.is-collapse-hidden` is applied to the rest.

### Hash deep linking

`expandSectionForHash`:

1. Reads `location.hash` (with `decodeURIComponent` in a try/catch).
2. Calls `findPersonCardById` which checks the literal id and any legacy keys on the card's `dataset`.
3. If the matching card lives in a collapsible section that's currently collapsed, expands it and updates `aria-expanded`.
4. Schedules a smooth `scrollIntoView`.

It runs once at the end of `renderPageData()` and again on every `hashchange` event.

### Headshot variants

`getHeadshotVariantPath(imageSrc, variantName)` strips the file extension and inserts `variants/<variantName>/` before the basename. The result is used as the `<source srcset>` inside a `<picture>` element. The `<img>` falls back to the original `imageSrc` if the WebP variant is missing.

---

## `JS/project-data.js`

Exposes `window.ProjectData = { renderPageData }`.

- Loads `Projects/manifest.json` once.
- **Homepage**: `renderFeaturedSlides` reads the `featured` array and inserts slide markup before `#featuredSlidesMount`, then removes the mount.
  - Slides include an optional `imageSrcMobile` rendered as `<source media="(max-width: 680px)">` so mobile gets a different image.
- **Projects page**: `renderProjectsPage` reads the `page` array and fills `#projectPageGrid` with `.project-card` articles.

---

## `JS/events-data.js`

Exposes `window.EventsData = { renderPageData: renderHomeEvents }`. Runs only on the homepage (looks for `#homeEventsSection` and `#homeEventsMount`).

- Loads `Events/manifest.json`'s `homepage` array.
- 0 events: removes `#homeEventsSection`.
- 1 event: applies `home-events-grid--single`.
- 2+ events: applies `home-events-grid--carousel`.
- The first card sets `loading="eager"` and `fetchpriority="high"` so the hero image loads early.
- After render, dispatches a `resize` event so `script.js` can re-evaluate carousel arrow visibility.

---

## `JS/jobs-data.js`

The odd one out. Does **not** register on `window`. Listens for `DOMContentLoaded` directly and fills `#jobsBoard` from `Jobs/manifest.json`'s `jobs` array. Sorts entries by `posted` date descending. If a load error occurs it logs to `console.error` and leaves the board empty.

---

## When you edit a script...

Bump its cache-buster on every HTML page that loads it. The pattern in this codebase is `?v=YYYY-MM-DD-N`. See [`CONVENTIONS.md`](CONVENTIONS.md#cache-busters) for the exact procedure plus a PowerShell helper that does it across all 7 pages at once.
