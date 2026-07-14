# UI Tokens

Design tokens for Neuvon AI Calling Platform. All colors, typography, spacing and component values defined for consistent use across the codebase. Use these exact values throughout — never hardcode colors or use raw Tailwind color classes in components.

---

## How to Use

This project uses **Tailwind CSS v3** with **shadcn/ui**. All design tokens are defined as CSS custom properties in `src/index.css` and mapped to Tailwind utilities via `tailwind.config.ts`.

Tailwind config maps CSS variables to utility classes:

- `--primary` → `bg-primary`, `text-primary`, `border-primary`
- `--muted` → `bg-muted`, `text-muted-foreground`
- `--card` → `bg-card`, `text-card-foreground`

```tsx
// Correct — uses Tailwind utility classes from config
className="bg-background text-foreground border-border"

// Correct — references CSS variable directly (rare, for charts/SVG)
style={{ color: 'var(--primary)' }}

// Never — hardcoded hex values
className="bg-[#644a40] text-[#202020]"

// Never — raw Tailwind color classes
className="bg-brown-700 text-gray-600"
```

---

## src/index.css — Complete Token Definition

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --card: #fcfcfc;
    --ring: #644a40;
    --input: #d8d8d8;
    --muted: #efefef;
    --accent: #e8e8e8;
    --border: #d8d8d8;
    --radius: 0.5rem;
    --chart-1: #644a40;
    --chart-2: #ffdfb5;
    --chart-3: #e8e8e8;
    --chart-4: #ffe6c4;
    --chart-5: #66493e;
    --popover: #fcfcfc;
    --primary: #644a40;
    --sidebar: #fbfbfb;
    --secondary: #ffdfb5;
    --background: #f9f9f9;
    --foreground: #202020;
    --destructive: #e54d2e;
    --sidebar-ring: #b5b5b5;
    --sidebar-accent: #f7f7f7;
    --sidebar-border: #ebebeb;
    --card-foreground: #202020;
    --sidebar-primary: #343434;
    --muted-foreground: #646464;
    --accent-foreground: #202020;
    --popover-foreground: #202020;
    --primary-foreground: #ffffff;
    --sidebar-foreground: #252525;
    --secondary-foreground: #582d1d;
    --destructive-foreground: #ffffff;
    --sidebar-accent-foreground: #343434;
    --sidebar-primary-foreground: #fbfbfb;

    /* Semantic status colors */
    --success: #16a34a;
    --success-foreground: #ffffff;
    --warning: #f59e0b;
    --warning-foreground: #ffffff;
  }

  .dark {
    --card: #191919;
    --ring: #ffe0c2;
    --input: #484848;
    --muted: #222222;
    --accent: #2a2a2a;
    --border: #201e18;
    --chart-1: #ffe0c2;
    --chart-2: #393028;
    --chart-3: #2a2a2a;
    --chart-4: #42382e;
    --chart-5: #ffe0c1;
    --popover: #191919;
    --primary: #ffe0c2;
    --sidebar: #18181b;
    --secondary: #393028;
    --background: #111111;
    --foreground: #eeeeee;
    --destructive: #e54d2e;
    --sidebar-ring: #d4d4d8;
    --sidebar-accent: #27272a;
    --sidebar-border: #27272a;
    --card-foreground: #eeeeee;
    --sidebar-primary: #1d4ed8;
    --muted-foreground: #b4b4b4;
    --accent-foreground: #eeeeee;
    --popover-foreground: #eeeeee;
    --primary-foreground: #081a1b;
    --sidebar-foreground: #f4f4f5;
    --secondary-foreground: #ffe0c2;
    --destructive-foreground: #ffffff;
    --sidebar-accent-foreground: #f4f4f5;
    --sidebar-primary-foreground: #ffffff;

    --success: #22c55e;
    --success-foreground: #ffffff;
    --warning: #f59e0b;
    --warning-foreground: #ffffff;
  }
}
```

---

## Color Usage Guide

### Page Layout

| Element              | Token                | Hex (Light)  |
| -------------------- | -------------------- | ------------ |
| Page background      | `bg-background`      | `#f9f9f9`    |
| Card / surface       | `bg-card`            | `#fcfcfc`    |
| Muted section        | `bg-muted`           | `#efefef`    |
| Accent surface       | `bg-accent`          | `#e8e8e8`    |
| Default border       | `border-border`      | `#d8d8d8`    |

