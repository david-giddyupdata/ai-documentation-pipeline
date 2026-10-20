# QuickSight Course Manual Style Guide

## Voice & Tone

Course manuals use a conversational, encouraging tone aimed at professionals learning QuickSight. Key characteristics:

- **Accessible:** Assumes no prior QuickSight experience
- **Encouraging:** "Let's" language, positive framing
- **Practical:** Focus on doing, not theory
- **Patient:** Acknowledges things may take time (SPICE imports, etc.)

**Example phrases:**
- "Let's connect to our data source"
- "Be patient! SPICE import may take a moment"
- "More details are available in the Addendum"

---

## Document Structure

### Section Format
Each major section follows this pattern:
1. Brief introduction/context
2. Step-by-step instructions with screenshots
3. "Completed Results" showing expected outcome
4. Optional: Commentary or reference to additional resources

### Instruction Format
- Numbered steps for sequential actions
- Each step = one action (click, type, select)
- Observations/notes in separate paragraphs
- Code blocks for calculated field syntax

**Example:**
```
1. Click Datasets in the left navigation.

2. Click New dataset.

3. Select S3 as the data source.
   Note: You can also use direct file upload for smaller datasets.
```

---

## Visual Elements

### Screenshots
- Placed inline with instructions
- Show current QuickSight UI (update when UI changes)
- Numbered callouts for complex interfaces
- Caption or context provided

### Tables
- Used for data samples, settings, field mappings
- Header row clearly labeled
- Consistent column alignment

### Code Blocks
- Calculated field syntax
- SQL queries (for Athena connections)
- Parameter expressions

---

## Formatting Conventions

| Element | Format | Example |
|---------|--------|---------|
| Hard-baked UI text | **Bold** | click **New dataset**, select **Inner join** |
| Variable/component names | "Double quotes" | select "Redshift-QuickSightClass", click "B-Data Sources" |
| Field member values | 'Single quotes' | filter to 'DFW' and 'IAH' |
| Field references | `{field_name}` with braces | drag `{iata}` to the **Columns** well |
| Menu paths | Arrow notation | **Data > Add data**, **File > Export** |
| Keyboard shortcuts | Plus notation | Ctrl + S |
| Calculated fields | Code blocks | `sum({cancelled})/sum({flights})` |
| Notes/warnings | Separate paragraph | "Note:" prefix |

### Text Formatting Summary
- **Bold** = buttons, menu items, UI labels that are always the same
- "Double quotes" = names you or the system assigned (dataset names, component names, analysis names)
- 'Single quotes' = specific values within a field (filter values, member names)
- `{braces}` = field names from the data

---

## QuickSight-Specific Terminology

Use these exact terms to match the QuickSight interface:

| Concept | Correct Term |
|---------|--------------|
| Data storage | SPICE / Direct Query |
| Chart types | Visual types |
| Dashboard sections | Sheets |
| Data connections | Data sources |
| Color and styling | Themes |
| Sharing | Publish dashboard |

---

## Document Layout Requirements

### Page Setup
- **Page size:** A4 Landscape (11.69" x 8.27")
- **Margins:** 0.50" on all sides
- **Orientation:** Landscape

### Two-Column Instruction Table
- **Left column (Instructions):** ~50% width
- **Right column (Screenshots):** ~50% width
- **Merged rows** for: Section headers, Completed Results

### Shading
| Row Type | Fill Color |
|----------|------------|
| Section headers | #D9D9D9 (light gray) |
| Completed Results | #E8F5E9 (light green) |
| Table headers | #D9D9D9 (light gray) |

---

## Screenshot Placeholders

When screenshots need updating:
- `[SCREENSHOT NEEDED: description]`: Red italic, needs capture
- `[SCREENSHOT: description]`: Gray italic, reusable from library

---

## Content Patterns

### Exercise Introduction
Brief context → what we're building → why it matters for business users

### Troubleshooting Notes
Inline with instructions when errors are expected (e.g., SPICE refresh failures)

### Completed Results
Visual confirmation of success:
- Screenshot of expected output
- "Completed Results:" label
- Brief description of what user should see

---

## David's Review Rules (apply without being asked)

Collected from David's draft reviews. Any agent editing the manual applies these by default. When David
gives a new rule, add it here in the same session.

### Step text
- **Don't explain what the student can see or work out.** If an action is intuitive from the screen, keep the
  step short. Good: "At the top of the interface, update the name of the dataset to “Uploaded-MonthlySummary”."
  Too much: "click the pencil next to “monthlysummary”, type … and click the check mark." (2026-10-13)
- **Do explain what isn't intuitive**: behavior the screen doesn't reveal. Example: "There's no Save button; the
  change applies when you choose a value, and the field's icon changes to a pin." (2026-10-13)
- **Keep a short how-to bullet when its picture shows it**, even if the action is easy. Example: "Click the
  dropdown arrow on the new sheet's tab and select **Rename**." next to the tab-menu screenshot. (2026-10-13)
- Where a screenshot already shows the answer, don't add extra bullets that repeat it. (session 4)
- **Inclusive date ranges say "through", not "to"**: "spanning January 2020 through December 2025". "To" can
  read as stopping before the end month. (2026-10-13)

### Screenshot size
- **Word "Scale" at least 90%; aim for 100%** when it fits. Our captures are saved at 192 dpi, so 100% is the
  on-screen size (1 in per 96 CSS px). David's own Snagit images are 96 dpi. (2026-10-13)
- **Maximum width: 5.57 in** in a two-column instruction row; **9.86 in** in a full-width row (Completed
  Results, Extra Credit images that span the table). (2026-10-13)
- If an image can't be 90% within the maximum width, **don't just shrink it; make it fit**: crop the sides; cut
  dead space out of the middle (for example the empty stretch between a dropdown's text and its arrow); use a
  horizontal tear on a tall image; recapture with a narrower browser window so the UI squeezes; or rebuild the
  shot (for example, long text on two lines). If nothing works, under 90% beats wider than the maximum, and
  flag it for David. (2026-10-13)
- Crop what the step doesn't need (for example a results table to the right of the pane being used), so the
  part that matters is larger. (2026-10-13)

### Screenshot content
- **Number both ends of an action.** When a step clicks fields in order and the Data pane has (1), (2), put the
  same (1), (2) where they land (the field wells). (2026-10-13)
- **Boxes hug the element.** Data-pane rows are full width; crop the blank part of the pane (or cut it out of the
  middle) so highlight boxes aren't wide and empty. (2026-10-13)
- **No stray tooltips or hover pop-ups** (for example "Format visual") over anything in the shot; move the
  mouse away before capturing. (2026-10-13)
- **Composite images are fine, and sometimes better**: two screenshots combined into one picture, with arrows,
  when that shows the action more clearly (example: master Themes step, Theme editor left pane + Custom color
  menu + Custom color dialog). Remove anything from the source shots that shouldn't show. (2026-10-13)
- **Torn-edge cut in the middle** to shorten a tall image (example: master Filled Map Edit filter). Optional,
  but use it where a tall image wastes a lot of vertical space. (2026-10-13)
- Show only what the student has at that step (no later sheet tabs, such as a sliver of "Point Map"). (2026-10-13)

### Layout
- **Images never touch the table border**: leave a little space below a picture at the bottom of a cell.
  (2026-10-13)
- **No blank pages.** (2026-10-13)
- **Keep "Completed Results:" on the same page as its image**; the row must not break across pages. (2026-10-13)
