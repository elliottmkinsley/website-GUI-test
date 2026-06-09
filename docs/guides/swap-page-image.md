# Swap a Page Banner / Hero Image

The hero/banner imagery on most pages is a plain `<img>` tag inside a hero section. This guide walks through replacing one. Use the Donate page as the example — the same pattern applies to the other pages.

## Where each page's hero image lives

| Page | Image file | Source location in HTML |
|---|---|---|
| `Donate.html` | `Images/donation_banner.jpg` | inside `.donate-hero-media > img.donate-hero-img` |
| `Contact_Us.html` | `Images/News/drone-lab.jpg` | hero background, set via `.contact-hero-section`'s `<img>` |
| `Jobs.html` | `Images/News/visions-spaceflight-hardware.jpg` | hero background |
| `Projects.html` | `Images/News/Grand_Canyon_Hidden_Water.jpg` | hero background |
| `Capabilities.html` | The hero is decorative gradient + text only — no image swap needed |
| `Our_Team.html` | The hero is gradient + text only — no image swap needed |
| `index.html` | The home hero uses `Projects/Featured/*.json` slides — see [`add-project.md`](add-project.md) instead |

## Step 1 — Drop the new image into the right folder

- For page banners that are decorative photos, use `Images/<descriptive-name>.jpg` (e.g. `Images/donation_banner.jpg`).
- For images that double as project/news imagery, use `Images/News/<descriptive-name>.jpg`.

Compress before saving. The hero JPGs in this codebase are typically 800-1500 KB; aim under 1 MB.

## Step 2 — Edit the HTML

Open the page (e.g. `Donate.html`). Find the hero block. For Donate it looks like this:

```html
<section class="donate-hero" aria-label="Support the Radiant Center">
    <div class="donate-hero-media" aria-hidden="true">
        <img src="Images/donation_banner.jpg" alt="" class="donate-hero-img">
        <div class="donate-hero-overlay"></div>
    </div>
    ...
</section>
```

Change the `src` to your new file. Leave the `class`, `alt`, and overlay div alone:

```html
<img src="Images/your-new-banner.jpg" alt="" class="donate-hero-img">
```

## Step 3 — Test

Open the page in a browser. Confirm:

- The new image fills the hero with the existing gradient overlay on top.
- The page title, eyebrow tag, and CTAs are still readable. If your image is too bright, the overlay should still darken it enough; if not, you may need to choose a different photo or ask a developer to tune the overlay opacity in `CSS/donate.css` (or the matching page CSS).

## What about cache busters?

Image swaps don't require a cache-buster bump. The browser fetches images by URL — a different filename means a fresh request. If you reuse the same filename for a different image (not recommended), users may see the cached old version until they hard-refresh; rename the file instead.

## Other hero patterns

Most other pages follow the same pattern (find the `<img>` inside the hero block, change the `src`). If a page uses a CSS `background-image` instead, the URL lives in `CSS/<page>.css` — search the file for `url(`. After editing CSS, bump the page's CSS cache buster per [`../CONVENTIONS.md`](../CONVENTIONS.md#cache-busters).
