#!/usr/bin/env python3
"""Render feedback_sheets.html pages to PNG for README documentation."""
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

DOCS_DIR = Path(__file__).parent
PROJECT_DIR = DOCS_DIR.parent


def capture(config_name, config_file, csv_file, pages_to_capture):
    """Generate HTML then capture specific pages as PNGs."""
    subprocess.run(
        [sys.executable, str(PROJECT_DIR / "generate_feedback.py"), config_file, csv_file],
        check=True,
    )
    html_path = PROJECT_DIR / "feedback_sheets.html"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")

        # Each .page div is a separate A4 page
        page_divs = page.query_selector_all(".page")
        print(f"  {config_name}: found {len(page_divs)} pages")

        for page_idx, label in pages_to_capture:
            if page_idx < len(page_divs):
                el = page_divs[page_idx]
                out = DOCS_DIR / f"{config_name}_{label}.png"
                el.screenshot(path=str(out))
                print(f"  Saved {out.name}")

        browser.close()


if __name__ == "__main__":
    # SPL: manufactured sample data — page 0 = summary, page 1 = first team sheet
    capture("spl", str(PROJECT_DIR / "config.json"), str(DOCS_DIR / "sample_spl.csv"), [
        (0, "overview"),
        (1, "team"),
    ])
    # FIRST: page 0 = summary p1, page 1 = summary p2, page 2 = team sheet p1, page 3 = team sheet p2
    capture("first", str(PROJECT_DIR / "config_first.json"), str(PROJECT_DIR / "scoring_sheet_first.csv"), [
        (0, "overview"),
        (2, "team_p1"),
        (3, "team_p2"),
    ])
