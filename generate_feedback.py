#!/usr/bin/env python3
import csv
import io
import json
import math
import sys
from pathlib import Path

import segno

SCRIPT_DIR = Path(__file__).parent
SUMMARY_PAGE_SIZE = 20

# Height estimates (mm) for A4 pagination of team sheets
PAGE_CONTENT_H = 260  # usable height inside a page (A4 minus top/bottom padding & footer)
HEADER_H = 32         # team header block (title + team-id + QR + border + margin)
CAT_HEADER_H = 12     # award header bar + bottom margin
TABLE_HEAD_H = 6      # criteria table header row
CRIT_ROW_H = 8        # one criterion row (with wrapping buffer)
CAT_BOTTOM_H = 3      # criteria table bottom margin
NOTES_H = 16          # notes block


def load_config(path):
    with open(path) as f:
        return json.load(f)


def make_qr_svg(url):
    qr = segno.make(url)
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=2, border=1, dark="#222", light="#fff")
    return buf.getvalue().decode()


def mean(scores):
    return sum(scores) / len(scores) if scores else 0.0


def stddev(scores):
    n = len(scores)
    if n < 2:
        return 0.0
    m = mean(scores)
    return math.sqrt(sum((x - m) ** 2 for x in scores) / (n - 1))


def compute_rankings(teams, config):
    """Compute top-3 rankings per award.

    Returns dict: {award_name: {team_id: place}} where place is 1, 2, or 3.
    Ties share the same place; the next place is skipped accordingly.
    """
    rankings = {}
    for award_name in config["awards"]:
        team_avgs = []
        for team, scores_by_award, _notes in teams:
            avg = mean(scores_by_award[award_name])
            team_avgs.append((team, avg))
        team_avgs.sort(key=lambda x: x[1], reverse=True)

        award_ranks = {}
        prev_avg = None
        place = 0
        for i, (team, avg) in enumerate(team_avgs):
            if avg != prev_avg:
                place = i + 1
            if place > 3:
                break
            award_ranks[team] = place
            prev_avg = avg
        rankings[award_name] = award_ranks
    return rankings


def estimate_category_height(criteria_count):
    return CAT_HEADER_H + TABLE_HEAD_H + criteria_count * CRIT_ROW_H + CAT_BOTTOM_H


def paginate_awards(config, notes):
    """Split awards across pages so no page overflows A4.
    Returns list of lists of award names."""
    available = PAGE_CONTENT_H - HEADER_H
    pages = []
    current_page = []
    remaining = available

    for award_name, criteria_defs in config["awards"].items():
        h = estimate_category_height(len(criteria_defs))
        if current_page and h > remaining:
            pages.append(current_page)
            current_page = []
            remaining = available
        current_page.append(award_name)
        remaining -= h

    # If notes don't fit on the last page, push to a new one
    if notes and current_page and remaining < NOTES_H:
        pages.append(current_page)
        current_page = []

    if current_page:
        pages.append(current_page)

    return pages


def score_bar(score, max_score):
    pct = (score / max_score) * 100 if max_score else 0
    if pct >= 70:
        shade = "#333"
    elif pct >= 40:
        shade = "#777"
    else:
        shade = "#bbb"
    return f"""<div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%;background:{shade}"></div></div>"""


def render_category(award_name, criteria_defs, scores, max_score, cat_index,
                    placement=None):
    avg = mean(scores)
    sd = stddev(scores)
    cat_classes = ["control", "design", "innovate"]
    cls = cat_classes[cat_index % len(cat_classes)]

    placement_html = ""
    if placement:
        placement_html = f' <span class="podium-badge">#{placement}</span>'

    rows = ""
    for i, (crit, score) in enumerate(zip(criteria_defs, scores)):
        req = crit["required"]
        badge_cls = "required" if req else "encouraged"
        badge_text = "Required" if req else "Encouraged"
        rows += f"""
        <tr>
          <td class="crit-num">{i+1}</td>
          <td class="crit-name">{crit['name']} <span class="badge {badge_cls}">{badge_text}</span></td>
          <td class="crit-score">{score:g}</td>
          <td class="crit-bar">{score_bar(score, max_score)}</td>
        </tr>"""

    return f"""
      <div class="category">
        <div class="cat-header {cls}">{award_name} Award{placement_html}
          <span class="stats">Avg: {avg:.2f} &nbsp;|&nbsp; StdDev: {sd:.2f}</span>
        </div>
        <table class="criteria-table">
          <colgroup><col style="width:4%"><col style="width:51%"><col style="width:10%"><col style="width:35%"></colgroup>
          <tr class="table-head"><th>#</th><th>Criterion</th><th>Score</th><th></th></tr>
          {rows}
        </table>
      </div>"""


