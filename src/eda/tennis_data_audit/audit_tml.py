"""Audit Tennis My Life's current public downloads, distinct from old GitHub copy."""
import concurrent.futures
import json
import sys
from audit_public_payloads import OUT, fetch, csv_audit

URLS = {"tml_catalog.json": "https://stats.tennismylife.org/api/data-files",
        "tml_github_readme.md":"https://raw.githubusercontent.com/Tennismylife/TML-Database/master/README.md"}
for name in ("2025.csv","2026.csv","2025_wta.csv","2026_wta.csv","2025_challenger.csv","2026_challenger.csv",
             "ongoing_tourneys.csv","wta_ongoing_tourneys.csv","ch_ongoing_tourney.csv","challenger_ongoing_tourneys.csv","atp_quali/2026_atp_quali.csv"):
    URLS["tml_"+name.replace("/","_")] = "https://stats.tennismylife.org/data/"+name


def main():
    if "--offline" in sys.argv:
        receipts = json.loads((OUT / "tml_audit.json").read_text())["receipts"]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda item:fetch(item,False),URLS.items()))
    audits = [csv_audit(OUT / "raw" / r["name"]) for r in receipts if "error" not in r and r["name"].endswith(".csv")]
    (OUT / "tml_audit.json").write_text(json.dumps({"receipts":receipts,"audits":audits},indent=2),encoding="utf-8")
    print(json.dumps({"errors":[r for r in receipts if "error" in r],"audits":[{k:v for k,v in a.items() if k in ("file","rows","tourney_date","requested_window_rows","duplicate_tourney_match_keys","invalid_width_rows")} for a in audits]},indent=2))


if __name__ == "__main__":
    main()
