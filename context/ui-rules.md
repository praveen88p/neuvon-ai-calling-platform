# UI Rules

Concise rules for building Neuvon AI Calling Platform UI. These rules cover the most important patterns and constraints to keep the UI consistent without over-specifying every detail.

---

## Font

Load Inter via Google Fonts link in `index.html`:

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Set `font-family: 'Inter', sans-serif` on the body via Tailwind's `font-sans` in `tailwind.config.ts`. Never use system fonts as the primary font.

---

## Layout

- Sidebar navigation on the left — collapsible to icon-only mode
- Main content area: `flex-1 overflow-auto p-6` (or `p-8` for primary pages)
- Gap between page sections: `space-y-8`
- No top navbar — sidebar handles all navigation
- All protected pages render inside `DashboardLayout` which wraps `SidebarProvider` + `AppSidebar` + `<main>`

---

## Sidebar

Nine primary nav items: Dashboard, Campaigns, Upload Leads, Live Calls, Call History, Analytics, Appointments, Settings, Phone Numbers.

- Active item: sidebar-accent background, primary text color
- Inactive item: sidebar-foreground text, no background
- Brand header: warm brown (`bg-primary`) logo icon + "Neuvon" text + tagline
- Footer: organization name, user email, collapse toggle, logout button
- Border: `border-sidebar-border`
- Width expanded: `w-64`, collapsed: `w-16`

---

## Cards

Every content section lives in a shadcn/ui `<Card>`.

```
background: bg-card (#fcfcfc)
border: border border-border (#d8d8d8)
border-radius: rounded-lg (var(--radius) = 0.5rem)
padding: p-6
shadow: shadow-sm
```

Never use colored card backgrounds — always `bg-card`. Color goes inside cards via badges, icons, and text, never on the card surface itself.

---

## Typography Hierarchy

Three levels used consistently throughout:

**Page titles / stat numbers**

```
font-size: 30px (text-3xl)
font-weight: 700 (font-bold)
color: text-foreground (#202020)
```

**Section headings / card titles**

```
font-size: 16px (text-base) to 18px (text-lg)
font-weight: 600 (font-semibold)
color: text-foreground (#202020)
```

**Secondary / muted text** — labels, timestamps, subtitles

```
font-size: 12px (text-xs) to 14px (text-sm)
font-weight: 400 (font-normal) to 500 (font-medium)
color: text-muted-foreground (#646464)
```

---

## Status Badges

All status badges use `rounded-full` (pill shape).

```
padding: px-2.5 py-0.5
font-size: text-xs (12px)
font-weight: font-medium (500)
```

| Status     | Background              | Text Color                 |
| ---------- | ----------------------- | -------------------------- |
| Live       | `bg-green-100`          | `text-green-700`           |
| Completed  | `bg-primary/10`         | `text-primary`             |
| Paused     | `bg-secondary`          | `text-secondary-foreground`|
| Failed     | `bg-destructive/10`     | `text-destructive`         |
| Pending    | `bg-muted`              | `text-muted-foreground`    |

Live status includes a pulsing dot animation (`animate-pulse`) before the text.

---

## Buttons

**Primary button:**

```
background: bg-primary (#644a40)
color: text-primary-foreground (#ffffff)
border-radius: rounded-md
padding: px-4 py-2
font-weight: font-medium
hover: opacity-90
```

**Outline button:**

```
background: bg-card (#fcfcfc)
border: border border-border (#d8d8d8)
color: text-foreground (#202020)
border-radius: rounded-md
padding: px-4 py-2
hover: bg-accent
```

**Ghost button:**

```
background: transparent
color: text-muted-foreground
hover: bg-accent
border-radius: rounded-md
```

---

## Form Inputs

```
background: bg-card (#fcfcfc)
border: border border-input (#d8d8d8)
border-radius: rounded-md
padding: px-3 py-2
font-size: text-sm (14px)
color: text-foreground (#202020)
placeholder: text-muted-foreground (#646464)
focus: ring-2 ring-ring (#644a40) border-ring
```

---

## Table (Call History / Campaign Lists)

- No alternating row colors — card background rows, separated by border
- Row border: `border-b border-border` between rows
- Column headers: `text-xs font-medium uppercase text-muted-foreground`
- Row text: `text-sm text-foreground`
- Hover state: `hover:bg-accent/50`

---

## KPI Cards

Used on Dashboard for key metrics (Calls Today, Contact Rate, Qualified Leads, Appointments).

```
Icon container: h-12 w-12 rounded-lg bg-primary/10
Icon: h-6 w-6 text-primary
Title: text-sm font-medium text-muted-foreground
Value: text-3xl font-bold text-foreground
Change badge: text-xs font-medium, green for positive / destructive for negative
```

---

## Progress Bars

Used in campaign cards and campaign details.

```
Track: bg-muted (#efefef)
Fill: bg-primary (#644a40)
Height: h-2
Border-radius: rounded-full
```

---

## Charts

All charts use Recharts. Colors reference CSS variables via `var(--chart-N)` — never hardcoded hex in chart configs.

| Element          | Value                          |
| ---------------- | ------------------------------ |
| Grid lines       | `1px dashed var(--border)`     |
| Axis labels      | `var(--muted-foreground)` 12px |
| Tooltip bg       | `var(--card)`                  |
| Tooltip border   | `1px solid var(--border)`      |
| Tooltip radius   | `8px`                          |
| Bar corners      | `radius={[4, 4, 0, 0]}`       |

---

## Empty States

Every section that can be empty must have an empty state. Keep it minimal:

- Short descriptive text in `text-muted-foreground`
- Optional Lucide icon above text in `text-muted-foreground/50`
- CTA button if there's a logical next action (e.g., "Upload Leads" on empty campaigns)

---

## Loading States

- Skeleton placeholders for KPI cards: `animate-pulse bg-muted rounded`
- Spinner for full-page loads: `Loader2` icon from Lucide with `animate-spin text-primary`
- Text hint: `text-sm text-muted-foreground` below spinner

---

## Login / Register (Auth Pages)

Auth pages use a warm dark gradient background instead of the dashboard layout:

```
background: bg-gradient-to-br from-[#3d2e28] via-[#2a1f1a] to-[#1a1210]
```

Card style on auth pages: `bg-card/80 backdrop-blur border-border`
All text on auth pages uses `text-foreground` and `text-muted-foreground` — never raw slate classes.

---

## Tailwind v3 Notes

This project uses **Tailwind CSS v3.4** with `tailwind.config.ts`. Color tokens are defined as CSS custom properties in `src/index.css` and mapped in `tailwind.config.ts`. No `@theme` directive — that's Tailwind v4 only.

---

## Do Nots

- Never use Tailwind's built-in color classes (`bg-brown-500`, `text-gray-600`, `bg-slate-900`) — use project tokens only
- Never define colors in `tailwind.config.ts` values directly — always reference CSS variables
- Never add gradients to card backgrounds (only auth pages use gradients)
- Never use more than one font weight in a single UI element
- Never show raw error messages to users — always show human readable text
- Never stack more than 2 levels of border radius inside each other
- Never use `position: fixed` for UI elements other than modals/dialogs
- Never use `hsl()` wrapper around CSS variables — variables store hex values directly
- Never use `from-slate-*` or `via-slate-*` on protected dashboard pages — only on auth pages
