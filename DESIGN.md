---
created: 2026-04-19T00:00:00Z
last_edited: 2026-04-19T00:00:00Z
---

# DESIGN.md — HomeView

HomeView is a self-hosted multi-stream video wall controller. The PWA remote runs primarily on phones and tablets in a dark, living-room environment. The visual language is cinematic and content-first — think Plex, Infuse, or a high-end home theater remote. Every design decision prioritizes glanceability, thumb-friendly touch targets, and minimal chrome so the content (live streams, video thumbnails) stays front and center.

---

## Section 1: Visual Theme & Atmosphere

### Design philosophy

- **Content-first.** UI recedes; video thumbnails, stream previews, and status indicators are the loudest elements on screen.
- **Cinematic dark.** Deep, cool-toned backgrounds evoke a theater environment. Surfaces use subtle blue-violet undertones rather than pure gray.
- **Calm confidence.** Interactions feel deliberate — smooth transitions, restrained animation, no flashy gradients. The system conveys that it is in control.
- **Touch-native.** All interactive elements are sized for thumbs (minimum 44px touch target). Spacing is generous on mobile, tighter on larger screens.

### Mood references

| Reference | What to borrow |
|-----------|---------------|
| Plex | Dark surfaces, content-card grid, glowing accent on active items |
| Infuse | Frosted overlays, cinematic blur behind modals, elegant typography |
| Apple TV Remote app | Bottom-sheet interactions, simple iconography, haptic-feeling button states |
| Sports bar monitor wall | Grid-of-screens mental model — each cell is a "screen" the user manages |

### Light mode

Light mode inverts the surface hierarchy (white base, light gray cards) while keeping the same teal accent and semantic palette. It exists for outdoor or bright-room use but is not the default. The atmosphere shifts from "theater" to "clean control panel."

---

## Section 2: Color Palette

### Dark mode

| Token | Hex | Role |
|-------|-----|------|
| `--color-bg-deep` | `#0A0A0F` | Page/app background, deepest layer |
| `--color-bg-surface` | `#141420` | Card backgrounds, main content areas |
| `--color-bg-elevated` | `#1E1E2E` | Modals, bottom sheets, dropdowns |
| `--color-bg-overlay` | `#28283C` | Tooltips, popovers, floating menus |
| `--color-border-subtle` | `#2A2A3E` | Dividers, card borders (low contrast) |
| `--color-border-default` | `#3A3A52` | Input borders, active card outlines |
| `--color-text-primary` | `#F0F0F5` | Headings, primary body text |
| `--color-text-secondary` | `#A0A0B8` | Descriptions, helper text, timestamps |
| `--color-text-muted` | `#6B6B82` | Placeholders, disabled labels |
| `--color-text-inverse` | `#0A0A0F` | Text on accent-colored backgrounds |

### Light mode

| Token | Hex | Role |
|-------|-----|------|
| `--color-bg-deep` | `#FFFFFF` | Page/app background |
| `--color-bg-surface` | `#F5F5F8` | Card backgrounds |
| `--color-bg-elevated` | `#EEEEF2` | Modals, bottom sheets |
| `--color-bg-overlay` | `#E4E4EA` | Tooltips, popovers |
| `--color-border-subtle` | `#E0E0E6` | Dividers |
| `--color-border-default` | `#C8C8D2` | Input borders |
| `--color-text-primary` | `#121218` | Headings, body text |
| `--color-text-secondary` | `#5A5A6E` | Descriptions, helper text |
| `--color-text-muted` | `#8A8A9E` | Placeholders |
| `--color-text-inverse` | `#F0F0F5` | Text on accent backgrounds |

### Accent — Teal/Cyan

| Token | Hex | Role |
|-------|-----|------|
| `--color-accent` | `#00C9C8` | Primary buttons, active indicators, links |
| `--color-accent-hover` | `#00E0DF` | Hover state for accent elements |
| `--color-accent-muted` | `#00C9C820` | 12% opacity — subtle backgrounds, selected card tint |
| `--color-accent-text` | `#0A0A0F` | Text rendered on top of `--color-accent` fill |

### Semantic colors