def render_summary(teams_data, config, qr_svg, rankings):
    """Render summary pages, splitting at SUMMARY_PAGE_SIZE teams each."""
    title = config.get("title", "SPL")
    max_score = config["max_score"]
    award_names = list(config["awards"].keys())

    hdr1 = '<th class="sum-team" rowspan="2">Team</th>'
    for name in award_names:
        hdr1 += f'<th colspan="2" class="sum-award">{name}</th>'
    hdr1 += '<th class="sum-notes" rowspan="2">Notes</th>'

    hdr2 = ""
    for _ in award_names:
        hdr2 += '<th class="sum-stat">Avg</th><th class="sum-stat">StdDev</th>'

    chunks = []
    for i in range(0, len(teams_data), SUMMARY_PAGE_SIZE):
        chunks.append(teams_data[i : i + SUMMARY_PAGE_SIZE])
    total_pages = len(chunks)

    pages = ""
    for page_idx, chunk in enumerate(chunks):
        body = ""
        for team, scores_by_award, notes in chunk:
            row = f'<td class="sum-team-val">{team}</td>'
            for name in award_names:
                scores = scores_by_award[name]
                avg = mean(scores)
                sd = stddev(scores)
                place = rankings.get(name, {}).get(team)
                if place:
                    row += f'<td class="sum-val podium">{avg:.1f} ({place})</td>'
                else:
                    row += f'<td class="sum-val">{avg:.1f}</td>'
                row += f'<td class="sum-val">{sd:.1f}</td>'
            notes_esc = notes if notes else ""
            row += f'<td class="sum-notes-val">{notes_esc}</td>'
            body += f"<tr>{row}</tr>\n"

        page_label = f"Scoring overview ({page_idx + 1}/{total_pages})" if total_pages > 1 else "Scoring overview"
        footer_text = f"{title} — Scores out of {max_score} — {page_label}"

        pages += f"""
    <div class="page">
      <div class="header">
        <div class="header-left">
          <div class="title">{title} — Scoring Overview</div>
        </div>
        <div class="qr-block"><div class="qr-label">{config.get("qr_label", "").replace(chr(10), "<br>")}</div><div class="qr">{qr_svg}</div></div>
      </div>
      <table class="summary-table">
        <thead>
          <tr>{hdr1}</tr>
          <tr>{hdr2}</tr>
        </thead>
        <tbody>
          {body}
        </tbody>
      </table>
      <div class="footer">{footer_text}</div>
    </div>"""

    return pages


def render_team(team, scores_by_award, notes, config, qr_svg, rankings):
    max_score = config["max_score"]
    title = config.get("title", "SPL")
    award_names = list(config["awards"].keys())

    award_pages = paginate_awards(config, notes)

    pages_html = ""
    for page_idx, page_award_names in enumerate(award_pages):
        categories_html = ""
        for award_name in page_award_names:
            cat_index = award_names.index(award_name)
            criteria_defs = config["awards"][award_name]
            scores = scores_by_award[award_name]
            categories_html += render_category(
                award_name, criteria_defs, scores, max_score, cat_index,
            )

        notes_html = ""
        if notes and page_idx == len(award_pages) - 1:
            notes_html = f"""<div class="notes"><strong>Notes:</strong> {notes}</div>"""

        pages_html += f"""
    <div class="page">
      <div class="header">
        <div class="header-left">
          <div class="title">{title} — Feedback Sheet</div>
          <div class="team-id">Team #{team}</div>
        </div>
        <div class="qr-block"><div class="qr-label">{config.get("qr_label", "").replace(chr(10), "<br>")}</div><div class="qr">{qr_svg}</div></div>
      </div>
      {categories_html}
      {notes_html}
      <div class="footer">{title} — Scores out of {max_score} — #{team} Feedback sheet{f" ({page_idx+1}/{len(award_pages)})" if len(award_pages) > 1 else ""}</div>
    </div>"""

    return pages_html


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #ddd; color: #111; }

.page {
  width: 210mm; min-height: 296mm; margin: 8mm auto; padding: 12mm 14mm;
  background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,0.15);
  page-break-after: always; position: relative;
}

