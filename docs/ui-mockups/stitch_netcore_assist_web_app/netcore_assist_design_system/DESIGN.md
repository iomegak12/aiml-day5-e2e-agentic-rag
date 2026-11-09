---
name: NetCore Assist Design System
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f4'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#444748'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#585f6c'
  on-secondary: '#ffffff'
  secondary-container: '#dce2f3'
  on-secondary-container: '#5e6572'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1d1b1a'
  on-tertiary-container: '#868381'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#dce2f3'
  secondary-fixed-dim: '#c0c7d6'
  on-secondary-fixed: '#151c27'
  on-secondary-fixed-variant: '#404754'
  tertiary-fixed: '#e6e1df'
  tertiary-fixed-dim: '#cac6c3'
  on-tertiary-fixed: '#1d1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: '600'
    lineHeight: 2.5rem
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.625rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.45rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.25rem
  label-md:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.375rem
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.25rem
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 0rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes an ultra-refined, quiet, and hyper-focused workspace for enterprise network engineers, architects, and DevOps operators. Blending structural clarity with a modern conversational AI aesthetic, the visual mood is calibrated to feel serene, authoritative, and frictionless—counterbalancing the high cognitive load of mission-critical SD-WAN diagnostics, BFD convergence monitoring, and SLA orchestration.

The visual direction merges **Minimalism** with **Atmospheric AI Nuance**:
- **Canvas Atmosphere:** Clean pure white base structured with an ethereal, diffused pastel radial aura (radiating gentle warm canary, soft blush, and lavender) anchored specifically beneath the main workspace.
- **Form Factor:** Purpose-built for high-density desktop web operations, utilizing disciplined negative space, hair-thin boundaries, and razor-sharp typographic scale.
- **Tactility:** Deliberate balance of engineered geometry (12px continuous radius surfaces) and ergonomic micro-elements (pill-shaped selectors and circular command triggers).

## Colors

The palette operates on restraint, relying primarily on near-black ink, soft neutral greys, and crisp surface whites, energized by high-definition functional status tints and deep charcoal telemetry surfaces.

### Surface Tones & Ambient Gradient
- **Canvas Base:** `#FFFFFF`
- **Ambient Radial Gradient:** Multi-stop diffuse aura placed behind the primary conversational track:
  - Center: `#FFFBEB` (Warm Canary, 45% opacity)
  - Mid-stop: `#FDF2F8` (Delicate Blush, 35% opacity)
  - Outer: `#F5F3FF` (Atmospheric Lavender, 25% opacity)
  - Fade: Blurs entirely into `#FFFFFF` at container boundaries.
- **Sidebar Surface:** `#FAFAFA` with subtle `#ECECEC` boundary delineation.
- **Inspector Panel Surface:** `#FFFFFF` or translucent frosted white `#FFFFFFE6` over background aura.
- **Code & Console Surface:** `#1E1E1E` (Dark Charcoal) for zero-glare terminal logs and telemetry payload inspection.

### Monochrome & Neutral Hierarchy
- **Text Primary (Ink):** `#111111` — Headings, key values, primary commands.
- **Text Body:** `#333333` — Assistant responses, architectural analysis, configuration diffs.
- **Text Secondary / Metadata:** `#8A8A8A` — Timestamps, hop counters, BGP peer state tags, unit captions.
- **Border Default:** `#ECECEC` (1px solid hairline).
- **Border Interactive / Hover:** `#D4D4D4`.

### Operational Status Tokens
Status indicators use a dedicated tri-token recipe (solid icon/label, low-intensity background fill, and matched tint border):
- **Success / Active / Healthy (Up, Passed, Low Latency):**
  - Text & Icon: `#10B981`
  - Background Fill: `#ECFDF5`
  - Border Stroke: `#A7F3D0`
- **Warning / Degraded / Low Confidence (Partial, Jitter Spike, Disconnected):**
  - Text & Icon: `#F59E0B`
  - Background Fill: `#FFFBEB`
  - Border Stroke: `#FDE68A`
- **Critical / Failed / Alert (Timeout, Policy Drop, BFD Down):**
  - Text & Icon: `#EF4444`
  - Background Fill: `#FEF2F2`
  - Border Stroke: `#FECACA`
- **In-Progress / Streaming / Executing (Active Trace, Probe Sync):**
  - Text & Icon: `#3B82F6`
  - Background Fill: `#EFF6FF`
  - Border Stroke: `#BFDBFE`
- **Neutral / Idle / Cached (Skipped, Synthetic Baseline):**
  - Text & Icon: `#6B7280`
  - Background Fill: `#F3F4F6`
  - Border Stroke: `#E5E7EB`

## Typography

The type system prioritizes reading comprehension during complex multi-hop network analysis and SLA policy evaluations.

- **Primary Typeface:** `Inter` handles all user-facing interfaces, conversational responses, and systemic metadata. Headings utilize semibold weights (`600`) with tight tracking to maintain authority, while body text uses a relaxed line height (`1.625`) for continuous conversational scanning.
- **Monospace Typeface:** `JetBrains Mono` manages syntax blocks, CIDR notations, MAC addresses, YAML configurations, and real-time execution logs. Font features such as zero-slashing and tabular lining numbers are enabled by default.
- **Numeric & Metrics Handling:** All throughput, packet loss, and latency metrics within tables and metrics chips render in tabular numbers (`tnum`) to eliminate jitter during real-time streaming updates.

