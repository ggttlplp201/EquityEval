# Handoff: EquityEval UI redesign — Sector Explorer, Company Fundamentals, News & Calendar

## Overview

A dark-mode redesign of EquityEval, a local-first personal equity research workbench. Three
connected areas are covered, all driven by the explicitly fictional development fixture:

1. **Sector Explorer** — the four linked graphs (comparison bars, history, distribution
   histogram, growth-vs-valuation scatter) plus context bar, constituent table and evidence drawer.
2. **Company · Fundamentals** — guided five-step read with basis and own-history controls.
3. **News & calendar** — economic calendar, a worked assessment, and separated collection /
   assessment health.

Design priorities, in order: preserve every financial meaning and coverage disclosure from the
brief; make the five-minute read easy; keep every displayed number one click from its evidence.

## About the design files

`SectorExplorer.design.html` is a **design reference created in HTML** — a prototype showing the
intended look and behavior. It is **not production code to copy**. The task is to recreate these
designs in the target codebase's existing environment (the current app is Next.js 15 + React 19
with plain CSS in `apps/web`), using its established patterns.

The file is a single self-contained component: markup with `{{ }}` value holes plus a
`class Component` that returns all view values from `renderVals()`. Read it as
**markup + view-model**, and port it to the codebase's own component idiom. The existing
`apps/web/src/features/sectors/{SectorExplorer.tsx,charts.tsx,types.ts}` already has the correct
state shape and data contract — keep that, and replace the presentation.

**Hard constraint carried over from the brief:** the browser may format and position only. All
financial arithmetic, eligibility gates, bin bounds and coordinates come from the Python core /
presentation exporter. The fixture values inside the design file exist purely to make the
prototype render; do not port them as a calculation layer.

## Fidelity

**High-fidelity.** Final colors, typography, spacing and interactions. Recreate pixel-accurately
using the codebase's own primitives. Every value below is exact.

---

## Design tokens

### Color — surfaces

| Token | Hex | Use |
| --- | --- | --- |
| `--bg` | `#0e1413` | Page background |
| `--surface` | `#161f1e` | Cards, panels, drawer, table header cells |
| `--surface-header` | `#151d1c` | App header bar |
| `--surface-subtle` | `#1a2321` | Legend strips, source-chain cards, inner wells |
| `--surface-raised` | `#1d2725` | Inactive segmented-control buttons |
| `--surface-selected` | `#1b2523` | Selected bar row, pinned company row |
| `--surface-aside` | `#1b2320` | "How to read" / "Review prompts" panels |
| `--banner` | `#1d2418` | Fictional-data banner |

### Color — lines

| Token | Hex | Use |
| --- | --- | --- |
| `--line` | `#26312f` | Card borders, header rule, column-head rule |
| `--line-soft` | `#232e2c` | Row separators, chart grid lines |
| `--line-strong` | `#33403d` | Control borders (segmented, select, search) |
| `--line-axis` | `#35423f` | Chart baselines, dashed roadmap border |
| `--shell` | `#212b29` | Outer shell left/right border |

### Color — text

| Token | Hex | Contrast on `--surface` | Use |
| --- | --- | --- | --- |
| `--ink` | `#eaf0ed` | 13.9:1 | Primary text, headings, values |
| `--ink-2` | `#d9e4df` | — | Inactive segmented label |
| `--ink-3` | `#b6c5bd` | — | Scatter point labels |
| `--muted` | `#9fb0a9` | 6.9:1 | Body copy, secondary values |
| `--muted-2` | `#93a49d` | 5.9:1 | Eyebrows, column heads, footnotes (min size 10px) |
| `--muted-3` | `#7d8b85` | 4.5:1 | Planned/disabled tab labels, placeholder |

Small text ≥ 4.5:1 is a hard requirement from the brief. Nothing below 10px.

### Color — semantic

| Token | Hex | Use |
| --- | --- | --- |
| `--accent` | `#00e0a4` | All chart marks, swatches, brand dot, live indicator |
| `--accent-bright` | `#8affd8` | Selected histogram bin stroke |
| `--accent-deep` | `#177a61` | Unselected histogram bin fill |
| `--accent-mid` | `#25a483` | Unselected histogram bin stroke |
| `--link` | `#6fcfb5` | Links, text buttons, eligible chip text |
| `--link-hover` | `#9ae2cd` | |
| `--tint-ok` | `#182a25` | Eligible chip background, active nav pill |
| `--border-ok` | `#2f6455` | Eligible chip border |
| `--tint-ok-2` | `#15251f` | Observations block background |
| `--warn` | `#e3b46c` | Limited coverage, N/M, unavailable, proposal labels |
| `--warn-strong` | `#e8c98d` | Simple-mean warning text |
| `--warn-bg` | `#241c10` | Warning block background |
| `--warn-border` | `#5b4826` | Warning chip border |
| `--warn-rule` | `#d99b3e` | Warning left rule, focus outline |
| `--olive` | `#cbd5ab` | Fictional-data banner text |

