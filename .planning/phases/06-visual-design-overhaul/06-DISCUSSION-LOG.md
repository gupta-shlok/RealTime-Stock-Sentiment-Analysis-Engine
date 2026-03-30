# Phase 6: Visual Design Overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 06-visual-design-overhaul
**Areas discussed:** Branding, Theme system, CSS variables, News layout, Card surfaces

---

## Branding / Logo

| Option | Description | Selected |
|--------|-------------|----------|
| Keep RIT orange image logo | Preserve existing download.png + orange h1 | |
| Text logo with new app name | Display app name as styled text in TopBar | ✓ |

**User's choice:** Text logo — "StockSentimentSense"
**Notes:** User explicitly did not want the RIT orange branding.

---

## Theme System

| Option | Description | Selected |
|--------|-------------|----------|
| Dark only | Single dark theme, no toggle | |
| Dark default + light toggle | CSS variables with data-theme attribute, persisted to localStorage | ✓ |
| Light default + dark toggle | Same system, different default | |

**User's choice:** Dark/light configurable, dark as default
**Notes:** User said "the background can follow a configurable dark and light theme."

---

## Theme Toggle Location

| Option | Description | Selected |
|--------|-------------|----------|
| TopBar icon (sun/moon) | Always visible in header | |
| Inside Settings dialog | Alongside refresh interval dropdown | ✓ |

**User's choice:** Inside Settings dialog as a toggle button

---

## CSS Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Keep scattered hardcoded values | No change to CSS file structure | |
| Centralize into CSS variables | `:root` variables, `[data-theme="light"]` override | ✓ |
| MUI ThemeProvider | Full MUI theme integration | |

**User's choice:** Centralize CSS — "we can centralize the css for better style handling"
**Notes:** MUI ThemeProvider deferred — CSS variables sufficient for this phase.

---

## News Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current (50vw hero + flex row) | No layout change, only recolor | |
| Card-based modern layout | Hero card + 3-column row of smaller cards | ✓ |
| Editorial magazine grid | Complex multi-column masonry | |

**User's choice:** Modern card-based layout
**Notes:** User said "I would prefer a modern looking news layout."

---

## Card Surfaces / Glassmorphism

| Option | Description | Selected |
|--------|-------------|----------|
| Glassmorphism | backdrop-filter blur + translucent borders | |
| Flat dark cards | Solid surface color + subtle border | ✓ |

**User's choice:** Claude's recommendation (flat dark cards) accepted — no explicit objection
**Notes:** Claude recommended against glassmorphism for data-dense dashboard. User did not push back.

---

## Deferred Ideas

- Glassmorphism — explicitly discussed and deferred
- MUI ThemeProvider — deferred, CSS variables sufficient