| Token | Hex | Dark bg variant (12%) | Role |
|-------|-----|----------------------|------|
| `--color-success` | `#34D399` | `#34D39920` | Stream running, connected, healthy |
| `--color-warning` | `#FBBF24` | `#FBBF2420` | Stream buffering, pairing expiring |
| `--color-error` | `#F87171` | `#F8717120` | Stream crashed, auth failed, errors |
| `--color-info` | `#00C9C8` | `#00C9C820` | Informational banners (reuses accent) |

### CSS custom properties (full set)

```css
:root {
  /* ---------- Accent ---------- */
  --color-accent: #00C9C8;
  --color-accent-hover: #00E0DF;
  --color-accent-muted: #00C9C820;
  --color-accent-text: #0A0A0F;

  /* ---------- Semantic ---------- */
  --color-success: #34D399;
  --color-success-muted: #34D39920;
  --color-warning: #FBBF24;
  --color-warning-muted: #FBBF2420;
  --color-error: #F87171;
  --color-error-hover: #EF4444;
  --color-error-muted: #F8717120;
  --color-info: #00C9C8;
  --color-info-muted: #00C9C820;
}

/* ---------- Dark mode (default) ---------- */
:root,
[data-theme="dark"] {
  --color-bg-deep: #0A0A0F;
  --color-bg-surface: #141420;
  --color-bg-elevated: #1E1E2E;
  --color-bg-overlay: #28283C;
  --color-border-subtle: #2A2A3E;
  --color-border-default: #3A3A52;
  --color-text-primary: #F0F0F5;
  --color-text-secondary: #A0A0B8;
  --color-text-muted: #6B6B82;
  --color-text-inverse: #0A0A0F;

  --shadow-low: 0 1px 3px rgba(0, 0, 0, 0.5), 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-mid: 0 4px 12px rgba(0, 0, 0, 0.55), 0 2px 4px rgba(0, 0, 0, 0.4);
  --shadow-high: 0 12px 32px rgba(0, 0, 0, 0.65), 0 4px 8px rgba(0, 0, 0, 0.4);
}

/* ---------- Light mode ---------- */
[data-theme="light"] {
  --color-bg-deep: #FFFFFF;
  --color-bg-surface: #F5F5F8;
  --color-bg-elevated: #EEEEF2;
  --color-bg-overlay: #E4E4EA;
  --color-border-subtle: #E0E0E6;
  --color-border-default: #C8C8D2;
  --color-text-primary: #121218;
  --color-text-secondary: #5A5A6E;
  --color-text-muted: #8A8A9E;
  --color-text-inverse: #F0F0F5;

  --shadow-low: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow-mid: 0 4px 12px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
  --shadow-high: 0 12px 32px rgba(0, 0, 0, 0.14), 0 4px 8px rgba(0, 0, 0, 0.06);
}
```

---

## Section 3: Typography

### Font stack

```css
--font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Helvetica, Arial, sans-serif, "Apple Color Emoji",
               "Segoe UI Emoji";
--font-mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas,
             "DejaVu Sans Mono", monospace;
```

### Type scale

| Token | Size (px) | Line height | Weight | Letter-spacing | Usage |
|-------|-----------|-------------|--------|----------------|-------|
| `--type-display` | 32 | 1.2 | 700 | -0.02em | Hero headings (e.g., layout name on full screen) |
| `--type-h1` | 24 | 1.3 | 700 | -0.01em | Page titles ("Layouts", "Sources") |
| `--type-h2` | 20 | 1.35 | 600 | -0.01em | Section headers, modal titles |
| `--type-h3` | 16 | 1.4 | 600 | 0 | Card titles, subsection labels |
| `--type-body-lg` | 16 | 1.5 | 400 | 0 | Prominent body text, descriptions |
| `--type-body` | 14 | 1.5 | 400 | 0 | Default body text |
| `--type-body-sm` | 13 | 1.45 | 400 | 0 | Secondary info, metadata |
| `--type-caption` | 12 | 1.4 | 400 | 0 | Timestamps, cell status badges |
| `--type-label` | 12 | 1.3 | 600 | 0.05em | Form labels, button text, uppercase tab labels |

### CSS custom properties

```css
:root {
  --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif, "Apple Color Emoji",
                 "Segoe UI Emoji";
  --font-mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas,
               "DejaVu Sans Mono", monospace;

  --type-display: 700 32px/1.2 var(--font-family);
  --type-h1: 700 24px/1.3 var(--font-family);
  --type-h2: 600 20px/1.35 var(--font-family);
  --type-h3: 600 16px/1.4 var(--font-family);
  --type-body-lg: 400 16px/1.5 var(--font-family);
  --type-body: 400 14px/1.5 var(--font-family);
  --type-body-sm: 400 13px/1.45 var(--font-family);
  --type-caption: 400 12px/1.4 var(--font-family);
  --type-label: 600 12px/1.3 var(--font-family);
}
```

