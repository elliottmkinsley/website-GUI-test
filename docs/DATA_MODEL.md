# Data Model

The site has four data domains. Each domain follows the same pattern:

1. A `manifest.json` lists the per-entry JSON files to load.
2. Each entry JSON file matches a documented schema.
3. A matching `*-data.js` script in `JS/` fetches the manifest, loads every entry in parallel, and renders cards/slides into mount points in the static HTML.

A JSON file that exists on disk but is not listed in its manifest is **silently ignored**. Always update the manifest when you add a new file.

---

## People

### Manifest

**Path:** `People/manifest.json`

**Shape:** A single object whose values are arrays of repo-relative paths.

```json
{
  "leadership":   [ "People/Leadership/...json" ],
  "faculty":      [ "People/Core Researchers/...json" ],
  "affiliation":  [ "People/Affiliation/...json" ],
  "staff":        [ "People/Staff/...json" ],
  "postdocs":     [ "People/Postdoctoral Scholars/...json" ],
  "graduate":     [ "People/Graduate Students & Assistants/...json" ]
}
```

The keys map to homepage container IDs and Our Team section IDs:

| Manifest key | Homepage container ID | Team page section ID |
|---|---|---|
| `leadership` | `#leadershipContainer` | `#leadership` |
| `faculty` | `#facultyContainer` | `#faculty` |
| `affiliation` | `#affiliationContainer` | `#affiliation` |
| `staff` | `#staffContainer` | `#staff` |
| `postdocs` | `#postDocContainer` | `#postdocs` |
| `graduate` | `#gradContainer` | `#graduate` |

### Per-entry schema

| Field | Required | Type | Where it appears |
|---|---|---|---|
| `name` | yes | string | Card heading; person URL hash is derived from this (`first-last` slug) |
| `role` | yes | string | Card subtitle on home and team pages |
| `type` | optional | string | Combined into the team page subtitle as `"role • type"` |
| `homepageType` | optional | string | Replaces `type` on homepage cards only (can include `\n`) |
| `school` | yes | string | School/department line on both surfaces |
| `secondarySchool` | optional | string | Second school line, homepage card only |
| `affiliation` | yes | string | "Affiliation" quick fact on the team page |
| `focus` | yes | string | "Focus" quick fact. Use ` • ` (space-bullet-space) to separate sub-topics; the team page splits on it to render bullets |
| `bio` | yes | string | Long bio on the team page; collapsible on small viewports |
| `profileUrl` | optional | URL or `mailto:` | "View Profile" button. Empty string or `#` hides the button |
| `imageSrc` | yes | string | Repo-relative path to the headshot, e.g. `Images/People/Kristen_Bennette.jpg` |
| `imageFit` | optional | CSS `object-fit` value | Inline style override on the `<img>` |
| `imagePosition` | optional | CSS `object-position` value | Inline style override on the `<img>` |

### Sample (annotated)

```json
{
  "name": "Dr Kristen Bennett",
  "role": "Associate Research Professor",
  "school": "Department of Astronomy and Planetary Science",
  "affiliation": "Northern Arizona University",
  "focus": "Lunar and Martian geology • Planetary remote sensing • Surface evolution",
  "bio": "Kristen A. Bennett is a planetary scientist...",
  "profileUrl": "https://directory.nau.edu/?person=kb2473",
  "imageSrc": "Images/People/Kristen_Bennette.jpg"
}
```

### Sort order behavior

`team-data.js` defines `RANDOMIZED_SECTIONS = {faculty, affiliation, postdocs, graduate}`.

- **Homepage** carousels: those four sections are shuffled on every page load. `leadership` and `staff` keep their manifest order.
- **Team page**: those four sections are sorted alphabetically by last name. `leadership` and `staff` keep their manifest order.

### Headshot variants

The runtime expects WebP variants alongside the base headshot:

```
Images/People/<basename>.jpg                       (base, used as <img src> fallback)
Images/People/variants/card/<basename>.webp        (homepage carousel)
Images/People/variants/team/<basename>.webp        (Our Team page)
```

If a variant is missing, the `<picture>` element falls through to the original `imageSrc` and the page still works. Variants are not auto-generated — see [`guides/create-image-variants.md`](guides/create-image-variants.md).

---

## Projects

### Manifest

**Path:** `Projects/manifest.json`

**Shape:**

```json
{
  "featured": [ "Projects/Featured/...json" ],
  "page":     [ "Projects/Page/...json" ]
}
```

