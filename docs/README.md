# Radiant Center for Remote Sensing — Documentation

This folder contains everything a future maintainer or content editor needs to understand and work with the radiant.nau.edu website.

## Where should I start?

| If you are... | Read first |
|---|---|
| A developer new to this codebase | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Looking up how a specific page is built | [`PAGES.md`](PAGES.md) |
| Writing or editing JSON data (people, projects, events, jobs) | [`DATA_MODEL.md`](DATA_MODEL.md) |
| Editing styles or hunting for a specific CSS rule | [`CSS_GUIDE.md`](CSS_GUIDE.md) |
| Editing scripts or hunting for a specific JS function | [`JS_GUIDE.md`](JS_GUIDE.md) |
| Bumping cache-busters, naming files, generating image variants | [`CONVENTIONS.md`](CONVENTIONS.md) |
| **A non-technical content editor** adding a new person, project, event, or job | jump straight to [`guides/`](guides/) |

## Document index

### Reference (developer-oriented)

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — High-level architecture: how a page renders, where data lives, and how the four data domains (People, Projects, Events, Jobs) flow into the DOM.
- [`PAGES.md`](PAGES.md) — Per-page anatomy: what `<main>` class, sections, mount points, and CSS/JS files each HTML page uses.
- [`DATA_MODEL.md`](DATA_MODEL.md) — JSON schemas for every data domain, plus the manifest pattern.
- [`CSS_GUIDE.md`](CSS_GUIDE.md) — Design tokens, the 8 active stylesheets, every responsive breakpoint, and a navigation index of the major sections inside `style.css`.
- [`JS_GUIDE.md`](JS_GUIDE.md) — File-by-file reference for the 7 scripts in `JS/`, plus the web component system, hash-driven deep linking, and the data-loading pattern.
- [`CONVENTIONS.md`](CONVENTIONS.md) — Cache-buster procedure, file naming, the WebP-variant workflow, and other things that aren't obvious from the code alone.

### Recipes (content-editor-oriented)

- [`guides/add-team-member.md`](guides/add-team-member.md) — Add a person to one of the team sections.
- [`guides/add-project.md`](guides/add-project.md) — Add a homepage hero slide and/or a Projects-page card.
- [`guides/add-event.md`](guides/add-event.md) — Add an event to the homepage Events block.
- [`guides/add-job-posting.md`](guides/add-job-posting.md) — Add a job to the Opportunities page.
- [`guides/swap-page-image.md`](guides/swap-page-image.md) — Replace a hero or banner image on any page.
- [`guides/create-image-variants.md`](guides/create-image-variants.md) — Generate the `card.webp` and `team.webp` variants for new headshots.

### Tooling

- [`../gui/README.md`](../gui/README.md) — Developer guide for the Radiant Content GUI: a PySide6 desktop app for editors to add/edit/delete/reorder People, Projects, Events, and Jobs, then publish to the NAU SMB share and to a GitHub `archive` branch. Lives at `gui/` inside this repo.
- [`INSTALLING.md`](INSTALLING.md) — End-user installation guide for the packaged Windows installer (`RadiantContentGUISetup.exe`).
- [`CHANGELOG.md`](CHANGELOG.md) — Release notes for the Radiant Content GUI. CI promotes `## [Unreleased]` to a versioned entry on every tag.

## Project at a glance

- **Stack:** Plain HTML, CSS, and JavaScript. No build system, no framework, no bundler.
- **Deployment:** Static files served as-is. To deploy, copy the project folder to the web host. To preview locally, open `index.html` in a browser.
- **Pages:** 7 active HTML pages at the project root (`index.html`, `Capabilities.html`, `Contact_Us.html`, `Donate.html`, `Jobs.html`, `Our_Team.html`, `Projects.html`).
- **Data:** All people, projects, events, and jobs live as JSON files inside the `People/`, `Projects/`, `Events/`, and `Jobs/` folders. Each domain has a `manifest.json` that lists the files to load.
- **Scripts:** 7 scripts in `JS/` orchestrated by `JS/script.js` after `DOMContentLoaded`.
- **Styles:** 8 stylesheets in `CSS/` with `style.css` as the shared design system and one stylesheet per page topic.
- **Browser support:** Modern Chromium, WebKit, and Gecko. No polyfills.