**Sector palette:** all seven sectors use `--accent` (`#00e0a4`). This is deliberate — the user
asked for one color. Sector identity is carried by label, position and the checkbox legend, never
by hue. In the history chart, up to four selected series are separated by **stroke opacity**
in legend order: `1, 0.68, 0.44, 0.26`. Keep the `color` field per sector in the data model so a
multi-hue mode can be reinstated without a refactor.

### Typography

Single family: `'Helvetica Neue', Helvetica, Arial, sans-serif`.
Numeric/label family: `ui-monospace, SFMono-Regular, Menlo, monospace`.

| Role | Size | Weight | Tracking | Line-height |
| --- | --- | --- | --- | --- |
| Page title (h1) | 32px (Sector) / 30px (Company, News) | 700 | −0.7px | 1.12 |
| Section title (h2) | 23px | 700 | −0.5px | default |
| Panel heading (h3) | 15–17px | 700 | — | default |
| Aside heading | 19–20px | 700 | −0.3px | 1.25 |
| Body | 12.5–14.5px | 400 | — | 1.5–1.55 |
| Footnote | 11–11.5px | 400 | — | 1.55 |
| Eyebrow (mono, uppercase) | 10px | 600 | 1–1.1px | 1.4 |
| Column head (mono, uppercase) | 10px | 600 | 1.1px | — |
| Value (mono) | 13.5–14px | 400 | — | 1.25 |
| Big stat (mono) | 19px | 500 | — | — |
| Chip / tag | 10.5–12px | 400 | 0.5–0.8px on mono | — |

### Spacing, radius, elevation

- Page padding `26px 22px 60px`; header padding `14px 22px`; card padding `18px 20px`.
- Card gap `18px`; inline control gap `12–16px`; chip gap `8px`.
- Radius: cards/panels `6px`; controls, chips, drawer sources `5px`; bars, small chips `2–4px`.
- Shadow: only the advanced-method popover — `0 12px 30px rgba(0,0,0,.55)`.
- Drawer scrim `rgba(0,0,0,.62)`.
- Focus ring: `outline: 2.5px solid #d99b3e; outline-offset: 3px` on every interactive element.
- Shell max-width `1480px` (desktop) / `390px` (mobile prop), centered, with `--shell` side borders.

---

## Screens

### 1. Sector Explorer

**Purpose:** compare sectors on one measure, then inspect the selected sector four ways and reach
the constituent companies and their evidence.

**Layout, top to bottom:**

1. **Fictional-data banner** — full width, flex, `background:#1d2418; color:#cbd5ab`, mono 11px.
   Copy: `FICTIONAL DATA` / "Invented companies and invented financial inputs. No market
   conclusions." / right-aligned link "Production prerequisites ↗".
2. **App header** — 30×30 rounded-4px brand mark (`#eaf0ed` on `#0e1413`, bold 16px "E"),
   wordmark 18px/700/−0.4px, nav pills (active: `#182a25` bg, `#eaf0ed` text, 600), right-aligned
   `LOCAL WORKBENCH · AWAKE` with a 6px accent dot.
3. **Title block** — eyebrow `THE BIG PICTURE, WITH THE DETAILS`, h1, one-line subhead;
   right column: `SOURCE SNAPSHOT`, truncated id, membership-mode line.
4. **Context strip** — one bordered card, flex-wrapping cells with `1px solid #26312f` dividers:
   Universe · Taxonomy · Evaluation date (`<select>`) · Period+Currency · Calculation.
   The Calculation cell mirrors the active method label.