.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6mm; border-bottom: 2.5pt solid #222; padding-bottom: 4mm; }
.header-left { flex: 1; }
.title { font-size: 18pt; font-weight: 700; color: #111; }
.team-id { font-size: 15pt; font-weight: 600; color: #444; margin-top: 1mm; }
.qr-block { flex-shrink: 0; margin-left: 4mm; display: flex; align-items: center; gap: 2mm; }
.qr-label { font-size: 8pt; color: #444; text-align: right; line-height: 1.4; padding: 0; }
.qr svg { width: 18mm; height: 18mm; }

.category { margin-bottom: 4mm; }
.cat-header {
  font-size: 11.5pt; font-weight: 700; padding: 2mm 4mm; margin-bottom: 1.5mm;
  display: flex; justify-content: space-between; align-items: center;
  border: 1pt solid #999; background: #f0f0f0; color: #111;
}
.cat-header.control { border-left: 5pt solid #111; }
.cat-header.design { border-left: 5pt solid #666; }
.cat-header.innovate { border-left: 5pt solid #aaa; }
.stats { font-size: 9.5pt; font-weight: 600; color: #333; }

.criteria-table { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-bottom: 3mm; table-layout: fixed; }
.criteria-table th,
.criteria-table td { text-align: left; padding: 2mm; }
.table-head th { color: #555; font-weight: 600; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.3pt; border-bottom: 1.5pt solid #aaa; }
.criteria-table td { border-bottom: 0.5pt solid #ddd; }
.crit-num { color: #888; }
.crit-name { color: #222; }
.crit-score { font-weight: 700; font-size: 11pt; color: #000; }
.crit-bar { padding-left: 0; }
.bar-bg { background: #e0e0e0; border-radius: 2px; height: 8px; width: 100%; }
.bar-fill { height: 100%; border-radius: 2px; }

.badge { font-size: 7pt; padding: 0.5mm 2mm; border-radius: 2px; margin-left: 2mm; vertical-align: middle; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2pt; }
.badge.required { background: #111; color: #fff; }
.badge.encouraged { background: #fff; color: #333; border: 1pt solid #888; }

/* Podium highlights (top 3 per award) */
.podium { background: #111; color: #fff; font-weight: 700; }
.podium-badge { background: #111; color: #fff; font-size: 8pt; padding: 0.5mm 2.5mm; border-radius: 2px; margin-left: 2mm; vertical-align: middle; font-weight: 700; }

.notes { margin: 4mm 0; padding: 3mm 4mm; background: #f5f5f5; border-left: 3pt solid #333; font-size: 9.5pt; color: #222; }

.footer { position: absolute; bottom: 8mm; left: 0; width: 100%; text-align: center; font-size: 8pt; color: #999; }

/* --- Summary table --- */
.summary-table { width: 100%; border-collapse: collapse; font-size: 9pt; margin-top: 4mm; }
.summary-table thead { background: #f0f0f0; }
.summary-table th, .summary-table td { border: 0.5pt solid #bbb; padding: 1.5mm 1.5mm; text-align: center; }
.sum-team { text-align: left; font-weight: 700; }
.sum-team-val { text-align: left; font-weight: 700; font-size: 10pt; }
.sum-award { font-size: 10pt; font-weight: 700; border-bottom: 1.5pt solid #888; }
.sum-stat { font-size: 7.5pt; text-transform: uppercase; color: #555; font-weight: 600; letter-spacing: 0.3pt; }
.sum-val { font-size: 9pt; font-variant-numeric: tabular-nums; }
.sum-notes, .sum-notes-val { text-align: left; font-size: 8pt; color: #444; }
.summary-table tbody tr:nth-child(even) { background: #f8f8f8; }

@media print {
  body { background: white; }
  .page { box-shadow: none; margin: 0; }
  @page { size: A4; margin: 0; }
  .bar-fill, .cat-header, .badge, .bar-bg, .summary-table thead,
  .summary-table tbody tr:nth-child(even), .podium, .podium-badge {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
"""


def main():
    config_path = SCRIPT_DIR / "config.json"
    csv_path = SCRIPT_DIR / "scoring_sheet.csv"

    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        csv_path = Path(sys.argv[2])

    config = load_config(config_path)

    # Build column ranges for each award: award -> (start_col, count)
    award_ranges = {}
    col = 1  # C1-based
    for award_name, criteria in config["awards"].items():
        count = len(criteria)
        award_ranges[award_name] = (col, count)
        col += count

    # Read CSV and split scores per award
    qr_svg = make_qr_svg(config["qr_url"])
    teams = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Team", "").strip():
                continue
            team = row["Team"]
            notes = row.get("Notes", "").strip()
            scores_by_award = {}
            for award_name, (start, count) in award_ranges.items():
                scores_by_award[award_name] = [
                    float(row[f"C{start + i}"]) for i in range(count)
                ]
            teams.append((team, scores_by_award, notes))

    rankings = compute_rankings(teams, config)

    summary = render_summary(teams, config, qr_svg, rankings)
    team_pages = "\n".join(
        render_team(team, scores, notes, config, qr_svg, rankings)
        for team, scores, notes in teams
    )
    pages = summary + "\n" + team_pages

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{config.get('title', 'Feedback')} Feedback Sheets</title>
<style>{CSS}</style>
</head>
<body>
{pages}
</body>
</html>"""

    out = SCRIPT_DIR / "feedback_sheets.html"
    out.write_text(html)
    print(f"Generated {out} with {len(teams)} team sheets")


if __name__ == "__main__":
    main()
