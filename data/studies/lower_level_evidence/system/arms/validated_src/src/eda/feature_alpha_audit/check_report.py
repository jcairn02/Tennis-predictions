"""Check generated local links and render the report in a disposable headless browser."""
import json
import argparse
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/studies/feature_alpha_audit/report.html"
OUT = ROOT / "data/studies/feature_alpha_audit"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href")


def main():
    parser_args = argparse.ArgumentParser()
    parser_args.add_argument("--document", default=str(DOC))
    parser_args.add_argument("--output-dir", default=str(OUT))
    args = parser_args.parse_args()
    doc, out = Path(args.document).resolve(), Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    parser = Links()
    parser.feed(doc.read_text(encoding="utf-8"))
    local = [p for p in parser.links if not p.startswith(("https://", "http://", "#"))]
    missing = [p for p in local if not (doc.parent / p.split("#", 1)[0]).exists()]
    assert not missing, missing
    checks = {"local_links_checked": len(local), "missing_local_links": missing, "views": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        for name, width, height in (("desktop", 1440, 1100), ("mobile", 390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(doc.as_uri())
            page.screenshot(path=str(out / f"report_{name}.png"))
            record = page.evaluate("""() => ({title: document.title,
                tables: document.querySelectorAll('table').length,
                pageWidth: document.documentElement.scrollWidth,
                viewportWidth: innerWidth,
                hasInvalidNumber: /\\b(?:NaN|undefined)\\b/.test(document.body.innerText)})""")
            assert record["pageWidth"] <= record["viewportWidth"], record
            assert not record["hasInvalidNumber"], record
            record["view"] = name
            checks["views"].append(record)
        browser.close()
    (out / "report_check.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