### Typography

| Element                | Token                    | Hex (Light)  |
| ---------------------- | ------------------------ | ------------ |
| Headings, primary text | `text-foreground`        | `#202020`    |
| Card text              | `text-card-foreground`   | `#202020`    |
| Secondary / muted text | `text-muted-foreground`  | `#646464`    |
| Accent text            | `text-accent-foreground` | `#202020`    |

### Primary (Warm Brown)

Used for: primary buttons, sidebar active items, focus rings, brand accents, KPI icons

| Element               | Token                    | Hex (Light)  |
| --------------------- | ------------------------ | ------------ |
| Button background     | `bg-primary`             | `#644a40`    |
| Button text           | `text-primary-foreground` | `#ffffff`   |
| Focus ring            | `ring-ring`              | `#644a40`    |

### Secondary (Warm Amber)

Used for: secondary badges, chart accents, subtle highlights

| Element               | Token                       | Hex (Light)  |
| --------------------- | --------------------------- | ------------ |
| Badge background      | `bg-secondary`              | `#ffdfb5`    |
| Badge text            | `text-secondary-foreground`  | `#582d1d`   |

### Status Colors

| Status     | Token / Variable          | Color       |
| ---------- | ------------------------- | ----------- |
| Success    | `--success`               | `#16a34a`   |
| Warning    | `--warning`               | `#f59e0b`   |
| Destructive| `bg-destructive`          | `#e54d2e`   |
| Live       | green dot animation       | `#16a34a`   |
| Completed  | `bg-primary`              | `#644a40`   |
| Failed     | `bg-destructive`          | `#e54d2e`   |
| Paused     | `bg-secondary`            | `#ffdfb5`   |
| Pending    | `bg-muted`                | `#efefef`   |

### Sidebar

| Element              | Token                          | Hex (Light)  |
| -------------------- | ------------------------------ | ------------ |
| Sidebar background   | `bg-sidebar`                   | `#fbfbfb`    |
| Sidebar text         | `text-sidebar-foreground`      | `#252525`    |
| Sidebar active item  | `bg-sidebar-accent`            | `#f7f7f7`    |
| Sidebar border       | `border-sidebar-border`        | `#ebebeb`    |

### Chart Colors

| Chart Element | Token       | Hex (Light)  | Usage                        |
| ------------- | ----------- | ------------ | ---------------------------- |
| Chart 1       | `--chart-1` | `#644a40`    | Primary metric / bar fills   |
| Chart 2       | `--chart-2` | `#ffdfb5`    | Secondary metric             |
| Chart 3       | `--chart-3` | `#e8e8e8`    | Tertiary / grid background   |
| Chart 4       | `--chart-4` | `#ffe6c4`    | Quaternary accent            |
| Chart 5       | `--chart-5` | `#66493e`    | Dark accent / alternate bars |

---

## Typography

Font family: **Inter** — load via Google Fonts link in `index.html`.

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

| Element              | Size  | Weight | Line height | Color token            |
| -------------------- | ----- | ------ | ----------- | ---------------------- |
| Page title           | 30px  | 700    | 36px        | `text-foreground`      |
| Stat number (KPI)    | 30px  | 700    | 36px        | `text-foreground`      |
| Section heading      | 18px  | 600    | 28px        | `text-foreground`      |
| Card title           | 16px  | 600    | 24px        | `text-foreground`      |
| Nav item (active)    | 14px  | 500    | 20px        | `text-primary`         |
| Nav item (inactive)  | 14px  | 400    | 20px        | `text-muted-foreground`|
| Body text            | 14px  | 400    | 20px        | `text-foreground`      |
| Label / secondary    | 14px  | 500    | 20px        | `text-muted-foreground`|
| Badge text           | 12px  | 500    | 16px        | varies by badge type   |
| Timestamp / muted    | 12px  | 400    | 16px        | `text-muted-foreground`|
| Chart axis labels    | 12px  | 400    | 15px        | `text-muted-foreground`|

---

## Spacing