### Usage rules

- **Headings** use `--color-text-primary`. Never color headings with accent unless they are interactive (links).
- **Body text** defaults to `--color-text-secondary` for descriptions, `--color-text-primary` for key content.
- **Labels** are always `--color-text-muted` with `text-transform: uppercase` and `letter-spacing: 0.05em`.
- **Monospace** is reserved for pairing codes, debug info, and error codes.

---

## Section 4: Component Library

### 4.1 Buttons

Four variants. All share: `border-radius: 8px`, `padding: 12px 20px`, `font: var(--type-label)`, `min-height: 44px`, `cursor: pointer`, `transition: all 150ms ease`.

#### Primary

```css
.btn-primary {
  background: var(--color-accent);
  color: var(--color-accent-text);
  border: none;
}
.btn-primary:hover {
  background: var(--color-accent-hover);
}
.btn-primary:active {
  background: var(--color-accent);
  transform: scale(0.97);
}
.btn-primary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.btn-primary:disabled {
  background: var(--color-bg-overlay);
  color: var(--color-text-muted);
  cursor: not-allowed;
}
```

#### Secondary

```css
.btn-secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}
.btn-secondary:hover {
  background: var(--color-bg-elevated);
  border-color: var(--color-text-secondary);
}
.btn-secondary:active {
  background: var(--color-bg-overlay);
  transform: scale(0.97);
}
.btn-secondary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.btn-secondary:disabled {
  border-color: var(--color-border-subtle);
  color: var(--color-text-muted);
  cursor: not-allowed;
}
```

#### Ghost

```css
.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
  border: none;
}
.btn-ghost:hover {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}
.btn-ghost:active {
  background: var(--color-bg-overlay);
}
.btn-ghost:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.btn-ghost:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}
```

#### Destructive

```css
.btn-destructive {
  background: var(--color-error);
  color: var(--color-text-inverse);
  border: none;
}
.btn-destructive:hover {
  background: var(--color-error-hover);
}
.btn-destructive:active {
  background: var(--color-error);
  transform: scale(0.97);
}
.btn-destructive:focus-visible {
  outline: 2px solid var(--color-error);
  outline-offset: 2px;
}
.btn-destructive:disabled {
  background: var(--color-bg-overlay);
  color: var(--color-text-muted);
  cursor: not-allowed;
}
```

### 4.2 CellCard

The primary UI unit. Represents one cell in the current layout. Displays stream status, source thumbnail/icon, and provides tap-to-assign interaction.

#### States

| State | Visual treatment |
|-------|-----------------|
| **Empty** | Dashed border (`var(--color-border-subtle)`), centered "+" icon in `--color-text-muted`, label "Tap to assign" |
| **Starting** | Solid border, pulsing accent glow, spinner icon, source name in `--color-text-secondary` |
| **Running** | Solid border with thin `--color-success` left accent bar (3px), thumbnail/favicon, source name in `--color-text-primary` |
| **Error** | Solid border with thin `--color-error` left accent bar (3px), error icon, retry button |
| **Audio active** | Running state + speaker icon badge with `--color-accent` fill in top-right corner |

#### Structure

```jsx
<div className="cell-card" data-status="running" data-audio-active="true">
  <div className="cell-card__status-bar" />
  <div className="cell-card__thumbnail">
    {/* stream preview or source icon */}
  </div>
  <div className="cell-card__info">
    <span className="cell-card__role">Hero</span>
    <span className="cell-card__source">ESPN</span>
  </div>
  <div className="cell-card__actions">
    <button className="btn-ghost cell-card__audio-toggle" aria-label="Set as audio source">
      {/* speaker icon */}
    </button>
    <button className="btn-ghost cell-card__clear" aria-label="Clear cell">
      {/* x icon */}
    </button>
  </div>
</div>
```

#### CSS

