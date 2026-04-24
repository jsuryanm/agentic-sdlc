# Dashboard Readability Design

## Summary

This change improves readability in the Streamlit dashboard while preserving the current dark visual theme and overall layout. The update is intentionally narrow: slightly increase recurring text sizes and brighten low-contrast text colors so the interface is easier to scan in the sidebar and main content areas.

## Goals

- Keep the existing dark theme, spacing, layout, and accent palette.
- Make text easier to read across the dashboard.
- Improve visibility of muted labels, metadata, helper text, and small UI copy.

## Non-Goals

- No structural layout changes.
- No behavioral changes to the dashboard or pipeline flow.
- No rebrand or broad color-system rewrite.
- No changes to strong accent colors used for status meaning unless needed for contrast consistency.

## Scope

The work is limited to the CSS embedded in `src/dashboard/streamlit_app.py`.

Areas covered:

- Sidebar labels, title, textarea, button copy, pipeline labels, and session metadata.
- Main-area form controls, buttons, expanders, alerts, cards, and helper text.
- Custom HTML components such as metrics, badges, issue rows, artifact rows, terminal panels, and page subtitles.

Areas excluded:

- Python rendering logic.
- Data flow, API calls, and graph behavior.
- Sidebar component HTML structure in `src/dashboard/sidebar_components.py`.

## Design Approach

### Typography

Increase the smallest recurring text sizes by roughly one step, typically in the `0.04rem` to `0.1rem` range depending on context.

Expected adjustments:

- Micro labels and metadata move from very small sizes into a still-compact but more legible range.
- Body-adjacent helper text and panel copy move up slightly while preserving information hierarchy.
- Large headings and brand marks stay mostly unchanged unless they need minor balance adjustments relative to the new baseline.

### Color

Preserve dark backgrounds and existing gold, green, red, and blue accents, but brighten muted foreground colors that currently sit too close to the background.

Expected adjustments:

- Slate and blue-gray text used for labels, subtitles, metadata, and secondary descriptions becomes lighter.
- Primary readable text remains bright, with only minor tuning where needed for consistency.
- Status accents remain visually distinct and should not be diluted by the readability pass.

### Visual Stability

The change should feel like a polish pass, not a redesign. The interface should remain recognizably the same product with improved legibility.

## Implementation Notes

- Prefer grouped edits inside the existing `GLOBAL_CSS` block rather than introducing a new styling mechanism.
- Update repeated font-size and color declarations consistently across comparable component types.
- Be conservative with elements that intentionally look secondary; brighten them enough for readability without flattening hierarchy.

## Verification

After implementation, verify:

- The app still renders with the same layout and dark theme.
- Sidebar pipeline, badges, expanders, and metadata remain compact but easier to read.
- Alerts, cards, issue rows, and terminal-like sections retain clear visual hierarchy.
- Accent states such as success, warning, error, and active remain more prominent than baseline text.

## Risks

- Over-brightening secondary text could reduce hierarchy and make the UI feel noisy.
- Increasing small text too much could crowd compact elements such as pills, metadata rows, and pipeline descriptions.

## Mitigation

- Make only incremental adjustments.
- Favor readability improvements on the lowest-contrast text first.
- Leave spacing and layout untouched unless a font-size increase creates a visible collision.
