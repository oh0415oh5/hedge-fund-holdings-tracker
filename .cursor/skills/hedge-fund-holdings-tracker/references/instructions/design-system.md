# Design System — Wall Street Prompt × Manus skills

This file is shared across all three WSP skills (web-traffic-intel, stock-value-chain-mapping, hedge-fund-holdings-tracker). The content must remain byte-identical across all three skill folders to preserve consistent visual identity. Do not edit one skill's design-system.md without propagating to the others.

## Palette

Use these exact hex codes for every deliverable. Do not substitute, lighten, or "interpret" the palette.

| Token | Hex | Purpose |
|---|---|---|
| `--paper` | `#FAF6EE` | Background (cream) |
| `--ink` | `#1F1B16` | Primary text, borders, target center node (dark brown) |
| `--ink-soft` | `#4A4239` | Secondary text |
| `--ink-mute` | `#807868` | Tertiary text, dim labels |
| `--rule` | `#D9CFB9` | Dividers, light borders |
| `--accent` | `#B5311A` | CTAs, supplier nodes, important callouts, primary highlight |
| `--positive` | `#1FAE7B` | Customer nodes, positive deltas (gains, adds) |
| `--code-bg` | `#F1EADC` | Code blocks, ticker chips |

## Typography

- **Display headers**: Source Serif 4 (or Charter / Georgia fallback) — weight 700, italic for accent numerals
- **Body**: Inter (or system-ui fallback) — weight 400 / 500 / 600
- **Code / tickers / CUSIPs**: JetBrains Mono (or system mono fallback)
- All primary text in `--ink`. Secondary text in `--ink-soft`. Dim labels in `--ink-mute`.

## Neobrutalism conventions

These rules are non-negotiable. Apply across deployed websites, HTML reports, and PDF deliverables.

1. **Thick borders.** 3px solid `--ink` on cards, modules, tables, charts, buttons.
2. **Hard offset shadows.** `box-shadow: 6px 6px 0 0 var(--ink)` for large elements (cards, modules); `4px 4px 0 0 var(--ink)` for smaller (buttons, chips). NEVER use soft blurred shadows or rgba shadows.
3. **No gradients.** Solid colors only. No linear-gradient, radial-gradient, glassmorphism, or shimmer effects.
4. **Minimal border-radius.** 0–4px maximum. No pill buttons, no large rounded cards.
5. **Chunky deliberate layout.** Generous padding inside cards (16–24px). Tight gaps between cards (12–16px). Every chart and module is its own bordered card on `--paper`.
6. **No drop-shadow text effects.** Text is flat in `--ink` or `--ink-soft`.
7. **Color discipline.** `--accent` (red) reserved for CTAs, supplier nodes, and primary highlights — do not use for body text or large fills. `--positive` (green) reserved for customer nodes and positive deltas.

## Charts

When charts are required:
- Background: `--paper`
- Bar fills: `--accent` for primary series, `--positive` for delta-positive, `--ink-soft` for neutral / secondary
- Axes and gridlines: `--rule` at 0.5px
- Axis labels: `--ink-mute` in Inter 10pt
- Border around chart canvas: 3px solid `--ink` (neobrutalism rule)
- Chart title above: bold Inter or Source Serif 4 in `--ink`

## Image Aspect Ratios (REQUIRED)

Never stretch or squish images. Preserve the original aspect ratio of every embedded image (logo, chart, screenshot, diagram).

CSS pattern:

```css
.logo { height: 48px; width: auto; }   /* OK — preserves ratio */
.chart { width: 100%; height: auto; }  /* OK — preserves ratio */
.img-stretched { height: 48px; width: 200px; }  /* WRONG — stretches */
```

For any constrained container, use `object-fit: contain` so the image scales without cropping or distorting:

```css
.container img { width: 100%; height: 100%; object-fit: contain; }
```

The WSP logo (`assets/wsp_logo.png`) is the most-checked surface. Its aspect ratio must be preserved everywhere it appears — header, footer, brand block, sidebar entry. Setting both a fixed width and a fixed height on the logo is a HARD FAIL.

## Forbidden visual patterns

Fail-criteria for the eval checklist. Any of these = revise before delivery.
- Generic Bootstrap-style cards (rounded, soft shadow, gradient backgrounds)
- Material Design or iOS-style "elevation"
- Glassmorphism / frosted glass
- Neon glow effects
- Default browser fonts (Times New Roman, plain Arial)
- Off-palette colors (purples, oranges, teals not in the palette table above)
- Stretched or squished images (any image with both fixed width and fixed height that distorts its aspect ratio)