The two arrays drive different surfaces:

- **`featured`** — entries become full-bleed slides in the homepage hero carousel (`#featuredSlidesMount`).
- **`page`** — entries become cards in the `#projectPageGrid` on `Projects.html`.

The same project can appear in both arrays with slightly different copy (precedent: `grand-canyon-hidden-water.json` exists in both `Projects/Featured/` and `Projects/Page/`).

### Per-entry schema

| Field | Required | Where used | Notes |
|---|---|---|---|
| `title` | yes | Slide H2 / card H2 | |
| `description` | yes | Slide deck / card lede | |
| `imageSrc` | yes | `<img>` background | `.jpg`, `.png`, or `.webp` all work |
| `imageSrcMobile` | optional | Featured slides only | `<source media="(max-width: 680px)">` swap-in for narrow screens |
| `imageAlt` | optional | `alt` text | Defaults to `title` |
| `linkUrl` | yes | CTA `href` | Empty falls back to `#` |
| `buttonLabel` | optional | CTA text | Defaults to "Read Full Story" (slides) or "Read the full story" (cards) |
| `badge` | optional | Card corner badge | Defaults to "Featured Story" on cards |
| `source` | optional | `.source-pill` on cards | Defaults to "Story" |
| `meta` | optional | Secondary text on cards | |
| `impact` | optional | "Radiant impact" block on cards | |

### Sample

```json
{
  "title": "Mapping Hidden Water in the Grand Canyon",
  "description": "Radiant researchers use airborne sensors to find groundwater seeps...",
  "imageSrc": "Images/News/Grand_Canyon_Hidden_Water.jpg",
  "linkUrl": "https://...",
  "source": "NAU News"
}
```

---

## Events

### Manifest

**Path:** `Events/manifest.json`

**Shape:**

```json
{ "homepage": [ "Events/...json" ] }
```

Only one array, `homepage`, since events currently only appear on the homepage Events block.

### Per-entry schema

| Field | Required | Notes |
|---|---|---|
| `headline` | yes (or use `title` as fallback) | H3 on the event card |
| `slug` | optional | Stored on `data-event-slug`; used for DOM hooks |
| `summary` | optional | Long copy below the headline; omitted if absent |
| `imageSrc` | yes | Hero image on the card; usually under `Images/Events/` |
| `imageAlt` | optional | Defaults to `headline` |

### Sample

```json
{
  "headline": "Colorado Space Symposium 2026",
  "slug": "colorado-space-symposium",
  "summary": "Drs. Shafer and Edwards represented Radiant at the symposium...",
  "imageSrc": "Images/Events/space_symposium.jpg"
}
```

### Behavior

- 0 events: `#homeEventsSection` removes itself from the page.
- 1 event: card uses `home-events-grid--single` class.
- 2+ events: grid uses `home-events-grid--carousel` class with arrow controls.

---

## Jobs

### Manifest

**Path:** `Jobs/manifest.json`

**Shape:**

```json
{ "jobs": [ "Jobs/...json" ] }
```

### Per-entry schema

| Field | Required | Where used |
|---|---|---|
| `title` | yes | Job card heading |
| `slug` | optional | `data-slug` on the card |
| `unit` | optional | Meta line (org/department) |
| `employmentType` | optional | Meta line (e.g. `"Summer 2026"`) |
| `location` | optional | Meta line |
| `summary` | yes | Intro paragraph |
| `highlights` | optional | Array of strings rendered as `<ul>` |
| `applyUrl` | optional | Button `href`; defaults to `#` |
| `applyLabel` | optional | Button text; defaults to "Apply" |
| `posted` | optional | `YYYY-MM-DD` — used for sort order only, not displayed |
| `closingDisplay` | optional | "Closing:" line below the highlights |

### Sort order

Newest `posted` date first. Entries without `posted` sort to the end.

### Sample

```json
{
  "title": "Summer Research Design Assistant",
  "slug": "summer-research-design-assistant",
  "unit": "Radiant Center for Remote Sensing",
  "employmentType": "Summer 2026",
  "summary": "We are looking for an undergraduate to support the design...",
  "highlights": [
    "Collaborate on graphic and web design",
    "Help maintain the Radiant website"
  ],
  "applyUrl": "mailto:radiant@nau.edu",
  "applyLabel": "Email to apply",
  "posted": "2026-03-15",
  "closingDisplay": "Closing April 30, 2026"
}
```
