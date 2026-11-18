#!/usr/bin/env python3
"""Fill the README summary from stats.json (so prose cannot drift from data). --final drops the draft status."""
import json
import re
import sys

from common import OUT, ROOT

FINAL = "--final" in sys.argv


def m(x):
    return f"${x / 1e6:,.1f} million"


def main():
    s = json.loads((OUT / "stats.json").read_text(encoding="utf-8"))
    bp = s["n_awards_by_programme"]
    ob = s["obligations_by_programme"]
    block = "\n".join([
        f"- **{s['n_awards']:,} awards** ({bp.get('RCDG', 0):,} RCDG, {bp.get('SDGG', 0):,} SDGG) made through "
        f"{s['n_transactions']:,} obligation actions in FY{s['fy_start']}–FY{s['fy_end']}. "
        f"{s['n_awards_new_in_window']:,} of the awards are new within the window.",
        f"- **{m(s['total_obligations'])}** in net obligations (nominal): {m(ob.get('RCDG', 0))} RCDG and {m(ob.get('SDGG', 0))} SDGG.",
        f"- Core co-op development (co-op centres, minority-producer grants and SDGG): {s['n_awards_core']:,} awards, {m(s['total_core_obligations'])}. "
        "Sub-programme counts: " + ", ".join(f"{k} {v:,}" for k, v in s["n_awards_by_subprogramme"].items()) + ".",
        f"- {s['n_recipients']:,} distinct recipients in {s['n_states_ever']} states and territories. "
        f"{s['n_counties_ever_recipient']:,} of {s['n_counties_frame']:,} counties held an award at some point.",
        f"- {s['share_dollars_in_county_recipient']:.1%} of dollars are placed in a county by recipient location, "
        f"and {s['share_dollars_in_county_pop']:.1%} by place of performance. The remainder is territories, one foreign recipient, and records with no usable county.",
        f"- The panel has {s['n_panel_rows']:,} rows.",
    ])
    r = (ROOT / "README.md").read_text(encoding="utf-8")
    r = re.sub(r"<!-- STATS -->.*?<!-- /STATS -->", f"<!-- STATS -->\n{block}\n<!-- /STATS -->", r, flags=re.S)
    if FINAL:
        r = re.sub(r"<!-- STATUS -->.*?<!-- /STATUS -->",
                   f"<!-- STATUS -->\n**Status: released, v{s['version']}, FY{s['fy_start']}–FY{s['fy_end']}.**\n<!-- /STATUS -->",
                   r, flags=re.S)
    (ROOT / "README.md").write_text(r, encoding="utf-8")
    print("README summary updated", "final" if FINAL else "draft")


if __name__ == "__main__":
    main()
