# NAU Nano - CSS Developer Guide

This document provides a comprehensive guide to the **CSS Design System** used in the NAU Nano website. The system follows a **Mobile-First, Utility-Enhanced Component** architecture.

## 1. Core Architecture
- **File**: `style.css`
- **Methodology**: The CSS is structured into layers:
    1.  **Variables/Tokens** (Root)
    2.  **Reset & Base Styles**
    3.  **Utilities** (Text, Spacing, Layout)
    4.  **Components** (Buttons, Cards, Nav)
    5.  **Layout Sections** (Hero, Footer)

## 2. Design Tokens (CSS Variables)
Always use these variables instead of hardcodding values to ensure consistency.

### Colors
| Variable | Value | Usage |
| :--- | :--- | :--- |
| `--nau-blue` | `#002454` | Primary brand color, headers, buttons |
| `--nau-gold` | `#FAC01A` | Accents, active states, buttons |
| `--white` | `#ffffff` | Backgrounds, text on dark |
| `--gray-50` | `#f8f9fa` | Light backgrounds for sections |
| `--gray-600` | `#6c757d` | Muted text, captions |

### Spacing
| Variable | Value | Usage |
| :--- | :--- | :--- |
| `--space-sm` | `8px` | Gap between small elements |
| `--space-md` | `16px` | Standard padding/margin |
| `--space-lg` | `24px` | Section sub-groups |
| `--space-3xl` | `64px` | Section padding |

## 3. Layout Utilities
### Container
- `.container`: Centered container with max-width 1400px.
- `.section-padding`: Standard top/bottom padding (`--space-4xl`).

### Grid System
The site uses a responsive grid system.
- `.grid`: Activates grid display.
- `.grid-2`: 2 columns (stacks on mobile).
- `.grid-3`: 3 columns (stacks on mobile).
- `.grid-4`: 4 columns (2 on tablet, 1 on mobile).
- `.gap-xl`: Adds extra large gap between items.

### Flex Utilities
- `.d-flex`: `display: flex`
- `.align-center`: `align-items: center`
- `.justify-between`: `justify-content: space-between`
- `.flex-col`: `flex-direction: column`

## 4. Components

### Buttons
Mix and match classes to create buttons.
- Base: `.btn`
- **Primary**: `.btn-primary` (Gold background, Blue text)
- **Secondary**: `.btn-secondary` (Blue background, White text)
- **Outline**: `.btn-outline` (Transparent, White border)
- **Small**: `.btn-sm` (Smaller padding, pill shape)

**Example:**
```html
<a href="#" class="btn btn-primary">Book Now</a>
<div class="btn btn-sm btn-outline">Learn More</div>
```

### Cards
Standard usage for content grouping.
```html
<div class="card">
    <div class="card-img-top">
        <img src="..." alt="...">
    </div>
    <div class="card-body">
        <h3 class="card-title">Title</h3>
        <p class="card-text">Description...</p>
    </div>
</div>
```

### Badges / Tags
Use for status or categories.
- `.tag`: Base tag class (Gold background).
- Wrappers: `.tag.blue`, `.tag.green`, `.tag.red`.
- `.status-badge`: For availability status (`.available`, `.limited`).

### Site Header
The main navigation component.
- **Base**: `.site-header` (Sticky, Glassmorphism).
- **White Background**: Uses `rgba(255, 255, 255, 0.95)` for high contrast.
- **Shadow**: `box-shadow` added for depth against white pages.
- **Gradient Border**: Aesthetic bottom border (Blue -> Gold) via `::after`.
- **Scrolled State**: `.scrolled` class adds transparency effects (handled by JS).

## 5. Animations
The `fade-in` class is available for scroll animations.
- Add `.fade-in` to any element to make it fade up upon scrolling (handled by JS Observer).
- Default opacity should be handled by the JS to avoid accessibility issues if JS fails.

## 6. How to Extend
1.  **New Page**: Copy the basic HTML structure (Head, Navbar, Footer).
2.  **New Section**: Create a `<section class="section-padding">`.
3.  **New Styles**: Add new specific styles at the bottom of `style.css` if they cannot be composed using existing utilities.
