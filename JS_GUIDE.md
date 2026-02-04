# NAU Nano - JavaScript Developer Guide

This document describes the structure and functionality of `script.js`. The script is designed to handle interactivity for the main page and can be extended for sub-pages.

## 1. Core Architecture
- **Event-Driven**: All logic is wrapped in `document.addEventListener('DOMContentLoaded', ...)` to ensure it only runs after the HTML is parsed.
- **Progressive Enhancement**: Features like Scroll Animations use `IntersectionObserver` but have safe fallbacks for older browsers or if JS fails.

## 2. Key Features

### Sticky Header
- **Function**: Monitors scroll position.
- **Behavior**: Toggles the `.scrolled` class on the `<header id="mainHeader">` when user scrolls past 50px.
- **Customization**: Adjust the `50` threshold in the scroll event listener if needed.

### Hero Slider
- **Logic**: Custom vanilla JS implementation (no JQuery/Bootstrap).
- **Elements**: Looks for `.slide`, `#nextSlide`, `-#prevSlide`.
- **Timing**: Auto-rotates every 6 seconds (`6000ms`).
- **Usage**: To add a slide, simply duplicate a `.slide` div in HTML. The JS automatically counts total slides.

### Mobile Menu
- **Elements**: `.mobile-toggle` (Hamburger icon) and `.nav-menu` (Link list).
- **Behavior**: Toggles display logic. On mobile, it injects inline styles to create a full-width overlay.

### Scroll Animations (Intersection Observer)
- **Target Elements**: `.card`, `.featured-story`, `.player-card`, `.metric-box`.
- **Behavior**:
    1.  JS hides these elements initially (`opacity: 0`).
    2.  When scrolled into view (10% visibility), it adds the `.fade-in` class.
    3.  CSS handles the actual animation.
- **Usage**: To animate a new element types, simply add its class selector to the `const cards = querySelectorAll(...)` list.

### Stats Counter
- **Target**: Elements with class `.metric-value`.
- **Behavior**: Counts up from 0 to the target number when scrolled into view.
- **Formatting**: Automatically detects and preserves Prefix ($) and Suffix (%, +).

## 3. API & Functions

### `scrollGrid(amount)`
- **Purpose**: Horizontal scrolling for the Equipment Carousel.
- **Usage**: Called by the left/right navigation buttons in HTML.
- **Params**: `amount` (pixels). Positive for right, negative for left.

## 4. How to Extend
To add new features for a sub-page (e.g., specific logic for `contact.html`):

1.  **Check Existence**: Always wrap element selectors in `if (element)` checks. This prevents errors when the script runs on a page that doesn't have that element.
    ```javascript
    const myButton = document.querySelector('.my-btn');
    if (myButton) {
        myButton.addEventListener(...);
    }
    ```
2.  **Add to DOMContentLoaded**: Place new logic inside the main event listener.

## 5. Contact Form Handler
- **To Connect**: Replace the `alert()` code with an actual `fetch()` call to a backend API or form service like Formspree.

## 6. Header & Footer Components (`layout.js`)
To ensure consistency across pages without code duplication, the site uses Vanilla JS Web Components.

### Usage
Instead of copying the full HTML for the header and footer, simply use:
```html
<site-header></site-header>
... content ...
<site-footer></site-footer>
<!-- Make sure layout.js is linked -->
<script src="layout.js"></script>
```

### Components
- **`<site-header>`**: Renders the sticky navigation bar. Automatically highlights the active link based on the current URL filename.
- **`<site-footer>`**: Renders the site footer with links and social icons.

### Modifying Layout
To change a menu link or update the footer address, edit `layout.js` directly. The changes will propagate to all pages using these tags.

## 7. Contact Form Logic
Located in `script.js` (lines ~210+), this logic handles the dynamic category selection on the Contact Us page.
- **`fieldData` Object**: Contains the configuration (Title, Description, HTML Fields) for each category key (e.g., 'equipment', 'research').
- **`selectCategory(category, element)`**: Injects the HTML from `fieldData` into the DOM and triggers animations.
- **`resetSelection()`**: Hides the form and resets grid selection.
- **`handleFormSubmit(e)`**: Intercepts submission for demo purposes.