| Token       | Value      | Usage                    |
| ----------- | ---------- | ------------------------ |
| `gap-1`     | 4px        | Tight inline gaps        |
| `gap-2`     | 8px        | Badge and tag gaps       |
| `gap-3`     | 12px       | Form field gaps          |
| `gap-4`     | 16px       | Section internal gaps    |
| `gap-6`     | 24px       | Between sections         |
| `gap-8`     | 32px       | Page section gaps        |
| `p-4`       | 16px       | Card padding (compact)   |
| `p-6`       | 24px       | Card padding (standard)  |
| `p-8`       | 32px       | Page content padding     |
| `px-4 py-2` | 16px / 8px | Button padding           |
| `px-3 py-1` | 12px / 4px | Badge padding            |

---

## Component Tokens

### Cards

```
background: bg-card
border: border border-border
border-radius: rounded-lg (var(--radius))
padding: p-6
shadow: shadow-sm
```

### Buttons

**Primary:**

```
background: bg-primary (#644a40)
text: text-primary-foreground (#ffffff)
border-radius: rounded-md
padding: px-4 py-2
font-weight: font-medium
hover: opacity-90
```

**Secondary / Outline:**

```
background: bg-card
border: border border-border
text: text-foreground
border-radius: rounded-md
padding: px-4 py-2
hover: bg-accent
```

**Ghost:**

```
background: transparent
text: text-muted-foreground
hover: bg-accent
border-radius: rounded-md
```

### Input Fields

```
background: bg-card
border: border border-input (#d8d8d8)
border-radius: rounded-md
padding: px-3 py-2
text: text-foreground
placeholder: text-muted-foreground
focus: ring-2 ring-ring (#644a40)
```

### Status Badges

```
border-radius: rounded-full (pill shape)
padding: px-2.5 py-0.5
font-size: text-xs
font-weight: font-medium
```

| Status     | Background               | Text                     |
| ---------- | ------------------------ | ------------------------ |
| Live       | `bg-green-100`           | `text-green-700`         |
| Completed  | `bg-primary/10`          | `text-primary`           |
| Paused     | `bg-secondary`           | `text-secondary-foreground` |
| Failed     | `bg-destructive/10`      | `text-destructive`       |
| Pending    | `bg-muted`               | `text-muted-foreground`  |

### KPI Cards

```
Card background: bg-card
Icon container: h-12 w-12 rounded-lg bg-primary/10
Icon: h-6 w-6 text-primary
Title: text-sm font-medium text-muted-foreground
Value: text-3xl font-bold text-foreground
Change text (positive): text-green-600
Change text (negative): text-destructive
```

### Trend Badges (KPI cards)

```
background: bg-green-50 (positive) or bg-red-50 (negative)
text: text-green-700 (positive) or text-destructive (negative)
border-radius: rounded-sm
padding: px-2 py-0.5
font-size: text-xs
font-weight: font-medium
```

### Progress Bars

```
background track: bg-muted
fill: bg-primary
height: h-2
border-radius: rounded-full
```

### Dashboard Chart Colors

| Chart                           | Color Token                |
| ------------------------------- | -------------------------- |
| Contact Rate bars               | `--chart-1` (#644a40)     |
| Qualification Rate bars         | `--chart-2` (#ffdfb5)     |
| Appointment Rate bars           | `--chart-3` (#e8e8e8)     |
| Pie chart segments              | cycle through chart-1 to 5 |
| Lollipop dot                    | `--primary` (#644a40)     |
| Cost badge background           | `--muted` (#efefef)       |
| Chart grid lines                | `1px dashed var(--border)` |
| Chart axis labels               | `--muted-foreground`       |
| Tooltip background              | `bg-card`                  |
| Tooltip border                  | `border-border`            |

### Sidebar / Logo

```
Logo container: h-9 w-9 rounded-lg bg-primary
Logo icon: h-4 w-4 text-primary-foreground
Brand text: text-sm font-semibold text-sidebar-foreground
Tagline: text-[11px] text-muted-foreground
```

---

## Invariants

- Never use hex values directly in components — always use CSS variables via Tailwind tokens
- Font is Inter — always load from Google Fonts, never use a fallback system font as primary
- Never use raw Tailwind color classes like `bg-brown-500` or `text-gray-600` — use project tokens only
- `--primary` (#644a40) is the brand brown — never use Tailwind's built-in brown/amber scale
- `--secondary` (#ffdfb5) is the warm amber — never use Tailwind's built-in amber/yellow scale
- All borders default to `--border` (#d8d8d8) — never use `border-gray-*`
- Chart colors always use `--chart-1` through `--chart-5` — never hardcoded colors
- Status colors must use the status badge table above — never ad-hoc colors for statuses