5. **Comparison panel** (card):
   - Toolbar: `MEASURE` eyebrow + 18px/700 `<select>` with a 1.5px bottom rule (9 metrics);
     right side a 2-button segmented control (`Sector total` / `Typical company`) and an
     `Advanced method` `<details>` popover containing `Simple mean` + its caveat.
     Active segment `#eaf0ed` bg / `#0e1413` text; inactive `#1d2725` / `#d9e4df`.
     Breadth metrics disable the median/mean buttons (`opacity:.45`) and relabel the first
     segment `Equal-company breadth`.
   - Heading row: h2 "Across the declared sectors" + the metric definition; right side
     `Market reference` checkbox and Sort `<select>` (Alphabetical / Value · eligible only).
   - Column head (flex, **wrapping**): `SECTOR` (168px) · axis ticks (flex 1, 5 ticks positioned
     absolutely at 0/25/50/75/100% with translateX 0/−50%/−100%) · `VALUE` (96px, right) ·
     `N · K · V · COVERAGE` (174px, right).
   - **Bar rows** (7): flex-wrap, `9px 0` padding, `1px solid #232e2c` bottom rule.
     - Label button: 8px accent dot + name; selected row gets `#1b2523` background and 600 weight.
     - Track: 26px tall, 1px zero line at left, bar 18px tall, radius 2px, `min-width:3px`.
       Eligible = filled accent. **Limited coverage = transparent fill, 1.5px accent outline.**
       Missing/N/M = no bar, instead a dashed-border mono label in the track.
     - Value cell: mono 13.5px; if limited, a 10px `LIMITED COVERAGE` line in `--warn` beneath.
     - Coverage cell: mono 11px, two lines — `N 12 · K 12 · V 12` then
       `data 100% · cap 100%`; the whole line turns `--warn` when cap coverage is `Unavailable`.
     - Every one of these four cells opens the evidence drawer.
   - **Coverage legend** (togglable prop): `#1a2321` well defining N, K, V and the gate
     `V ≥ 10 · K/N ≥ 70% · cap coverage ≥ 80% · unknown cap fails`.
   - **Encoding legend:** outlined-bar swatch + dashed-line swatch with their meanings.
   - **Market reference block:** always-visible button. When eligible it is neutral-bordered and a
     dashed `#46564f` vertical line is drawn in every bar track at the market position. When
     **limited**, the dashed line is suppressed, the block takes the amber border/background, and
     the status line reads "Limited coverage — no dashed reference line is drawn · data 98% ·
     cap Unavailable". This is a required behavior, not decoration.
   - `<details>` table alternative: Sector / Value / N·K·V / Data cov. / Cap cov. / Status·exclusions.
6. **Selected-sector heading** — eyebrow `LOOK INSIDE`, h2 with accent dot, and two secondary
   buttons: `Explore industries ↗`, `Coverage & calculation`.
7. **Observations block** — 3px accent left rule on `#15251f`, one `<p>` per observation.
   For a limited-coverage sector these are replaced with withheld-claim copy.
8. **Concentration strip** — two stat buttons (current top-five cap share; growth excluding the
   *prior-date* top five, with both dates shown) + a right-aligned caveat that the two measures
   are not interchangeable.
9. **Research grid** — `repeat(auto-fit, minmax(360px, 1fr))`, gap 18px:
   - **01 / THROUGH TIME** — `1Y/3Y/5Y` segmented control, seven sector checkboxes (max 4;
     the rest disable), an SVG line chart (`viewBox 0 0 720 240`, 5 grid lines with mono labels,
     paths 2.25px, 3.6r dots with `#161f1e` fill), gap-preserving paths (a null starts a new
     subpath — **never interpolate**), start/end date labels, the current-members-backcast caveat,
     and a `<details>` data table.
   - **02 / WITHIN THE SECTOR** — 5-bin histogram as flex columns (height % of max count, count
     label inside the top), bin range labels beneath, P25 / MEDIAN / P75 buttons, exclusion chips
     (`1 nonpositive earnings — N/M`, `0 missing inputs`, `0 stale…`, `0 unsupported profile`),
     and the no-trimming note. Clicking a bin toggles the constituent-table filter.
   - **03 / TWO DIFFERENT QUESTIONS** — CSS-positioned scatter in a 230px box with left/bottom
     axes, dashed y gridlines, 13px dots (11/16/22px when "Size by market cap" is on), labels to
     the right of each dot, axis captions, and a **"Not placed"** list naming each absent sector
     and why (limited coverage; unsupported profile). Nothing is ever plotted at zero.
   - **HOW TO READ THIS VIEW** — aside on `#1b2320`, four numbered notes (sector total vs typical
     company vs coverage vs the ETF caveat) and a `Missing production prerequisites` `<details>`.
