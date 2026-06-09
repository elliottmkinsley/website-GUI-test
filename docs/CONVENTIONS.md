# Conventions

The "things that aren't obvious from the code" file. If you've read [`ARCHITECTURE.md`](ARCHITECTURE.md), this is where the operational details live.

## Cache busters

Every `<link>` and `<script>` tag in HTML uses a query string to tell the browser when to re-fetch the file:

```html
<link rel="stylesheet" href="CSS/style.css?v=2026-04-29-2">
<script src="JS/layout.js?v=2026-04-29-2"></script>
```

Format: `?v=YYYY-MM-DD-N` where `N` is a small integer that increments if you ship multiple versions on the same day.

### When to bump

| Edit | Bump |
|---|---|
| Edited a CSS file | Its `?v=` on every HTML page that loads it |
| Edited `JS/layout.js`, `JS/script.js`, or `JS/site-config.js` | Its `?v=` on every HTML page (those scripts are loaded on every page) |
| Edited a `*-data.js` script | Its `?v=` on every HTML page that loads it (consult [`PAGES.md`](PAGES.md)) |
| Edited only a JSON file | Often nothing — but if you want everyone to see the change immediately, bump `assetVersion` in `JS/site-config.js` and bump `site-config.js` itself on every HTML page |
| Edited only HTML | Nothing — the browser refetches HTML on each navigation |
| Edited only an image | Nothing |

### How to bump across all pages at once

The HTML files in this repo were edited en masse before with a PowerShell one-liner. Replace the date strings to suit:

```powershell
$files = @('Capabilities.html','Contact_Us.html','Donate.html','Jobs.html','Our_Team.html','Projects.html','index.html')
foreach ($f in $files) {
  (Get-Content $f -Raw) `
    -replace 'CSS/style\.css\?v=2026-04-29-2','CSS/style.css?v=2026-04-29-3' `
    -replace 'JS/layout\.js\?v=2026-04-29-2','JS/layout.js?v=2026-04-29-3' `
    | Set-Content -NoNewline $f
}
```

After bumping, do a search to confirm no stale versions remain. From the project root:

```powershell
rg "style\.css\?v=" *.html
```

## File and folder naming

### People JSON files

- Filename: `kebab-case-of-name.json` (e.g. `kristen-bennett.json`, `duan-biggs.json`).
- Folder: matches the team group exactly. The six folders are `People/Leadership/`, `People/Core Researchers/`, `People/Affiliation/`, `People/Staff/`, `People/Postdoctoral Scholars/`, and `People/Graduate Students & Assistants/`.
- The path you put into `People/manifest.json` must use forward slashes and exact-case folder names: `"People/Core Researchers/kristen-bennett.json"`.

### Headshot images

- Filename: any unique slug, often `First_Last.jpg` or initials (e.g. `Kristen_Bennette.jpg`, `jagoda_j.jpg`). Whatever you choose, the JSON `imageSrc` must match exactly.
- Path: `Images/People/<basename>.<ext>`.
- WebP variants: `Images/People/variants/card/<basename>.webp` and `Images/People/variants/team/<basename>.webp`. The basename **must match exactly**, including case (case-sensitive on some web hosts even though Windows is forgiving locally).

A shared placeholder, `Images/People/blank-headshot.png`, exists for people whose photo is not available.

### Project / event / job filenames

- `kebab-case-slug.json`. The slug usually matches a `slug` field inside the JSON, but the filename itself is the source of truth in the manifest.

### Page-banner / news images

- `Images/<descriptive-name>.jpg` for hero banners (e.g. `Images/donation_banner.jpg`).
- `Images/News/<descriptive-name>.jpg` for project-card / story images.
- `Images/Events/<descriptive-name>.jpg` for event imagery.

## Image variants are NOT auto-generated

There is no build step in this repo. The two WebP variants per headshot must be produced manually whenever you add a new person. The recipe is in [`guides/create-image-variants.md`](guides/create-image-variants.md).

If a variant file is missing, the runtime gracefully falls back to the original `imageSrc` — the page still works, it just loads a slightly larger image.

## Person URL hashes

The site supports deep-linking to a specific person via `Our_Team.html#first-last`. The `first-last` slug is generated from `name` by `personKeyFromName` in `JS/team-data.js` (lowercase, strips diacritics, hyphenates).

If you rename a person and existing links would break, add the old slug(s) as `data-person-legacy-keys` in the team page or rely on `legacyPersonKeysFromName` to produce them automatically. See `JS/team-data.js`.

## Manifest-driven loading

Adding a JSON file to disk does **not** make the site render it. You must add the file path to the matching `manifest.json` array. This is intentional — it lets you stage drafts on disk without exposing them.

Practical implication: when reviewing changes, always diff the manifest first. If a manifest entry is missing, that JSON is dead weight (and was caught by the cleanup audit in May 2026).

## Browser support

The site targets modern Chromium, WebKit (Safari), and Gecko (Firefox). It uses:

- `<picture>` element with WebP sources
- `IntersectionObserver` and `ResizeObserver`
- `matchMedia` with `change` event
- Custom Elements v1 (no Shadow DOM is used)
- `fetch()`, `async/await`, `Promise.all`

No polyfills are bundled. Internet Explorer is not supported.

## Testing changes locally

Open any `.html` file in a browser. Two caveats:

1. **JSON fetches over `file://`** are blocked by some browsers (Chrome especially). If a page renders blank where data should appear, run a tiny static server. Easiest options:
   - VS Code "Live Server" extension.
   - From a terminal in the project root: `python -m http.server 8000` and open `http://localhost:8000/`.
2. **Hard refresh** (`Ctrl+Shift+R`) after bumping cache busters to verify the new versions actually load. The browser console's Network tab will show the `?v=...` you expect.

## Adding a new HTML page

1. Copy an existing simple page (e.g. `Capabilities.html`) as a starting point.
2. Update `<title>`, `<meta>` description, the `<main>` class, and the page content.
3. Update or remove the page-specific stylesheet `<link>` tag.
4. Add or remove page-specific data scripts (e.g. only include `team-data.js` if the page renders team data).
5. Add the page to the `<site-header>` template in `JS/layout.js` if it should show in the nav (with a matching `data-path="<filename>"`), and bump `layout.js` on every HTML page.
6. Add the page to `<site-footer>` similarly if it should appear in the footer.
7. Verify cache busters are current per the table in [`PAGES.md`](PAGES.md#page-asset-version-reference-cache-busters).

## Glossary

| Term | Meaning |
|---|---|
| Manifest | The `manifest.json` in each data folder; lists which entry JSONs to load |
| Entry / per-entry JSON | An individual person, project, event, or job file |
| Mount point | An empty container in the static HTML that a data script fills at runtime (e.g. `#jobsBoard`) |
| Cache buster | The `?v=YYYY-MM-DD-N` query string on CSS/JS URLs that forces fresh downloads |
| Variant | A pre-generated alternate format of an image, currently only WebP versions of headshots in two sizes |
| Web component | A `customElements.define()`-registered HTML element. We have two: `<site-header>` and `<site-footer>` from `JS/layout.js` |
