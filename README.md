# OpenAward

A configurable, print-ready feedback sheet generator for robotics competition scoring. Built for [FIRST Tech Challenge](https://www.firstinspires.org/robotics/ftc) and [SPL](https://wiki.teamclockworks.ro/en/spl-rules), but adaptable to any competition with award-based judging criteria.

OpenAward reads a JSON config defining awards and criteria, pairs it with a flat CSV of scores, and produces a single HTML file containing:

- **Scoring overview pages** with per-award averages, standard deviations, and top-3 highlights
- **Per-team feedback sheets** with individual criterion scores, bar charts, and notes
- **Automatic pagination** that keeps award sections intact across multiple pages
- **QR codes** linking to full criteria descriptions

Everything is optimized for **grayscale A4 printing** with `print-color-adjust: exact`.

## Examples

| ![SPL Team Feedback](docs/spl_team.png) | ![FIRST Scoring Overview](docs/first_overview.png) |
| :--: | :--: |
| SPL 2026 — Team feedback sheet (3 awards, single page) | FTC DECODE 2025-26 — Scoring overview (7 awards, 30 teams) |

| ![FIRST Team Feedback Page 1](docs/first_team_p1.png) | ![FIRST Team Feedback Page 2](docs/first_team_p2.png) |
| :--: | :--: |
| FTC DECODE 2025-26 — Team feedback sheet (page 1/2) | FTC DECODE 2025-26 — Team feedback sheet (page 2/2) |

## Quick start

```bash
pip install segno
python generate_feedback.py config.json scoring_sheet.csv
# Open feedback_sheets.html in a browser and print to PDF or paper
```

## Configuration

### Config file (JSON)

```json
{
  "title": "SPL 2026",
  "max_score": 5,
  "qr_url": "https://wiki.teamclockworks.ro/en/spl-rules",
  "qr_label": "Scan for full\ncriteria descriptions",
  "awards": {
    "Control": [
      { "name": "Software overview", "required": true, "slug": "C1" },
      { "name": "Sensor input", "required": true, "slug": "C2" },
      { "name": "Advanced algorithms", "required": false, "slug": "C3" }
    ],
    "Design": [
      { "name": "Elegance and efficiency", "required": true, "slug": "D1" },
      { "name": "Aesthetic identity", "required": false, "slug": "D2" }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `title` | Competition name, shown in headers and footers |
| `max_score` | Maximum score per criterion (used for bar chart scaling) |
| `qr_url` | URL encoded in the QR code |
| `qr_label` | Label text next to the QR code (`\n` for line breaks) |
| `awards` | Ordered dict of award names to arrays of criteria |
| `awards.*.name` | Criterion display name |
| `awards.*.required` | `true` for required criteria (black badge), `false` for encouraged (outline badge) |
| `awards.*.slug` | CSV column name for this criterion's score (e.g. `C1`, `D3`, `I2`) |

### Scoring CSV

The CSV must have columns `Team`, `C1` through `CN` (one per criterion across all awards, in order), and optionally `Notes`:

```csv
Team,C1,C2,C3,D1,D2,Notes
15989,4,2.5,4.5,3,4.5,
21087,5,4.5,5,5,4,Strong overall
```

Each column name must match a `slug` defined in the config. The ordering of columns in the CSV does not matter — scores are mapped by slug, not by position.

## Features

### Top-3 podium highlights

The three highest-scoring teams per award are highlighted in the scoring overview with inverted cells (black background, white text) and placement numbers. Ties share the same placement.

### Automatic pagination

Team feedback sheets are automatically paginated based on estimated content height. Award sections are never split across pages — if an award doesn't fit on the current page, it moves to the next one. Each page carries its own header, footer, and page indicator (e.g., "Feedback sheet (1/2)").

### Print-optimized design

- Grayscale-only palette for reliable photocopying
- A4 page dimensions with proper margins
- `print-color-adjust: exact` ensures bar charts, badges, and podium highlights print correctly
- `page-break-after: always` for clean page separation

## Generating screenshots

For documentation or previews, use `docs/take_screenshots.py` with [Playwright](https://playwright.dev/python/):

```bash
pip install playwright
playwright install chromium
python docs/take_screenshots.py
```

This renders the HTML in headless Chromium and saves specific pages as PNGs in `docs/`.

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0).
