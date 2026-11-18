#!/usr/bin/env python3
"""QA report and stats file. Writes data/processed/qa_report.txt and stats.json.

Every number quoted in the README, the Zenodo description or a descriptor comes from stats.json.
"""
import json

import pandas as pd

from common import FY_END, FY_START, OUT, RAW, VERSION

SEED = 20261113


def main():
    log = json.loads((OUT / "build_log.json").read_text(encoding="utf-8"))
    aw = pd.read_csv(OUT / "cdap_awards.csv", dtype={"rec_county_fips": str, "pop_county_fips": str, "recipient_zip5": str})
    p = pd.read_csv(OUT / "cdap_county_fy.csv", dtype={"county_fips": str, "state_fips": str})
    s = pd.read_csv(OUT / "cdap_state_fy.csv", dtype={"state_fips": str})
    L, fails = [], []

    def check(name, ok, detail=""):
        L.append(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
        if not ok:
            fails.append(name)

    L += [f"Cooperative Development Award Panel v{VERSION} — QA report", "=" * 60, "",
          "1. Row counts", f"   raw transaction rows ............ {log['n_raw_rows']:,}",
          f"   in 10.771 / 10.871 .............. {log['n_in_programmes']:,}",
          f"   other-listing corrections kept .. {log.get('n_other_listing_corrections', 0):,}",
          f"   delete-flag rows dropped ........ {log['n_delete_flag_dropped']:,}",
          f"   duplicate transactions dropped .. {log['n_duplicate_transactions_dropped']:,}",
          f"   missing award key dropped ....... {log['n_missing_award_key']:,}",
          f"   transactions in FY{FY_START}-FY{FY_END} ... {log['n_transactions_in_window']:,}",
          f"   transactions outside window ..... {log['n_transactions_outside_window']:,}",
          f"   awards .......................... {log['n_awards']:,}  {log['n_awards_by_programme']}",
          f"   awards new in window ............ {int(aw.new_in_window.sum()):,}",
          f"   awards with >1 listing .......... {log['n_awards_mixed_listing']}",
          f"   panel rows ...................... {log['n_panel_rows']:,}", "",
          "   Listing counts in raw files (other listings are dropped):"]
    L += [f"     {k}: {v:,}" for k, v in log["listing_counts_raw"].items()]
    L += ["", "2. County assignment (awards)", "   recipient county:"]
    L += [f"     {k}: {v:,}" for k, v in log["rec_county_status"].items()]
    L += ["   place-of-performance county:"]
    L += [f"     {k}: {v:,}" for k, v in log["pop_county_status"].items()]
    L += ["   place-of-performance scope:"]
    L += [f"     {k}: {v:,}" for k, v in log["pop_scope_counts"].items()]
    unmatched = aw[aw.rec_county_status.isin(["invalid", "missing"])]
    L += ["", f"   Recipient county unmatched ({len(unmatched)}), first 25:"]
    L += [f"     {r.award_key} | {r.recipient_name} | {r.recipient_city}, {r.recipient_state}" for r in unmatched.head(25).itertuples()]

    # recipient county code vs the county name USAspending reports alongside it
    tx_files = sorted(RAW.glob("*PrimeTransactions*.csv"))
    if tx_files:
        from common import county_frame
        tx = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, usecols=lambda c: c in
                        ("assistance_award_unique_key", "recipient_county_name")) for f in tx_files])
        src = tx.drop_duplicates("assistance_award_unique_key").set_index("assistance_award_unique_key")["recipient_county_name"]
        fr = county_frame().set_index("county_fips")["county_name"].str.upper()
        a = aw[aw.rec_county_status.isin(["matched", "recoded"])]
        nm = a.award_key.map(src).fillna("").str.upper()
        fn = a.rec_county_fips.map(fr).fillna("")
        norm = lambda x: x.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.replace(r"[^A-Z]", "", regex=True)
        agree = [b.startswith(n[:5]) if n else True for n, b in zip(norm(nm), norm(fn))]
        keep = [(not x) for x in agree]
        mis = a[keep]
        L += ["", f"   Recipient county code vs reported county name: {len(mis)} disagreements of {len(a):,}"
              " (code kept; DC is reported as 'District of Columbia')"]
        L += [f"     {r.award_key} | {r.recipient_city}, {r.recipient_state} | code {r.rec_county_fips} = {fr.get(r.rec_county_fips)} | reported {src.get(r.award_key)}"
              for r in mis.itertuples() if r.recipient_state != "DC"]
    L += ["", f"   Aggregate records (ASST_AGG, many individual recipients in one county row): {int(aw.aggregate_record.sum())} "
          f"(${aw.loc[aw.aggregate_record == 1, 'net_obligation'].sum():,.0f}); kept in obligations, not counted as new awards or recipients"]
    L += ["", "   Verified county overrides (R11, data/reference/county_overrides.csv):"]
    L += [f"     {x}" for x in log.get("county_overrides_applied", [])] or ["     none"]
    check("every county override applied", not any(x.startswith("NOT APPLIED") for x in log.get("county_overrides_applied", [])))
    L += ["", f"   Fully deobligated awards (net $0, not counted as new): {int(aw.fully_deobligated.sum())}"]
    L += ["", "3. Checks"]
    check("panel is balanced (counties x FY x programmes)",
          len(p) == log["n_frame_counties"] * (FY_END - FY_START + 1) * 2 and not p.duplicated(["county_fips", "fy", "programme"]).any())
    tot = log["total_obligations_in_window"]
    check("state table total = in-window transaction total", abs(s.rec_obligations_total.sum() - tot) < 1 and abs(s.pop_obligations_total.sum() - tot) < 1)
    check("county + not-in-county = total (recipient basis)",
          abs(p.rec_obligations.sum() + s.rec_obligations_not_in_county.sum() - tot) < 1)
    check("county + not-in-county = total (place-of-performance basis)",
          abs(p.pop_obligations.sum() + s.pop_obligations_not_in_county.sum() - tot) < 1)
    # Benchmark read off the USAspending Advanced Search page on 2026-11-13 (same filters, Awarding Subagency chart):
    # Rural Business-Cooperative Service $277.64m + NIFA $13.80m = $291.44m net obligations, FY2008-FY2026.
    bench = 277.64e6 + 13.80e6
    lo = log.get("total_listing_only_all_years", tot)
    check("10.771/10.871 actions alone within 2% of USAspending search-page benchmark ($291.44m, 2026-11-13)",
          abs(lo - bench) / bench < 0.02, f"pipeline ${lo / 1e6:,.2f}m")
    L.append(f"[INFO] other-listing corrections (R14): {log.get('n_other_listing_corrections', 0)} actions, "
             f"${log.get('other_listing_correction_amount', 0):,.0f}; panel total after corrections ${tot / 1e6:,.2f}m")
    rec_share = p.rec_obligations.sum() / tot if tot else 0
    pop_share = p.pop_obligations.sum() / tot if tot else 0
    check("recipient basis puts >= 95% of dollars in a county", rec_share >= 0.95, f"{rec_share:.1%}")
    L.append(f"[INFO] place-of-performance basis puts {pop_share:.1%} of dollars in a county")
    neg = p[(p.rec_obligations < 0)]
    L.append(f"[INFO] county-years with net negative obligations (deobligations): {len(neg)}")
    big = aw[aw.net_obligation > 1_000_000]
    L.append(f"[INFO] awards above $1m net: {len(big)} (expected for ATTRA/AgMRC; check any COOP_CENTRE/SDGG ones)")
    L += [f"     {r.award_key} | {r.subprogramme} | {r.recipient_name} | ${r.net_obligation:,.0f}" for r in big.itertuples()]
    check("no core co-op development award above $1m net", big[big.core_coop_dev == 1].empty)
    L += ["", "   Sub-programme tags (awards):"]
    L += [f"     {k}: {v:,}" for k, v in aw.subprogramme.value_counts().items()]
    L += ["   Most common descriptions tagged COOP_CENTRE (review the keyword rules against these):"]
    L += [f"     {n:>4}  {d}" for d, n in aw.loc[aw.subprogramme == "COOP_CENTRE", "award_description"].fillna("(blank)").str[:90].value_counts().head(30).items()]

    # cross-check against award summaries if downloaded
    summ_files = sorted(RAW.glob("*PrimeAwardSummaries*.csv"))
    if summ_files:
        sm = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, low_memory=False) for f in summ_files])
        kcol = "assistance_award_unique_key" if "assistance_award_unique_key" in sm else None
        ocol = next((c for c in ["total_obligated_amount", "award_amount"] if c in sm), None)
        if kcol and ocol:
            sm[ocol] = pd.to_numeric(sm[ocol], errors="coerce")
            m = aw.merge(sm[[kcol, ocol]].drop_duplicates(kcol), left_on="award_key", right_on=kcol, how="left")
            found = m[ocol].notna().mean()
            diff = (m[ocol] - m.net_obligation).abs()
            agree = (diff[m[ocol].notna()] < 1).mean()
            check("awards found in award-summary file", found >= 0.98, f"{found:.1%}")
            L.append(f"[INFO] award total = summary total for {agree:.1%} of matched awards. The panel uses transactions "
                     "(10.771/10.871 plus R14 corrections on the same awards).")
            dd = m[(diff >= 1) & m[ocol].notna()]
            L.append(f"       {len(dd)} awards differ; summary minus transactions = ${(dd[ocol] - dd.net_obligation).sum():,.0f}.")
            if "cfda_numbers_and_titles" in sm:
                lst = m["award_key"].map(sm.drop_duplicates(kcol).set_index(kcol)["cfda_numbers_and_titles"])
                other = lst.str.contains(r"10\.352", na=False) & (diff >= 1)
                pre = (diff >= 1) & ~other
                L.append(f"       {int(other.sum())} of them still differ despite carrying 10.352 actions "
                         f"(${(m.loc[other, ocol] - m.loc[other, 'net_obligation']).sum():,.0f}).")
                L.append(f"       {int(pre.sum())} began before FY2008, so their base obligation is outside the window "
                         f"(${(m.loc[pre, ocol] - m.loc[pre, 'net_obligation']).sum():,.0f}).")
            L.append("       First 10:")
            L += [f"       {r.award_key} | transactions ${r.net_obligation:,.0f} | summary ${getattr(r, ocol):,.0f}" for r in dd.head(10).itertuples()]
    else:
        L.append("[INFO] no award-summary file; cross-check skipped")

    # spot checks
    L += ["", "4. Spot checks — open each permalink and confirm recipient, county and amount"]
    picks = []
    if len(aw):
        picks += [("largest award", aw.nlargest(1, "net_obligation")),
                  ("earliest award", aw.head(1)),
                  ("latest award", aw.tail(1)),
                  ("statewide performance", aw[aw.pop_multi_flag == 1].head(1)),
                  ("Tennessee award", aw[aw.recipient_state == "TN"].head(1)),
                  ("recoded/split county", aw[aw.rec_county_status.isin(["recoded", "split_unallocatable", "ct_planning_region"])].head(1)),
                  ("SDGG award", aw[aw.programme == "SDGG"].sample(min(1, (aw.programme == "SDGG").sum()), random_state=SEED)),
                  (f"random (seed {SEED})", aw.sample(min(5, len(aw)), random_state=SEED))]
    for label, d in picks:
        for r in d.itertuples():
            L.append(f"   [{label}] {r.award_key} | {r.programme} | {r.recipient_name} | {r.recipient_city}, {r.recipient_state} "
                     f"| rec county {r.rec_county_fips} ({r.rec_county_status}) | pop {r.pop_county_fips} ({r.pop_county_status}) "
                     f"| ${r.net_obligation:,.0f} | FY{r.first_action_fy} | {r.usaspending_permalink}")

    # stats
    win = s.groupby(["fy", "programme"]).rec_obligations_total.sum().rename("obl").to_frame().join(
        aw[aw.new_in_window == 1].groupby(["first_action_fy", "programme"]).size().rename("new").rename_axis(["fy", "programme"]), how="outer").fillna(0).reset_index()
    any_county = p.groupby("county_fips").rec_any_award.max()
    stats = {
        "version": VERSION, "fy_start": FY_START, "fy_end": FY_END,
        "n_awards": int(len(aw)), "n_awards_new_in_window": int(aw.new_in_window.sum()),
        "n_awards_by_programme": aw.programme.value_counts().to_dict(),
        "n_awards_by_subprogramme": aw.subprogramme.value_counts().to_dict(),
        "n_awards_core": int(aw.core_coop_dev.sum()),
        "total_core_obligations": round(float(s.rec_core_obligations_total.sum()), 2),
        "n_recipients": int(aw.loc[aw.aggregate_record == 0, "recipient_uei"].fillna(aw.recipient_name).nunique()),
        "n_aggregate_records": int(aw.aggregate_record.sum()),
        "n_fully_deobligated": int(aw.fully_deobligated.sum()),
        "n_other_listing_corrections": int(log.get("n_other_listing_corrections", 0)),
        "other_listing_correction_amount": log.get("other_listing_correction_amount", 0),
        "n_awards_with_corrections": int((aw.n_other_listing_actions > 0).sum()),
        "n_transactions": int(log["n_transactions_in_window"]),
        "total_obligations": round(tot, 2),
        "obligations_by_programme": {k: round(v, 2) for k, v in s.groupby("programme").rec_obligations_total.sum().items()},
        "share_dollars_in_county_recipient": round(rec_share, 4),
        "share_dollars_in_county_pop": round(pop_share, 4),
        "n_counties_frame": int(log["n_frame_counties"]),
        "n_counties_ever_recipient": int(any_county.sum()),
        "n_states_ever": int(s.loc[s.rec_obligations_total != 0, "state_fips"].nunique()),
        "n_panel_rows": int(len(p)),
        "obligations_by_fy_programme": {f"{r.fy}_{r.programme}": round(r.obl, 2) for r in win.itertuples()},
        "new_awards_by_fy_programme": {f"{r.fy}_{r.programme}": int(r.new) for r in win.itertuples()},
        "qa_failures": fails,
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    L += ["", f"QA failures: {len(fails)} {fails}"]
    (OUT / "qa_report.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-3:]))


if __name__ == "__main__":
    main()
