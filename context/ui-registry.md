# UI Registry

Living document. Updated after every component is built. Read this before building any new component — match existing patterns exactly before inventing new ones.

---

## How to Use

Before building any component:

1. Check if a similar component already exists here
2. If yes — match its exact classes and patterns
3. If no — build it following ui-rules.md and ui-tokens.md, then add it here

After building any component — update this file with the component name, file path, and key classes used.

---

## Layout Components

### DashboardLayout
**File:** `src/components/DashboardLayout.tsx`
**Description:** Wraps all protected pages with sidebar + main content area.
**Key classes:** `flex min-h-screen w-full bg-background`
**Main area:** `flex-1 overflow-auto p-6`
**Dependencies:** `SidebarProvider`, `AppSidebar`

### AppSidebar
**File:** `src/components/AppSidebar.tsx`
**Description:** Left sidebar with navigation, brand header, and user footer.
**Key classes:** Expanded `w-64`, collapsed `w-16`, `collapsible="icon"`
**Brand icon:** `bg-primary rounded-lg h-9 w-9`, icon `text-primary-foreground`
**Active nav item:** `isActive` prop on `SidebarMenuButton`
**Footer:** org name, email, collapse trigger, logout button

### ProtectedRoute
**File:** `src/components/ProtectedRoute.tsx`
**Description:** Auth guard — redirects to `/login` if not authenticated.

---

## Data Display Components

### KPICard
**File:** `src/components/KPICard.tsx`
**Description:** Stat card for dashboard KPI metrics.
**Props:** `title`, `value`, `change`, `changeType`, `icon`
**Key classes:**
- Container: `<Card>` → `<CardContent className="p-6">`
- Layout: `flex items-start justify-between`
- Title: `text-sm font-medium text-muted-foreground`
- Value: `text-3xl font-bold text-foreground`
- Change: dynamic color via `changeType` (`text-success` / `text-destructive` / `text-muted-foreground`)
- Icon box: `h-12 w-12 rounded-lg bg-primary/10`, icon `h-6 w-6 text-primary`

### StatusBadge
**File:** `src/components/StatusBadge.tsx`
**Description:** Pill badge for campaign/call status.
**Props:** `status` (live | completed | paused | pending | failed)
**Key classes:** `rounded-full px-2.5 py-0.5 text-xs font-medium`
**Status colors:** See ui-tokens.md → Status Badges table

---

## Navigation Components

### NavLink
**File:** `src/components/NavLink.tsx`
**Description:** Wrapper around React Router's `NavLink` with active state styling.

---

## shadcn/ui Primitives

All located in `src/components/ui/`. These are standard shadcn/ui components — do not modify their internals unless absolutely necessary. Override styles via className props at the usage site.

**Commonly used:**
- `button.tsx` — Primary, outline, ghost, destructive variants
- `card.tsx` — Card, CardHeader, CardTitle, CardContent, CardFooter
- `input.tsx` — Text input with border-input styling
- `label.tsx` — Form labels
- `badge.tsx` — Generic badge component
- `progress.tsx` — Progress bar (campaign progress)
- `select.tsx` — Dropdown select
- `table.tsx` — Data table (call history, campaigns)
- `tabs.tsx` — Tab navigation (settings, analytics)
- `dialog.tsx` — Modal dialogs
- `alert.tsx` — Inline alerts
- `skeleton.tsx` — Loading placeholder
- `sidebar.tsx` — Full sidebar system (SidebarProvider, Sidebar, SidebarMenu, etc.)
- `toast.tsx` + `toaster.tsx` + `sonner.tsx` — Toast notifications

---

## Chart Components

### Analytics Charts (inline in pages)
**File:** `src/pages/Dashboard.tsx`, `src/pages/Analytics.tsx`
**Library:** Recharts
**Key patterns:**
- Chart colors: `var(--chart-1)` through `var(--chart-5)` — never hardcoded hex
- Tooltip: `backgroundColor: "var(--card)"`, `border: "1px solid var(--border)"`, `borderRadius: "8px"`
- Grid: `stroke="var(--border)"`
- Axis: `stroke="var(--muted-foreground)"`
- Bar radius: `radius={[4, 4, 0, 0]}`

---

## Page Patterns

### Standard Page Header
Used on every protected page:
```tsx
<div className="flex items-center justify-between">
  <div>
    <h1 className="text-3xl font-bold text-foreground">Page Title</h1>
    <p className="text-muted-foreground">Short description text</p>
  </div>
  <div className="flex gap-3">
    {/* Action buttons */}
  </div>
</div>
```

### Auth Page Container (Login / Register)
```tsx
<div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#3d2e28] via-[#2a1f1a] to-[#1a1210] p-4">
  <div className="w-full max-w-md">
    {/* Brand + Card */}
  </div>
</div>
```