```css
.cell-card {
  position: relative;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
  padding: var(--space-12);
  display: flex;
  align-items: center;
  gap: var(--space-12);
  min-height: 72px;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease;
}
.cell-card:hover {
  border-color: var(--color-border-default);
  background: var(--color-bg-elevated);
}
.cell-card:active {
  transform: scale(0.98);
}
.cell-card[data-status="empty"] {
  border-style: dashed;
}
.cell-card__status-bar {
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 2px 2px 0;
}
.cell-card[data-status="running"] .cell-card__status-bar {
  background: var(--color-success);
}
.cell-card[data-status="error"] .cell-card__status-bar {
  background: var(--color-error);
}
```

### 4.3 SourcePickerModal

Displayed as a bottom sheet on mobile, centered modal on tablet/desktop. Lists available sources for assignment to a cell.

#### Structure

```jsx
<div className="modal-backdrop">
  <div className="bottom-sheet" role="dialog" aria-label="Choose a source">
    <div className="bottom-sheet__handle" />
    <header className="bottom-sheet__header">
      <h2>Choose Source</h2>
      <button className="btn-ghost" aria-label="Close">X</button>
    </header>
    <div className="bottom-sheet__body">
      <input className="input-search" type="search" placeholder="Search sources..." />
      <ul className="source-list">
        <li className="source-item">
          <img className="source-item__icon" src="..." alt="" />
          <span className="source-item__name">ESPN</span>
          <span className="source-item__url caption">espn.com/watch</span>
        </li>
        {/* more items */}
      </ul>
    </div>
  </div>
</div>
```

#### Key styles

```css
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-end;  /* bottom sheet on mobile */
  justify-content: center;
  z-index: 50;
}
.bottom-sheet {
  background: var(--color-bg-elevated);
  border-radius: 16px 16px 0 0;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: var(--space-16);
}
.bottom-sheet__handle {
  width: 36px;
  height: 4px;
  background: var(--color-border-default);
  border-radius: 2px;
  margin: 0 auto var(--space-12);
}
.source-item {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-12) var(--space-16);
  border-radius: 8px;
  cursor: pointer;
  transition: background 120ms ease;
}
.source-item:hover {
  background: var(--color-bg-overlay);
}
.source-item:active {
  background: var(--color-accent-muted);
}

/* Tablet/desktop: centered modal instead of bottom sheet */
@media (min-width: 768px) {
  .modal-backdrop {
    align-items: center;
  }
  .bottom-sheet {
    border-radius: 12px;
    max-width: 480px;
    max-height: 70vh;
  }
}
```

### 4.4 LayoutPickerScreen

Full-page or modal view showing available layouts as visual thumbnails. Each layout shows a miniature proportional grid preview.

```css
.layout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--space-16);
  padding: var(--space-16);
}
.layout-card {
  background: var(--color-bg-surface);
  border: 2px solid var(--color-border-subtle);
  border-radius: 12px;
  padding: var(--space-12);
  text-align: center;
  cursor: pointer;
  transition: border-color 150ms ease, transform 150ms ease;
}
.layout-card:hover {
  border-color: var(--color-border-default);
}
.layout-card[aria-selected="true"] {
  border-color: var(--color-accent);
  background: var(--color-accent-muted);
}
.layout-card:active {
  transform: scale(0.96);
}
.layout-card__preview {
  aspect-ratio: 16 / 9;
  background: var(--color-bg-deep);
  border-radius: 8px;
  margin-bottom: var(--space-8);
  overflow: hidden;
  display: grid;
  gap: 2px;
  padding: 2px;
  /* grid-template-* set dynamically per layout */
}
.layout-card__name {
  font: var(--type-caption);
  color: var(--color-text-secondary);
}
```

### 4.5 Text Inputs

```css
.input {
  width: 100%;
  padding: var(--space-12) var(--space-16);
  background: var(--color-bg-deep);
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  color: var(--color-text-primary);
  font: var(--type-body);
  transition: border-color 150ms ease, box-shadow 150ms ease;
  min-height: 44px;
}
.input::placeholder {
  color: var(--color-text-muted);
}
.input:hover {
  border-color: var(--color-text-secondary);
}
.input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-muted);
}
.input:disabled {
  background: var(--color-bg-surface);
  color: var(--color-text-muted);
  cursor: not-allowed;
}
.input--error {
  border-color: var(--color-error);
}
.input--error:focus {
  box-shadow: 0 0 0 3px var(--color-error-muted);
}
```

### 4.6 Pairing Code Display

The 6-digit pairing code uses monospace font at display size, with digit grouping for readability.

