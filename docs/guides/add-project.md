# Add a Project

Projects appear in two places:

- **Homepage hero carousel** — full-bleed slides at the top of `index.html`. Driven by `Projects/Featured/*.json` files listed in the `featured` array of `Projects/manifest.json`.
- **Projects page grid** — cards on `Projects.html`. Driven by `Projects/Page/*.json` files listed in the `page` array.

A given project can appear in one or both. They're separate JSON files because the carousel and the card usually want slightly different copy (the carousel needs a punchy 1-2 sentence deck; the card can carry more detail).

## What you need before you start

- Project title, 1-2 paragraph description, and a link URL.
- A landscape image, ideally at least 1600 px wide for the homepage hero. Optionally a separate mobile crop.
- Optional: a "Radiant impact" sentence, a source label (e.g. "NAU News"), and a meta tag.

---

## Adding a homepage hero slide

### Step 1 — Drop the image into `Images/News/`

Use a descriptive filename: `Images/News/<short-name>.jpg`. Keep the file under ~500 KB if possible (compress with Squoosh, TinyPNG, or similar).

If you also want a mobile-specific image (taller crop or different image entirely), save it as `Images/News/mobile-<short-name>.jpg` or similar.

### Step 2 — Create the JSON

Create `Projects/Featured/<short-name>.json`. Copy from a sibling like `Projects/Featured/grand-canyon-hidden-water.json` and edit:

```json
{
  "title": "Mapping Hidden Water in the Grand Canyon",
  "description": "Radiant researchers use airborne sensors to find groundwater seeps that sustain rare desert ecosystems.",
  "imageSrc": "Images/News/Grand_Canyon_Hidden_Water.jpg",
  "imageSrcMobile": "Images/News/mobile-grand-canyon.jpg",
  "linkUrl": "https://news.nau.edu/...",
  "buttonLabel": "Read Full Story"
}
```

Keep `description` to 1-2 sentences — the homepage blue overlay box gets crowded otherwise.

### Step 3 — Register in the manifest

Open `Projects/manifest.json`. Add the new path to the `featured` array:

```json
{
  "featured": [
    "Projects/Featured/kristen-bennett-lunar-south-pole-science.json",
    "Projects/Featured/your-new-slide.json",
    ...
  ],
  "page": [ ... ]
}
```

Order in the array is the slide order in the carousel.

### Step 4 — Test

Open `index.html`. The hero slider should auto-advance through the slides; navigate with the arrow buttons or dots. Resize the browser narrower than 680 px to verify the mobile image (if you supplied one) takes over.

---

## Adding a Projects-page card

### Step 1 — Drop the image into `Images/News/`

Same as above. Cards display landscape images at ~16:9.

### Step 2 — Create the JSON

Create `Projects/Page/<short-name>.json`. Copy from `Projects/Page/grand-canyon-hidden-water.json` and edit:

```json
{
  "title": "Mapping Hidden Water in the Grand Canyon",
  "description": "Radiant researchers spent two field seasons surveying ...",
  "imageSrc": "Images/News/Grand_Canyon_Hidden_Water.jpg",
  "linkUrl": "https://news.nau.edu/...",
  "buttonLabel": "Read the full story",
  "badge": "Featured Story",
  "source": "Grand Canyon National Park",
  "meta": "Hydrology",
  "impact": "Findings inform park management decisions and water-rights planning across the Colorado Plateau."
}
```

Cards have more room than slides, so the description can be longer (3-5 sentences). The optional `impact` field renders as a "Radiant impact:" block at the bottom of the card.

### Step 3 — Register in the manifest

Add the path to the `page` array in `Projects/manifest.json`. Order matters — the array order is the grid order.

### Step 4 — Test

Open `Projects.html`. Confirm the new card appears in the right slot.

---

## Adding the same project to both surfaces

You can have separate `Projects/Featured/<slug>.json` and `Projects/Page/<slug>.json` for the same project with different copy. That's how `grand-canyon-hidden-water.json` already works:

- The Featured version has a punchy slide description and a `"source": "NAU News"` because it links to a news story.
- The Page version has a longer description and `"source": "Grand Canyon National Park"` because it cites the field partner.

If you'd rather have identical copy in both, just duplicate the JSON.

## Schema reference

Every supported field with type and behavior is in [`../DATA_MODEL.md`](../DATA_MODEL.md#projects).

## Removing a project

1. Remove the path from `Projects/manifest.json` (from `featured`, `page`, or both).
2. Optionally delete the JSON and image files.
