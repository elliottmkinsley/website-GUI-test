# Add a Job Posting

Jobs appear on `Jobs.html` (the Opportunities page). The board is sorted with the newest `posted` date first.

## What you need before you start

- Job title and a 1-2 paragraph summary.
- Optional: department/unit name, employment type (e.g. "Summer 2026"), location, 3-5 highlights bullet points.
- An apply URL or `mailto:` address.
- The date you posted the job (used only for sort order).

---

## Step 1 — Create the JSON

Create `Jobs/<slug>.json`. Copy from `Jobs/summer-research-design-assistant.json` as a template:

```json
{
  "title": "Summer Research Design Assistant",
  "slug": "summer-research-design-assistant",
  "unit": "Radiant Center for Remote Sensing",
  "employmentType": "Summer 2026",
  "summary": "We are looking for an undergraduate to support the design and development of Radiant's communications materials, including the website and printed flyers.",
  "highlights": [
    "Collaborate on graphic and web design",
    "Help maintain and improve the Radiant website",
    "Coordinate with researchers on visual materials"
  ],
  "applyUrl": "mailto:radiant@nau.edu",
  "applyLabel": "Email to apply",
  "posted": "2026-03-15",
  "closingDisplay": "Closing April 30, 2026"
}
```

Field reminders:

- **`title`** and **`summary`** are required.
- **`slug`** is optional; it's stored on the card as `data-slug` and used as a stable handle for the listing.
- **`highlights`** is an optional array of strings rendered as a bulleted list under the summary.
- **`applyUrl`** can be a URL or a `mailto:` link. Defaults to `#` if missing.
- **`applyLabel`** is the apply button text. Defaults to `"Apply"`.
- **`posted`** must be a `YYYY-MM-DD` string. It's only used for sort order — newest posted date appears first.
- **`closingDisplay`** is shown as a "Closing: ..." line under the highlights. Free-form text — write whatever you want users to see.

The full schema is in [`../DATA_MODEL.md`](../DATA_MODEL.md#jobs).

## Step 2 — Register in the manifest

Open `Jobs/manifest.json`. Add the new path to the `jobs` array:

```json
{
  "jobs": [
    "Jobs/summer-research-design-assistant.json",
    "Jobs/your-new-posting.json"
  ]
}
```

Manifest order doesn't matter — the script sorts by `posted` date descending.

## Step 3 — Test

Open `Jobs.html`. The new posting should appear in the "Open Roles" section. Confirm:

- Title, unit, and employment type render correctly in the meta line.
- Highlights render as a bullet list.
- The apply button uses the correct URL and label.
- If you supplied `closingDisplay`, the closing line appears below the highlights.

## Removing or closing a job

When a position is filled or the deadline passes:

1. Remove the path from `Jobs/manifest.json`.
2. Optionally delete the JSON file. (Many teams prefer to keep the file as a record — that's fine; manifest-driven loading means it's just inert.)

## Common mistakes

- **`posted` typo.** Use `YYYY-MM-DD`, not `MM/DD/YYYY`. A bad date format silently sinks the entry to the bottom of the sort.
- **Forgetting the manifest update.** Adding a JSON file alone does nothing — the manifest must list it.
- **HTML in `summary`.** Keep summaries as plain text. The renderer escapes HTML for safety.