```css
.pairing-code {
  font-family: var(--font-mono);
  font-size: 48px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--color-accent);
  text-align: center;
  padding: var(--space-32) 0;
}
.pairing-code__digit-group {
  display: inline-block;
}
.pairing-code__separator {
  display: inline-block;
  width: var(--space-16);
}
```

### 4.7 Status Badge

Small pill indicating cell or connection status.

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  padding: 2px var(--space-8);
  border-radius: 999px;
  font: var(--type-caption);
  font-weight: 600;
}
.badge--success {
  background: var(--color-success-muted);
  color: var(--color-success);
}
.badge--warning {
  background: var(--color-warning-muted);
  color: var(--color-warning);
}
.badge--error {
  background: var(--color-error-muted);
  color: var(--color-error);
}
.badge--info {
  background: var(--color-info-muted);
  color: var(--color-info);
}
.badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
```

---

## Section 5: Layout & Spacing

### Spacing scale

Base unit: **4px**. All spacing derives from this scale.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-4` | 4px | Icon-to-label gaps, badge internal padding |
| `--space-8` | 8px | Tight element grouping, inline spacing |
| `--space-12` | 12px | Card internal padding, compact lists |
| `--space-16` | 16px | Default section padding, form field gaps |
| `--space-24` | 24px | Between content groups, mobile page padding |
| `--space-32` | 32px | Between major sections |
| `--space-48` | 48px | Page-level vertical breathing room |
| `--space-64` | 64px | Hero section padding, modal vertical margins |
| `--space-96` | 96px | Splash/pairing screen centering space |

### CSS custom properties

```css
:root {
  --space-4: 4px;
  --space-8: 8px;
  --space-12: 12px;
  --space-16: 16px;
  --space-24: 24px;
  --space-32: 32px;
  --space-48: 48px;
  --space-64: 64px;
  --space-96: 96px;
}
```

### Page structure

```
+-------------------------------------------+
|  Status bar (connection indicator)  24px  |
+-------------------------------------------+
|                                           |
|  Page padding: --space-16 (mobile)        |
|               --space-24 (tablet+)        |
|                                           |
|  +------+ +------+ +------+              |
|  | Cell | | Cell | | Cell |  gap: 12px   |
|  +------+ +------+ +------+              |
|                                           |
|  Section gap: --space-32                  |
|                                           |
|  [Actions row]          gap: 8px          |
|                                           |
+-------------------------------------------+
|  Bottom nav / action bar          56px    |
+-------------------------------------------+
```

### Grid patterns

```css
/* Cell card list — single column on mobile, multi on tablet+ */
.cell-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-12);
}
@media (min-width: 768px) {
  .cell-list {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 1024px) {
  .cell-list {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
}
```

### Corner radius

| Context | Radius | Usage |
|---------|--------|-------|
| Small elements | `8px` | Buttons, inputs, badges, list items |
| Cards | `12px` | CellCard, LayoutCard, source items |
| Modals/sheets | `16px` (top corners) | Bottom sheets, modals |
| Pill | `999px` | Status badges, toggle chips |

---

## Section 6: Elevation & Depth

Three elevation levels, each with dark and light mode shadow values.

| Level | Token | Dark mode | Light mode | Usage |
|-------|-------|-----------|------------|-------|
| **Low** | `--shadow-low` | `0 1px 3px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.4)` | `0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)` | Cards resting on surface, subtle lift |
| **Mid** | `--shadow-mid` | `0 4px 12px rgba(0,0,0,0.55), 0 2px 4px rgba(0,0,0,0.4)` | `0 4px 12px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)` | Dropdowns, bottom sheet resting |
| **High** | `--shadow-high` | `0 12px 32px rgba(0,0,0,0.65), 0 4px 8px rgba(0,0,0,0.4)` | `0 12px 32px rgba(0,0,0,0.14), 0 4px 8px rgba(0,0,0,0.06)` | Modals, popovers, dragging states |

### Dark mode depth strategy

In dark mode, elevation is conveyed primarily through **surface color stepping** (`bg-deep` < `bg-surface` < `bg-elevated` < `bg-overlay`), not shadows alone. Shadows reinforce the layer but the lighter surface is the dominant cue.

### Backdrop blur