## Layout & Spacing

The viewport implements a dedicated three-tier operational shell optimized for standard and wide desktop monitors (1440px+ standard):

```
+----------------+-------------------------------+----------------------+
|  Left Sidebar  |     Chat & Workflow Column    |   Context Inspector  |
|     (240px)    |         (Max 760px)           |        (380px)       |
+----------------+-------------------------------+----------------------+
```

### Layout Architecture
- **Left Navigation Sidebar (Fixed 240px):** Light neutral tint (`#FAFAFA`), contains tenant switchers, network site hierarchies (SD-WAN nodes), recent incident sessions, and NetCore Meet room bridges.
- **Primary AI Workspace (Max 760px Centered):** Houses the conversational feed, interactive remediation steps, topology change previews, and the floating execution composer. Unbounded height with smooth auto-scroll orchestration.
- **Contextual Inspector (Fixed 380px, Collapsible):** Displays real-time telemetry metrics, SLA burn rates, active QoS queue drops, and BFD link peer states tied directly to the current chat prompt.
- **Breakpoint Rules:**
  - Below `1280px`: Right inspector collapses into a drawer accessed via a top-right toggle.
  - Below `1024px`: Left sidebar collapses into an icon rail (64px), dedicating the viewport to the conversational stream.

## Elevation & Depth

This design system avoids heavy shadows, skewing towards a flat, architectural presence defined by 1px hairline structural dividers and delicate ambient dispersion.

- **Level 0 (Flat Canvas & Panels):** Sidebar, conversation viewport, and inspector rest on the same baseline elevation, separated strictly by `1px solid #ECECEC` vertical rules.
- **Level 1 (Cards & Data Containers):** Grounded cards use `#FFFFFF` fill with `1px solid #ECECEC` borders. No drop shadows.
- **Level 2 (Floating Composer & Overlays):** The conversational input composer floats pinned at the bottom of the 760px column. It applies an ultra-refined shadow to lift cleanly over incoming text streams:
  `box-shadow: 0 4px 20px -2px rgba(17, 17, 17, 0.04), 0 2px 6px -1px rgba(17, 17, 17, 0.02)`.
- **Level 3 (Dropdown Menus & Modals):** Crisp flyouts use `#FFFFFF` with `1px solid #ECECEC` and `box-shadow: 0 12px 32px -4px rgba(17, 17, 17, 0.08)`.

## Shapes

The shape vocabulary applies a strict two-tier taxonomy:

1. **Containers & Structural Cards (`roundedness: 2` / 12px):** Diagnostic cards, configuration diff containers, telemetry panels, inspector modules, and code log wrappers maintain a clean, exact `12px` corner radius.
2. **Interactive Controls & System Status Badges (Full Pill / 9999px):** All buttons, input triggers, status indicators, filter tags, network interface pills (e.g., `ge-0/0/1`), and execution controls use completely rounded capsule/pill silhouettes. Circular action elements maintain a precise 1:1 aspect ratio.

## Components

### Buttons & Action Controls
- **Primary Action (Circular Command Button):**
  - Pure `#111111` circle (36px or 40px diameter), containing a centered crisp white (`#FFFFFF`) arrow or icon.
  - Hover state: Slight expansion scale (`transform: scale(1.03)`) with background shift to `#262626`.
- **Secondary Action (Pill Buttons):**
  - Background `#FFFFFF`, border `1px solid #ECECEC`, text `#111111`, border-radius `9999px`.
  - Hover: Background `#F9F9F9`, border `#D4D4D4`.
- **Icon Actions (Ghost):**
  - Transparent background, `#8A8A8A` iconography, transitioning to `#111111` on hover with a `#F5F5F5` pill backing.

### Status Indicators & Pills
- Rendered as compact badges (height: 24px) with `border-radius: 9999px`, padding `0 10px`, font size `11px`, weight `600`.
- Includes a 6px solid colored circular dot on the left side of the label matching the indicator text color.
- Applied across SLA statuses (e.g., `SLA OK`, `JITTER VIOLATION`), BFD health states, and AI step streams.

### Floating Prompt Composer
- Pinned at the bottom of the central 760px column with `16px` bottom offset.
- Styled as a contained card (`border-radius: 16px`, background: `#FFFFFF`, border: `1px solid #ECECEC`).
- Features a multi-line auto-expanding textarea, bottom-left utility pills (Attachment, Network Scope, Target Router), and bottom-right circular `#111111` submit trigger.

### Code, CLI, & Telemetry Blocks
- Enclosed in an independent `12px` rounded card with `#1E1E1E` background.
- Header strip: Top-left displays language or context metadata (`BGP Route Table`, `cisco-ios-xe`, `json`) in `#8A8A8A` uppercase `11px` monospace. Top-right houses a secondary pill "Copy" button with ghost styling.
- Body: Monospace `JetBrains Mono` (`13px`, line-height `1.5`) with light syntax tokens (keywords in muted azure, numbers in soft amber, strings in gentle sage).

### Network Metric & Incident Cards
- Structured `12px` rounded cards with `#FFFFFF` fill and `1px solid #ECECEC` borders.
- Top section: Incident title, interface identifier tag, timestamp, and aligned operational status pill.
- Bottom section: Inline sparkline or key-value metric pair (e.g., `RTT: 14.2ms | Loss: 0.00%`).