10. **Constituents panel** — search field, optional bin-filter chip with clear, wrapping column
    head, 12 rows: ticker (mono 600) + name, value, eligibility chip + reason, Pin/Unpin,
    `Fundamentals ↗`. Empty state with "Clear filters".
11. **Roadmap strip** — dashed-border card listing retained-but-unbuilt destinations with their
    status tags (`F-13 · PLAN`, `D004 · P1`, …).
12. **Footer** — two mono lines: fictional snapshot context, and rules/policy version.
13. **Evidence drawer** — fixed right panel, `min(540px,100%)`, scrim, `FROZEN SNAPSHOT ·
    FICTIONAL` eyebrow, title, subtitle, then sections (Calculation / Coverage / Exclusions /
    Concentration, or Result / Inputs for a company, or Result / Gate for the market reference),
    then a Source chain of cards with accession, capture time, transform and usage.

### 2. Company · Fundamentals

Title block → **identity strip** (6 cells: issuer+security, exchange+currency, quote with delay
and age, reporting period, balance-sheet date, filing cutoff + capture vintage) → tab row
(`Fundamentals` active, `Overview`, `Financials`, then dashed non-interactive `DCF P1`,
`Comps P1`, `Scenarios P1`, `Catalysts P2`, `Noise P2`, `Thesis P2`, `Calibration P2`) →
**controls bar** (BASIS: TTM / Latest quarter / Fiscal year 2025, with a basis note; OWN HISTORY:
3Y / 5Y / 10Y with a coverage note) → **insufficient-history block** shown only at 10Y:
"24 eligible quarter ends covering 6.0 years… the window has **not** been silently shortened and
no percentile band or rank is shown."

Then the guided grid, `repeat(auto-fit, minmax(400px, 1fr))`, in fixed order:
`01 Growth → 02 Profitability → 03 Cash generation → 04 Balance sheet → 05 Valuation`, plus
`06 Returns on capital` as a collapsed `<details>` (align-self:start). Each card: step number +
title, one-line purpose, 4 metric rows (label / mono value / delta with green-or-amber tint /
`Evidence` link), and a limitation footnote — gross margin ≠ unit economics, CFO−PPE capex ≠ FCFF,
restricted cash ≠ available cash, forward P/E needs reviewed estimates, SBC ≠ dilution.
All three period values per row are in the data; the BASIS control swaps them.