Modals and bottom sheets use `backdrop-filter: blur(4px)` on their overlay to create depth separation without fully obscuring underlying content. The overlay color is `rgba(0, 0, 0, 0.6)` in dark mode, `rgba(0, 0, 0, 0.3)` in light mode.

---

## Section 7: Do's and Don'ts

### Colors

**Do:** Use semantic tokens for all colors.

```css
/* Correct */
.card { background: var(--color-bg-surface); }
.heading { color: var(--color-text-primary); }
```

**Don't:** Hard-code hex values in component styles.

```css
/* Wrong — breaks theme switching, impossible to maintain */
.card { background: #141420; }
.heading { color: #F0F0F5; }
```

### Typography

**Do:** Use the type scale tokens.

```css
/* Correct */
.modal-title { font: var(--type-h2); }
```

**Don't:** Invent ad-hoc font sizes.

```css
/* Wrong — 15px is not on the scale */
.modal-title { font-size: 15px; font-weight: 500; }
```

### Spacing

**Do:** Use spacing tokens from the 4px scale.

```jsx
// Correct
<div style={{ padding: 'var(--space-16)', gap: 'var(--space-12)' }}>
```

**Don't:** Use arbitrary pixel values or mix units.

```jsx
// Wrong — 10px and 18px are off-scale
<div style={{ padding: '10px', gap: '18px' }}>
```

### Touch targets

**Do:** Ensure all interactive elements meet 44px minimum.

```css
/* Correct */
.icon-button {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

**Don't:** Rely on icon size alone for the tap target.

```css
/* Wrong — 24px icon with no padding is too small to tap reliably */
.icon-button {
  width: 24px;
  height: 24px;
}
```

### Focus states

**Do:** Provide visible focus indicators for keyboard/screen-reader navigation.

```css
/* Correct */
.btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

**Don't:** Remove outlines without replacement.

```css
/* Wrong — makes keyboard navigation impossible */
.btn:focus { outline: none; }
```

### Component structure

**Do:** Use the data-attribute pattern for state-driven styling.

```jsx
// Correct
<div className="cell-card" data-status={cell.status}>
```

**Don't:** Generate dynamic class names for state.

```jsx
// Wrong — proliferates classes, harder to trace in devtools
<div className={`cell-card cell-card--${status} cell-card--${role} ${isActive ? 'active' : ''}`}>
```

### Elevation

**Do:** Match shadow level to the component's z-layer.

```css
/* Correct — modal uses highest elevation */
.modal { box-shadow: var(--shadow-high); }
.card { box-shadow: var(--shadow-low); }
```

**Don't:** Apply heavy shadows to resting elements.

```css
/* Wrong — cards don't need modal-level shadows */
.card { box-shadow: 0 12px 32px rgba(0,0,0,0.65); }
```

---

## Section 8: Responsive Design

### Breakpoints

| Name | Min-width | Target devices | Layout behavior |
|------|-----------|---------------|----------------|
| `mobile` | 0px | Phones (primary PWA target) | Single column, bottom sheet modals, bottom nav |
| `tablet` | 768px | Tablets, small laptops | 2-column cell grid, centered modals, expanded nav |
| `desktop` | 1024px | Laptops, monitors | Multi-column grid, sidebar navigation option |
| `wide` | 1440px | Large monitors | Max-width container (1200px), wider card grids |

### CSS

```css
/* Mobile-first — no media query needed for base styles */

@media (min-width: 768px) {
  /* tablet */
}

@media (min-width: 1024px) {
  /* desktop */
}

@media (min-width: 1440px) {
  /* wide */
}
```

### Behavior matrix

| Component | Mobile (< 768px) | Tablet (768px+) | Desktop (1024px+) |
|-----------|-------------------|-----------------|-------------------|
| **Cell list** | 1 column | 2 columns | auto-fill, min 280px |
| **Source picker** | Bottom sheet, full width | Centered modal, 480px max | Centered modal, 480px max |
| **Layout picker** | 2-col grid of cards | 3-col grid | auto-fill, min 140px |
| **Navigation** | Bottom tab bar (56px) | Bottom tab bar | Optional sidebar (240px) |
| **Pairing code** | Centered, full-width card | Centered, 400px max | Centered, 400px max |
| **Page padding** | 16px | 24px | 24px |
| **Modal overlay** | Aligned to bottom | Centered vertically | Centered vertically |

### Safe areas

