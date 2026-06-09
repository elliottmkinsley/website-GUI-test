# CSS Guide

The site has 8 active stylesheets in `CSS/`. The shared design system lives in `CSS/style.css`; each topical page additionally loads one page-specific stylesheet.

## Stylesheet map

| File | Loaded by | Covers |
|---|---|---|
| `CSS/style.css` | every page | Design tokens, reset, typography, layout utilities, buttons, header/nav, hero slider, quick actions, about/mission, carousels, homepage team cards, stats, news primitives, footer, contact form primitives, and the equipment catalog. The big shared toolbox. |
| `CSS/events-home.css` | `index.html` | The homepage Events block (`.home-events-section`, card grid modifiers). |
| `CSS/teams.css` | `Our_Team.html` | The team directory: search/filter bar, person stacks, card chrome, section collapse fade. |
| `CSS/projects.css` | `Projects.html` | The projects hero (image + gradient) and project-card grid (hover lift, image zoom). |
| `CSS/donate.css` | `Donate.html` | The donate hero, mission band, four-card impact grid, final CTA. |
| `CSS/contact.css` | `Contact_Us.html` | The contact hero, two-column contact card + map, "Connect with us" social grid. |
| `CSS/jobs-page.css` | `Jobs.html` | The opportunities hero, intro, jobs board cards, footnote band. |
| `CSS/capabilities.css` | `Capabilities.html` | The atmospheric gold-into-blue background, hero, and lab-capability grid. |

## Where do I find styles for...?

| Component | File | Notes |
|---|---|---|
| The brand title and `<site-header>` nav | `style.css` | Search for the "Navigation Component (SiteHeader)" banner |
| Hamburger menu / mobile nav | `style.css` | Inside the `@media (max-width: 1170px)` block; see [`JS_GUIDE.md`](JS_GUIDE.md) for the matching JS |
| Hero slider on the home page | `style.css` | "Hero Slider" banner |
| Quick action buttons on the home page | `style.css` | "Quick Actions Bar" banner |
| Stats / Radiant's Impact band | `style.css` | "Dashboard & Metrics Visualization" banner |
| Homepage team carousel cards (`.card`) | `style.css` | "Meet The Team (homepage carousels only)" banner |
| Our Team page cards (`.person-feature`) | `teams.css` | |
| Project hero / project cards | `projects.css` | |
| Donate page everything | `donate.css` | |
| Contact page everything | `contact.css` | |
| Jobs board cards | `jobs-page.css` | |
| Capabilities labs | `capabilities.css` | |
| Footer | `style.css` | "Footer" banner |
| Buttons (`.btn`, `.btn-primary`, etc.) | `style.css` | "Component Layer: Buttons & Interactives" banner |
| Equipment catalog / product page | `style.css` | "EQUIPMENT CATALOG STYLES" + "PRODUCT / EQUIPMENT PAGE DESIGN" banners |

## Design tokens

All defined in the `:root` block at the top of `CSS/style.css`. Use these instead of hard-coded values.

### Brand colors

| Token | Purpose |
|---|---|
| `--nau-blue`, `--nau-blue-dark`, `--nau-blue-light` | Primary brand blue and shades |
| `--nau-gold`, `--nau-gold-dark`, `--nau-gold-light` | Accent gold and shades |
| `--nau-green`, `--nau-red`, `--nau-monsoon` | Secondary accents used sparingly |

### Neutrals

| Token | Purpose |
|---|---|
| `--white`, `--black` | Bookends |
| `--gray-50` through `--gray-900` | Greys in 50/100/200/.../900 increments |

### Theme

| Token | Purpose |
|---|---|
| `--bg-body` | Page background |
| `--text-main` | Default body text color |
| `--text-muted` | Secondary text color |
| `--border-light` | Subtle dividers |

### Spacing scale

| Token | Approx value |
|---|---|
| `--space-xs` | 4 px |
| `--space-sm` | 8 px |
| `--space-md` | 16 px |
| `--space-lg` | 24 px |
| `--space-xl` | 32 px |
| `--space-2xl` | 48 px |
| `--space-3xl` | 64 px |
| `--space-4xl` | 96 px |

### Typography

| Token | Value |
|---|---|
| `--font-display` | `'Roboto', sans-serif` |
| `--font-body` | `'Open Sans', sans-serif` |

Both fonts are loaded from Google Fonts in each page's `<head>`. When adding a new HTML page, copy the `<link rel="preconnect">` and `<link rel="stylesheet">` tags from an existing page so typography stays consistent.

### Radii, shadows, transitions

| Group | Tokens |
|---|---|
| Radii | `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-full` |
| Shadows | `--shadow-sm` through `--shadow-xl` |
| Transitions | `--trans-fast`, `--trans-med`, `--trans-slow`, `--trans-bouncy` |

## Responsive breakpoints

The codebase uses these `max-width` breakpoints (px). When adding new responsive rules, prefer reusing one of these rather than introducing a new value.

| Breakpoint | Used for |
|---|---|
| 1280 | Hero combined with `(max-height: 1050px)` to keep the hero copy readable on small laptops |
| 1180 | Hero / nav fine-tuning |
| **1170** | **Hamburger menu threshold** — header switches to mobile layout below this width. The matching JS lives in `JS/layout.js` (`matchMedia('(max-width: 1170px)')`). |
| 1024 | Tablet layouts |
| 950 | Capabilities, projects fine-tuning |
| 900 | Contact page two-column collapse |
| 768 | Standard tablet break |
| 680 | Quick-actions strip hides; project hero mobile slide image kicks in (`<source media="(max-width: 680px)">`) |
| 600 | Donate page fine-tuning |
| 520 | Smaller phone tweaks |
| 500 | Projects page hero hides entirely (very small phones) |
| 430 | Tightest phone-only adjustments |

A `@media (prefers-reduced-motion: reduce)` rule lives in both `style.css` and `teams.css` to disable non-essential animations for users who request reduced motion.

## Navigating `style.css`

The file is large (~4000 lines). Use these comment banners to jump around.

| Approx. line | Banner |
|---|---|
| 1 | NAU Radiant Center - Design System |
| 7 | Global Design Tokens (CSS Variables) |
| 176 | Utility Classes |
| 327 | Component Layer: Buttons & Interactives |
| 466 | Contact Gateway Page |
| 560 | Form & Layout Utility Classes |
| 679 | Navigation Component (SiteHeader) |
| 1035 | Hero Slider |
| 1494 | Quick Actions Bar |
| 1755 | About / Mission Section |
| 1786 | Carousel / Equipment Section |
| 2025 | Meet The Team (homepage carousels only) |
| 2462 | Dashboard & Metrics Visualization (Radiant's Impact) |
| 2761 | News & Multimedia |
| 3172 | Footer |
| 3324 | Contact & Forms |
| 3690 | Extractions (Part 2) |
| 3868 | EQUIPMENT CATALOG STYLES |
| 4300 | PRODUCT / EQUIPMENT PAGE DESIGN |

(Line numbers drift as the file is edited. If a banner has moved, search the file for the banner text.)

## Adding new styles

- Default to **extending `style.css`** if the rule is global (header, footer, button variants, typography, etc.).
- Default to **a page-specific stylesheet** if the rule only applies to one page (e.g. donate page hero, jobs board card).
- For brand-new pages, create a new `CSS/<page>.css` and load it after `style.css` in the page's `<head>`.

After editing any stylesheet, bump its cache buster on every HTML page that loads it. See [`CONVENTIONS.md`](CONVENTIONS.md#cache-busters).
