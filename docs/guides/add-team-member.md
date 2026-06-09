# Add a Team Member

Use this guide to add a new person to one of the team sections (Leadership, Core Researchers, Affiliate Researchers, Staff, Postdoctoral Scholars, or Graduate Students & Assistants). The new person will appear in both the Our Team page and the matching homepage carousel.

## What you need before you start

- The person's name, role, school/department, focus areas (3 short topics), and bio.
- A headshot image (`.jpg` or `.png`). If you don't have one, use the placeholder `Images/People/blank-headshot.png`.
- A profile URL — typically `https://directory.nau.edu/?person=<id>` or a `mailto:` address.

---

## Step 1 — Pick the right folder

Match the person to one of these team groups, then use the matching folder under `People/`:

| Person type | Folder |
|---|---|
| Director / co-director / executive role | `People/Leadership/` |
| Faculty researcher within Radiant | `People/Core Researchers/` |
| External NAU faculty affiliate | `People/Affiliation/` |
| Operations, ops support, lab manager | `People/Staff/` |
| Postdoctoral scholar | `People/Postdoctoral Scholars/` |
| Grad student, masters student, undergraduate research assistant | `People/Graduate Students & Assistants/` |

## Step 2 — Create the JSON file

Inside that folder, create a new file named `first-last.json` (lowercase, hyphenated). For example, `kathleen-orndahl.json` or `duan-biggs.json`.

Open an existing JSON in the same folder as a template — for example `People/Core Researchers/kristen-bennett.json`. Copy its contents and fill in your fields:

```json
{
  "name": "Dr First Last",
  "role": "Their Title",
  "school": "Department of ...",
  "affiliation": "Northern Arizona University",
  "focus": "Topic one • Topic two • Topic three",
  "bio": "A 3-6 sentence third-person bio describing background, research focus, and relevant credentials or recognitions.",
  "profileUrl": "https://directory.nau.edu/?person=ABC123",
  "imageSrc": "Images/People/First_Last.jpg"
}
```

Field reminders:

- **`name`** drives the URL hash. The site converts "Dr Jane Doe" into `jane-doe` (it strips honorifics and lowercases).
- **`focus`** uses ` • ` (space, bullet, space) between topics. The team page splits on that to render bullets.
- **`bio`** should be in third person.
- **`profileUrl`** can be empty (`""`), a real URL, or `mailto:firstname.lastname@nau.edu`. An empty string hides the "View Profile" button.

The full schema with every optional field is in [`../DATA_MODEL.md`](../DATA_MODEL.md#people).

## Step 3 — Add the headshot

Put the image at the path you specified in `imageSrc`. Naming convention: `Images/People/First_Last.jpg`.

If you want the carousel and team-page WebP variants too (recommended for site performance), follow [`create-image-variants.md`](create-image-variants.md). If you skip variants, the site uses the original image everywhere — still works, just slightly heavier.

If you don't have a headshot yet, use:

```json
"imageSrc": "Images/People/blank-headshot.png"
```

The placeholder already has the matching WebP variants in place.

## Step 4 — Register in the manifest

Open `People/manifest.json`. Find the array that matches the team group (e.g. `"faculty"` for Core Researchers). Add the new file path to the array:

```json
"faculty": [
  ...
  "People/Core Researchers/kaitlyn-davis.json",
  "People/Core Researchers/kathleen-orndahl.json",
  "People/Core Researchers/keith-nowicki.json",
  ...
]
```

The order in this array doesn't matter for `faculty`, `affiliation`, `postdocs`, and `graduate` (they're randomized on the homepage and sorted alphabetically by last name on the team page). For `leadership` and `staff`, manifest order is preserved on both surfaces.

## Step 5 — Test

1. Open `Our_Team.html` in a browser. Confirm the new card appears in the right section.
2. Open `index.html`. Confirm the card also appears in the matching homepage carousel.
3. Use the search box on Our Team to make sure searching by the person's name finds them.
4. Try clicking "More Info" on the homepage card — it should jump to the right person on the team page (deep linking via `Our_Team.html#first-last`).

If the card doesn't appear, check the browser console for a JSON parse error (most common: a stray comma or missing quote in the new file). Also double-check the manifest path uses forward slashes and exact-case folder names.

## Updating the home-page metric counter

When you add a new Core Researcher, also update the count in `index.html`'s "Radiant's Impact" panel:

```html
<div class="metric-box"><span class="metric-value">19</span><span
        class="metric-label">Core Researchers</span>
</div>
```

Bump that number to match the new manifest length.

## Removing a team member

Reverse the process:

1. Remove the path from `People/manifest.json`.
2. Optionally delete the JSON file and the headshot images. (Leaving them on disk is harmless because anything not in the manifest is ignored.)
3. If you removed a Core Researcher, decrement the homepage metric counter.