```css
/* Respect notch/home indicator on modern phones */
.app-shell {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

.bottom-nav {
  padding-bottom: calc(var(--space-8) + env(safe-area-inset-bottom));
}
```

### Touch considerations

- All tap targets: minimum 44x44px
- Buttons spaced at least 8px apart to prevent mis-taps
- Swipe gestures reserved for bottom sheet dismiss (swipe down) and potential future cell reordering
- No hover-only interactions — everything accessible via tap

---

## Section 9: Agent Prompt Guide

### Quick-reference token table

| Category | Token | Value / Example |
|----------|-------|-----------------|
| **Background** | `--color-bg-deep` | `#0A0A0F` (dark) / `#FFFFFF` (light) |
| **Background** | `--color-bg-surface` | `#141420` (dark) / `#F5F5F8` (light) |
| **Background** | `--color-bg-elevated` | `#1E1E2E` (dark) / `#EEEEF2` (light) |
| **Text** | `--color-text-primary` | `#F0F0F5` (dark) / `#121218` (light) |
| **Text** | `--color-text-secondary` | `#A0A0B8` (dark) / `#5A5A6E` (light) |
| **Accent** | `--color-accent` | `#00C9C8` |
| **Accent** | `--color-accent-hover` | `#00E0DF` |
| **Accent** | `--color-accent-muted` | `#00C9C820` (12% opacity) |
| **Semantic** | `--color-success` | `#34D399` |
| **Semantic** | `--color-warning` | `#FBBF24` |
| **Semantic** | `--color-error` | `#F87171` |
| **Border** | `--color-border-subtle` | `#2A2A3E` (dark) / `#E0E0E6` (light) |
| **Border** | `--color-border-default` | `#3A3A52` (dark) / `#C8C8D2` (light) |
| **Shadow** | `--shadow-low` | Cards |
| **Shadow** | `--shadow-mid` | Dropdowns, sheets |
| **Shadow** | `--shadow-high` | Modals |
| **Spacing** | `--space-{4,8,12,16,24,32,48,64,96}` | 4px base unit |
| **Type** | `--type-h1` | `700 24px/1.3` |
| **Type** | `--type-body` | `400 14px/1.5` |
| **Type** | `--type-caption` | `400 12px/1.4` |
| **Radius** | Buttons/inputs | `8px` |
| **Radius** | Cards | `12px` |
| **Radius** | Modals | `16px` top corners |
| **Font** | `--font-family` | System stack (no web fonts) |
| **Breakpoint** | `tablet` | `min-width: 768px` |
| **Breakpoint** | `desktop` | `min-width: 1024px` |

### Example prompts with correct token usage

**Prompt 1: "Build the CellCard component"**

> Build a CellCard React component. Background is `--color-bg-surface`, border `1px solid --color-border-subtle`, `border-radius: 12px`, padding `--space-12`. On hover, background shifts to `--color-bg-elevated`. The left status bar is 3px wide: `--color-success` when running, `--color-error` on error. Role label uses `--type-caption` in `--color-text-muted` uppercase. Source name uses `--type-h3` in `--color-text-primary`. Minimum height 72px, minimum touch target 44px on all interactive sub-elements. Ghost buttons for actions. Use `data-status` attribute for state styling.

**Prompt 2: "Build the source picker bottom sheet"**

> Build a SourcePickerModal as a bottom sheet on mobile (< 768px), centered modal on tablet+. Backdrop uses `rgba(0,0,0,0.6)` with `backdrop-filter: blur(4px)`. Sheet background is `--color-bg-elevated`, top corners `border-radius: 16px`. Drag handle: 36px wide, 4px tall, `--color-border-default`. Search input uses the `.input` pattern: `--color-bg-deep` background, `--color-border-default` border, `8px` radius, accent focus ring. Source list items: `--space-12` vertical padding, hover background `--color-bg-overlay`, active background `--color-accent-muted`. At 768px+, switch to centered modal with `max-width: 480px` and `border-radius: 12px`.

**Prompt 3: "Add a status badge to the header"**

> Add a connection status badge to the app header. Use the `.badge` pattern: pill shape (`border-radius: 999px`), `--type-caption` at `font-weight: 600`. When connected: `--color-success-muted` background, `--color-success` text, 6px dot via `currentColor`. When disconnected: swap to `--color-error-muted` / `--color-error`. Padding `2px --space-8`. Place it in the header bar with `--space-8` gap from adjacent elements.
