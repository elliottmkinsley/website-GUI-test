# Add an Event

Events appear in the "Events & Outreach" block on the homepage. Behind the scenes:

- One event renders as a single featured card.
- Two or more events render as a horizontally scrollable carousel.
- Zero events makes the entire section disappear.

## What you need before you start

- Event headline.
- 1-2 sentence summary.
- A representative photo (landscape, ideally at least 1200 px wide).

---

## Step 1 — Drop the photo into `Images/Events/`

Use a descriptive filename: `Images/Events/<short-name>.jpg`. Compress to keep under ~500 KB.

## Step 2 — Create the JSON

Create `Events/<short-name>.json`. Copy from `Events/science-on-the-square.json` as a template:

```json
{
  "headline": "Colorado Space Symposium 2026",
  "slug": "colorado-space-symposium",
  "summary": "Drs. Shafer and Edwards represented Radiant Center at the symposium, presenting the VISIONS space camera project.",
  "imageSrc": "Images/Events/space_symposium.jpg",
  "imageAlt": "Drs. Shafer and Edwards at the Colorado Space Symposium"
}
```

Field reminders:

- **`headline`** is required. (`title` is also accepted as a fallback.)
- **`slug`** is optional but recommended; it's stored on the card as `data-event-slug`.
- **`summary`** is optional. If empty, only the headline shows on the card.
- **`imageSrc`** is required.
- **`imageAlt`** is optional; defaults to the headline if omitted.

The full schema is in [`../DATA_MODEL.md`](../DATA_MODEL.md#events).

## Step 3 — Register in the manifest

Open `Events/manifest.json`. Add the path to the `homepage` array:

```json
{
  "homepage": [
    "Events/science-on-the-square.json",
    "Events/colorado-space-symposium.json"
  ]
}
```

Order matters — first in the array is first in the carousel.

## Step 4 — Test

Open `index.html`. Scroll to the "Events & Outreach" block. The new event should appear with its photo and copy. With multiple events the arrow buttons let you scroll between them.

If you only have one event, the layout switches to a single hero card. If you remove the last event from the manifest, the entire `#homeEventsSection` is removed at runtime.

## Removing an event

Remove the path from `Events/manifest.json`. The JSON and image files can stay on disk if you might use them again later.