Bottom row: **neutral review prompts** (max three, each with a limitation line, closing with the
explicit "no score, conviction, price target, bargain or value-trap label") and an
**applicability & coverage** card (status chips, issuer profile, fiscal-calendar support,
restatement mode, and the note that banks/insurers/REITs would read "Sector-specific
interpretation needed" instead).

### 3. News & calendar

Title block → amber **PROPOSAL** block ("Monitoring is designed, not deployed…") → three health
cards: **Collection health** (configured sources 0 of 6, cadence, last success, lag),
**Assessment health** (produced, queue, revisions, outside-market-hours behavior) — kept
deliberately separate — and **Runtime & delivery** (local machine, no collection while asleep with
catch-up on wake, quiet hours delay delivery not collection, three channel chips with real states:
in-app ready, desktop permission not granted, email unconfigured).

Then a two-column grid: **US economic calendar** with four entries showing the four distinct
states (`HEADS-UP` / `RELEASED` with release·consensus·prior as three separate figures /
`CORRECTION` retaining the original value / a second heads-up that generates no expectation), and
a worked **assessment** card: verified facts (green rule) vs inference (amber rule) as visually
separate blocks, a meta row (assessment confidence / source reliability / horizon / materiality —
confidence and reliability are distinct axes), business driver, counterevidence, what would
reverse it, the no-causation-from-price-movement note, and a revision-history `<details>` showing
rev 1 retained rather than overwritten.

Finally **topic discovery**: chips with `ACTIVE` / `MUTED` / `EXCLUDED` states and the note that
relevance discovery covers regulation, products, ecosystems, competitors, customers and suppliers
including developments that never name the ticker.

---

## Interactions & behavior

| Trigger | Result |
| --- | --- |
| Nav pill | Switches screen; clears the open drawer |
| Measure `<select>` | New metric; breadth metrics force method to `total`; clears bin filter and drawer |
| Method segment | New method; **recomputes V** (see below); clears bin filter |
| `Simple mean` | Sets method and shows the amber sensitivity warning above the chart |
| Evaluation date | Reloads the frozen view; clears bin and drawer |
| Sort | Alphabetical, or descending value with **ineligible rows pushed to the end and never ranked** |
| Market reference checkbox | Shows/hides the dashed marker *and* the disclosure block |
| Bar / value / coverage cell | Opens the evidence drawer for that sector |
| Sector label, scatter point, "Not placed" entry | Selects the sector; resets history selection to it, clears bin, pin and search |
| History checkbox | Toggles series; hard cap of 4 (others disable) |
| `1Y/3Y/5Y` | 5 / 13 / 21 quarter-end points |
| Histogram bin | Toggles the constituent-table filter; shows a clearable chip |
| Pin company | Toggles the pinned row highlight |
| Search | Filters ticker + name, case-insensitive, composes with the bin filter |
| BASIS / OWN HISTORY | Swap displayed values / trigger the insufficient-history state at 10Y |
| Drawer scrim, `×` | Close |

No animation anywhere beyond native `<details>` disclosure — intentional for a research tool.

**Responsive:** no media queries. Grids use `repeat(auto-fit, minmax(360–420px, 1fr))`; all row
layouts are `flex-wrap:wrap` with fixed-basis cells, **including the column headers** (they must
wrap in step with their data rows). The 390px mobile mode is the same markup at a narrower shell.
Dense tables scroll inside their container; the page never overflows horizontally.

**Accessibility:** `aria-pressed` on every toggle; `aria-label` on chart roots and icon buttons;
status is always carried by text and shape (outline, dashed border, chip label) in addition to
color; hit targets ≥ 36px in the controls; visible amber focus ring.

## State

```
screen      'sectors' | 'company' | 'news'
metric      one of 9 metric ids            method  'total' | 'median' | 'mean'
asOf        evaluation date                sector  selected sector id
win         '1' | '3' | '5'                historySel  string[] (max 4)
sort        'alpha' | 'numeric'            showMarket, capSized  boolean
query       string                         bin  number | null
pinned      company id | null              detail  drawer descriptor | null
fPeriod     0 | 1 | 2                      fWin  '3' | '5' | '10'
```

Derived, and the part most worth porting carefully:

- **V is method-dependent.** `V = K` for sector total and breadth; `V = K − nonPositiveCount` for
  median and simple mean. Known losses and exact zeros stay in K even when the company multiple
  is N/M.
- **Status** resolves to `nm` (null value) → `limited` (cap coverage unknown, or `V < 10`) →
  `eligible`. Limited rows keep their value and bar outline but get no rank and no scatter point.
- **Axis max** is a "nice" ceiling over all sector values *and* the market reference, so the
  reference is never clipped; 5 ticks.
- In production all of these arrive precomputed from the core; the prototype derives them only so
  the controls are live.

## Assets

None. No images, no icon fonts, no SVG illustrations. The brand mark is a styled letter, the
search glyph is `⌕`, disclosure arrows are `▸`. Fonts are the system Helvetica stack — nothing to
load.

## Files

- `SectorExplorer.design.html` — the complete design reference (all three screens). Open it
  directly in a browser; the nav switches screens and every control works.

Original brief material lives in the project's `uploads/` folder:
`01_EquityEval_Design_Brief.txt` (Part B checklist has the 113 feature IDs),
`02_EquityEval_Current_UI_Reference.txt` (the current React/CSS source), and the four PNGs.

## Feature-ID coverage

Represented: **X-01 … X-23** (all four graphs, context bar, method/metric/date/sort controls,
market reference incl. the limited-coverage disclosure, drilldown entry point, coverage panel,
exclusions, scatter unavailable list, table alternatives, full ranges), **G-02, G-04, G-06, G-07,
G-10**, **F-01 … F-04, F-07, F-08, F-10, F-11** (guided order, basis and 3/5/10Y controls,
insufficient history, neutral prompts, applicability), and the N1 states (calendar heads-up /
release / correction, fact-vs-inference, confidence vs reliability, revision history, topic
management, separated health, local runtime, quiet hours, channels).

Not represented: **W1 watchlist** (add / resolve / stage progress / partial failure / rerun /
run comparison), **U1 help, glossary and printable manual**, **X-24/X-25** real-data setup and
refresh-failure frames, **F-05/F-06/F-09/F-12 … F-15** detail screens, and the P1/P2 workspaces —
all of which appear only as labelled roadmap destinations. Treat that list as open, not as
descoped.
