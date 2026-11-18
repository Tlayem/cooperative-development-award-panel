#!/usr/bin/env python3
"""Build the award file, the county x fiscal-year x programme panel, and the state companion table.

Reads  data/raw/usaspending/*PrimeTransactions*.csv
Writes data/processed/cdap_awards.csv, cdap_county_fy.csv, cdap_state_fy.csv, build_log.json
"""
import json
import re
import sys

import numpy as np
import pandas as pd

from common import (REF, CT_PLANNING_REGIONS, FY_END, FY_START, MULTI_SCOPES, OUT, PROGRAMMES, RAW,
                    RECODE_TO_2020, UNALLOCATABLE, VERSION, CORE_SUBPROGRAMMES, county_frame, fiscal_year,
                    states, subprogramme)

LOG = {"version": VERSION}


def pick(df, *cands, required=False):
    for c in cands:
        if c in df.columns:
            return df[c]
    if required:
        sys.exit(f"None of the expected columns {cands} found. Columns: {list(df.columns)[:40]}...")
    return pd.Series(pd.NA, index=df.index, dtype="object")


def clean(s):
    s = s.astype("string").str.strip()
    return s.mask(s.isin(["", "nan", "NaN", "None"]))


def norm_listing(s):
    s = clean(s).str.extract(r"(\d{2})\.?(\d{3})")
    return (s[0] + "." + s[1]).astype("string")


def read_transactions():
    files = sorted(RAW.glob("*PrimeTransactions*.csv"))
    if not files:
        sys.exit(f"No *PrimeTransactions*.csv in {RAW}. Run code/01_ingest.py first.")
    df = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, low_memory=False) for f in files],
                   ignore_index=True)
    LOG["transaction_files"] = [f.name for f in files]
    LOG["n_raw_rows"] = len(df)
    return df


def county_fips(df, prefix, st, alt):
    """Return 5-digit county FIPS and 2-digit state FIPS.

    Current USAspending downloads carry `prime_award_transaction_<alt>_county_fips_code`; some values arrive
    float-formatted ("19169.0") or as state + unpadded county ("5015.0" = VT 50 + 015). Those are repaired
    using the row's state FIPS. Older layouts with a 3-digit county code are also handled.
    """
    five = clean(pick(df, f"prime_award_transaction_{alt}_county_fips_code", f"{prefix}_county_fips_code"))
    sfips = clean(pick(df, f"prime_award_transaction_{alt}_state_fips_code", f"{prefix}_state_fips_code"))
    scode = clean(pick(df, f"{prefix}_state_code"))
    sfips = sfips.fillna(scode.map(dict(zip(st.postal, st.fips)))).str.zfill(2)
    five = five.str.replace(r"\.0+$", "", regex=True)
    ok5 = five.str.fullmatch(r"\d{5}", na=False)
    short = five.str.fullmatch(r"\d{3,4}", na=False) & sfips.notna()
    rest = pd.Series([f[len(s_):] if isinstance(f, str) and isinstance(s_, str) and f.startswith(s_) else None
                      for f, s_ in zip(five, sfips)], index=five.index, dtype="object")
    repaired = (sfips + rest.str.zfill(3)).where(short & rest.notna() & rest.str.len().between(1, 3))
    LOG[f"{alt}_county_codes_repaired"] = int(repaired.notna().sum())
    cty = clean(pick(df, f"{prefix}_county_code"))
    cty = cty.where(cty.str.fullmatch(r"\d{1,3}", na=False)).str.zfill(3)
    out = five.where(ok5).fillna(repaired).fillna(sfips + cty)
    return out, sfips


def name_fallback(fips, sfips, names, frame):
    """Where the code is not in the frame, look the county up by state + county name."""
    key = lambda n: n.astype("string").str.upper().str.replace(r"\b(COUNTY|PARISH|BOROUGH|CENSUS AREA|CITY AND BOROUGH|MUNICIPALITY)\b", "", regex=True).str.replace(r"[^A-Z]", "", regex=True)
    fr = frame.assign(k=frame.state_fips + "|" + key(frame.county_name))
    fr = fr[~fr.k.duplicated(keep=False)]           # ambiguous names (e.g. a county and a city) are not used
    lut = dict(zip(fr.k, fr.county_fips))
    bad = ~fips.isin(set(frame.county_fips)) & ~fips.isin(RECODE_TO_2020) & names.notna()
    look = (sfips + "|" + key(names)).map(lut)
    filled = fips.where(~(bad & look.notna()), look)
    return filled, int((bad & look.notna()).sum())


def harmonise(fips, frame_set):
    """Map county FIPS to Census 2020 vintage; return (county_fips_2020, status)."""
    out = fips.copy()
    status = pd.Series("missing", index=fips.index, dtype="object")
    rec = fips.isin(RECODE_TO_2020)
    out[rec] = fips[rec].map(RECODE_TO_2020)
    status[fips.notna()] = "invalid"
    status[out.isin(frame_set)] = "matched"
    status[rec] = "recoded"
    status[fips.isin(UNALLOCATABLE)] = "split_unallocatable"
    status[fips.isin(CT_PLANNING_REGIONS)] = "ct_planning_region"
    status[fips.str[:2].isin(["60", "66", "69", "72", "74", "78"]).fillna(False)] = "territory"
    out = out.where(status.isin(["matched", "recoded"]))
    return out, status


def main():
    st = states()
    frame = county_frame()
    fset = set(frame.county_fips)
    LOG["n_frame_counties"] = len(frame)

    df = read_transactions()
    df["listing"] = norm_listing(pick(df, "cfda_number", "assistance_listing_number",
                                      "prime_award_transaction_cfda_number", required=True))
    LOG["listing_counts_raw"] = df["listing"].value_counts(dropna=False).to_dict()
    # R14: actions filed under another listing (in practice 10.352) on an award that has 10.771/10.871 actions
    # are corrections to that award (e.g. a value-added grant first filed under 10.771, then moved out).
    # They are kept, credited to the award's own programme, and flagged. All other rows are dropped.
    akey = clean(pick(df, "assistance_award_unique_key")).fillna(clean(pick(df, "award_id_fain")))
    in_prog = df["listing"].isin(PROGRAMMES)
    corr = ~in_prog & akey.isin(set(akey[in_prog].dropna()))
    df["other_listing_action"] = corr.astype(int)
    df["original_listing"] = df["listing"]
    LOG["n_in_programmes"] = int(in_prog.sum())
    LOG["n_other_listing_corrections"] = int(corr.sum())
    df = df[in_prog | corr].copy()

    cdi = clean(pick(df, "correction_delete_indicator_code", "correction_delete_indicatr")).str.upper().fillna("")
    LOG["n_delete_flag_dropped"] = int((cdi == "D").sum())
    df = df[(cdi != "D").to_numpy(dtype=bool)]

    key = clean(pick(df, "assistance_transaction_unique_key"))
    df["award_key"] = clean(pick(df, "assistance_award_unique_key")).fillna(clean(pick(df, "award_id_fain")))
    df["fain"] = clean(pick(df, "award_id_fain"))
    df["mod"] = clean(pick(df, "modification_number")).fillna("")
    df["action_date"] = pd.to_datetime(clean(pick(df, "action_date", required=True)), errors="coerce")
    df["amount"] = pd.to_numeric(clean(pick(df, "federal_action_obligation", required=True)), errors="coerce").fillna(0.0)
    df["action_type"] = clean(pick(df, "action_type_code")).str.upper()
    tkey = key.fillna(df["award_key"] + "|" + df["mod"] + "|" + df["action_date"].astype(str) + "|" + df["amount"].astype(str))
    before = len(df)
    df = df[~tkey.duplicated()].copy()
    LOG["n_duplicate_transactions_dropped"] = before - len(df)
    LOG["n_missing_award_key"] = int(df["award_key"].isna().sum())
    df = df[df["award_key"].notna()]
    # credit corrections to the programme of the award's own (10.771/10.871) actions
    own = df[df["other_listing_action"] == 0].sort_values(["award_key", "action_date", "mod"]).groupby("award_key")["listing"].first()
    df.loc[df["other_listing_action"] == 1, "listing"] = df.loc[df["other_listing_action"] == 1, "award_key"].map(own)
    LOG["other_listing_correction_amount"] = round(float(df.loc[df["other_listing_action"] == 1, "amount"].sum()), 2)
    LOG["total_listing_only_all_years"] = round(float(df.loc[df["other_listing_action"] == 0, "amount"].sum()), 2)

    fy = pd.to_numeric(clean(pick(df, "action_date_fiscal_year")), errors="coerce").astype("Int64")
    df["fy"] = fy.fillna(fiscal_year(df["action_date"]))
    LOG["fy_counts_all"] = {str(k): int(v) for k, v in df["fy"].value_counts(dropna=False).sort_index().items()}

    # recipient and place-of-performance locations, per transaction
    df["rec_fips_raw"], df["rec_state_fips"] = county_fips(df, "recipient", st, "recipient")
    df["pop_fips_raw"], df["pop_state_fips"] = county_fips(df, "primary_place_of_performance", st, "place_of_performance")
    df["rec_fips_raw"], LOG["rec_county_name_fallback"] = name_fallback(
        df["rec_fips_raw"], df["rec_state_fips"], clean(pick(df, "recipient_county_name")), frame)
    df["pop_fips_raw"], LOG["pop_county_name_fallback"] = name_fallback(
        df["pop_fips_raw"], df["pop_state_fips"], clean(pick(df, "primary_place_of_performance_county_name")), frame)
    df["rec_country"] = clean(pick(df, "recipient_country_code")).str.upper()
    df["pop_country"] = clean(pick(df, "primary_place_of_performance_country_code")).str.upper()
    df["pop_scope"] = clean(pick(df, "primary_place_of_performance_scope")).str.upper()
    df["recipient_uei"] = clean(pick(df, "recipient_uei"))
    df["recipient_duns"] = clean(pick(df, "recipient_duns"))
    df["recipient_name"] = clean(pick(df, "recipient_name", "recipient_name_raw"))
    df["recipient_city"] = clean(pick(df, "recipient_city_name"))
    df["recipient_state"] = clean(pick(df, "recipient_state_code"))
    df["recipient_zip5"] = clean(pick(df, "recipient_zip_code", "recipient_zip_4_code")).str[:5]
    df["pop_state"] = clean(pick(df, "primary_place_of_performance_state_code"))
    df["assistance_type"] = clean(pick(df, "assistance_type_code"))
    df["business_types"] = clean(pick(df, "business_types_description"))
    df["permalink"] = clean(pick(df, "usaspending_permalink"))
    df["description"] = clean(pick(df, "prime_award_base_transaction_description")).fillna(
        clean(pick(df, "transaction_description", "award_description")))
    df["rec_id"] = df["recipient_uei"].fillna(df["recipient_duns"]).fillna(df["recipient_name"].str.upper())

    # ---- award level: location taken from the base (earliest) action, falling back to later actions
    df = df.sort_values(["award_key", "action_date", "mod"])
    first = df.groupby("award_key").first()          # first non-null per column, in date order
    base = df[df["other_listing_action"] == 0].groupby("award_key").head(1).set_index("award_key")
    g = df.groupby("award_key")
    aw = pd.DataFrame({
        "award_key": first.index,
        "fain": first["fain"],
        "assistance_listing": base["listing"],
        "programme": base["listing"].map(lambda x: PROGRAMMES[x][0]),
        "n_listings_on_award": g["original_listing"].nunique(),
        "n_other_listing_actions": g["other_listing_action"].sum(),
        "other_listing_amount": df.assign(x=df["amount"] * df["other_listing_action"]).groupby("award_key")["x"].sum().round(2),
        "recipient_name": first["recipient_name"],
        "recipient_uei": first["recipient_uei"],
        "recipient_duns": first["recipient_duns"],
        "recipient_id": first["rec_id"],
        "recipient_city": first["recipient_city"],
        "recipient_state": first["recipient_state"],
        "recipient_zip5": first["recipient_zip5"],
        "recipient_country": first["rec_country"],
        "rec_fips_raw": first["rec_fips_raw"],
        "rec_state_fips": first["rec_state_fips"],
        "pop_scope": first["pop_scope"],
        "pop_state": first["pop_state"],
        "pop_country": first["pop_country"],
        "pop_fips_raw": first["pop_fips_raw"],
        "pop_state_fips": first["pop_state_fips"],
        "first_action_date": g["action_date"].min().dt.date,
        "last_action_date": g["action_date"].max().dt.date,
        "first_action_fy": g["fy"].min(),
        "base_action_type": base["action_type"],
        "base_mod": base["mod"],
        "n_actions": g.size(),
        "net_obligation": g["amount"].sum().round(2),
        "assistance_type": first["assistance_type"],
        "business_types": first["business_types"],
        "usaspending_permalink": first["permalink"],
        "award_description": first["description"],
    }).reset_index(drop=True)
    aw["subprogramme"] = [subprogramme(l, d) for l, d in zip(aw["assistance_listing"], aw["award_description"])]
    aw["core_coop_dev"] = aw["subprogramme"].isin(CORE_SUBPROGRAMMES).astype(int)
    LOG["n_awards_by_subprogramme"] = aw["subprogramme"].value_counts().to_dict()
    aw["aggregate_record"] = aw["award_key"].str.startswith("ASST_AGG").fillna(False).astype(int)
    new_type = aw["base_action_type"].str.startswith("A").fillna(False)
    no_type = aw["base_action_type"].isna() & aw["base_mod"].isin(["", "0", "00", "000", "0000"])
    # R13: an award whose actions net to exactly $0 (made and fully cancelled) is not counted as a new award
    aw["fully_deobligated"] = (aw["net_obligation"].abs() < 0.005).astype(int)
    aw["new_in_window"] = (new_type | no_type) & aw["first_action_fy"].between(FY_START, FY_END) \
        & (aw["aggregate_record"] == 0) & (aw["fully_deobligated"] == 0)
    LOG["n_fully_deobligated"] = int(aw["fully_deobligated"].sum())

    aw["rec_county_fips"], aw["rec_county_status"] = harmonise(aw["rec_fips_raw"], fset)
    aw.loc[aw["recipient_country"].notna() & ~aw["recipient_country"].isin(["USA", "US"]), "rec_county_status"] = "non_us"
    aw.loc[aw["rec_county_status"] == "non_us", "rec_county_fips"] = pd.NA
    aw["pop_county_fips"], aw["pop_county_status"] = harmonise(aw["pop_fips_raw"], fset)

    # R11: verified corrections to USAspending county codes (data/reference/county_overrides.csv).
    # Each row names the award, the basis (rec/pop), the code it replaces and the evidence.
    aw["county_override"] = 0
    ov_path = REF / "county_overrides.csv"
    LOG["county_overrides_applied"] = []
    if ov_path.exists():
        ov = pd.read_csv(ov_path, dtype=str)
        for r in ov.itertuples():
            for basis in str(r.basis).split("+"):
                hit = (aw["award_key"] == r.award_key) & (aw[f"{basis}_county_fips"] == r.from_fips)
                if hit.any():
                    aw.loc[hit, f"{basis}_county_fips"] = r.to_fips
                    aw.loc[hit, f"{basis}_county_status"] = "verified_override"
                    aw.loc[hit, "county_override"] = 1
                    LOG["county_overrides_applied"].append(f"{r.award_key} {basis} {r.from_fips}->{r.to_fips}")
                else:
                    LOG["county_overrides_applied"].append(f"NOT APPLIED: {r.award_key} {basis} (code is no longer {r.from_fips})")
    multi = aw["pop_scope"].isin(MULTI_SCOPES).fillna(False).astype(bool)
    aw.loc[multi, "pop_county_status"] = "multi_county_or_statewide"
    aw.loc[multi, "pop_county_fips"] = pd.NA
    aw["pop_multi_flag"] = multi.astype(int)
    aw["recipient_territory_flag"] = pd.to_numeric(aw["rec_state_fips"], errors="coerce").gt(56).fillna(False).astype(int)
    LOG["n_awards"] = len(aw)
    LOG["n_awards_by_programme"] = aw["programme"].value_counts().to_dict()
    LOG["n_awards_mixed_listing"] = int((aw["n_listings_on_award"] > 1).sum())
    LOG["rec_county_status"] = aw["rec_county_status"].value_counts().to_dict()
    LOG["pop_county_status"] = aw["pop_county_status"].value_counts().to_dict()
    LOG["pop_scope_counts"] = aw["pop_scope"].value_counts(dropna=False).to_dict()

    # ---- transaction -> award location (all of an award's dollars follow the award's location)
    tx = df[df["fy"].between(FY_START, FY_END)].merge(
        aw[["award_key", "programme", "recipient_id", "rec_county_fips", "pop_county_fips",
            "rec_state_fips", "pop_state_fips", "new_in_window", "first_action_fy", "core_coop_dev",
            "aggregate_record"]],
        on="award_key", how="left", suffixes=("_tx", ""))
    LOG["n_transactions_in_window"] = len(tx)
    LOG["n_transactions_outside_window"] = int(len(df) - len(tx))
    tx["is_new"] = tx["new_in_window"] & (tx["fy"] == tx["first_action_fy"])
    # new awards are counted with nunique, so each is counted once in its first fiscal year
    # aggregate records (one row per county for many individual recipients) are not counted as recipients
    tx["recipient_id"] = tx["recipient_id"].where(tx["aggregate_record"] == 0)
    tx["award_if_new"] = tx["award_key"].where(tx["is_new"])

    def agg(basis):
        c = f"{basis}_county_fips"
        core = tx["core_coop_dev"] == 1
        t = tx[tx[c].notna()].assign(core_amt=tx["amount"].where(core, 0.0),
                                     core_key=tx["award_key"].where(core),
                                     core_new=tx["award_if_new"].where(core))
        a = t.groupby([c, "fy", "programme"]).agg(
            new_awards=("award_if_new", "nunique"),
            actions=("amount", "size"),
            obligations=("amount", "sum"),
            awards_active=("award_key", "nunique"),
            recipients=("recipient_id", "nunique"),
            core_new_awards=("core_new", "nunique"),
            core_awards_active=("core_key", "nunique"),
            core_obligations=("core_amt", "sum"),
        ).reset_index().rename(columns={c: "county_fips"})
        return a.rename(columns={k: f"{basis}_{k}" for k in
                                 ["new_awards", "actions", "obligations", "awards_active", "recipients",
                                  "core_new_awards", "core_awards_active", "core_obligations"]})

    years = range(FY_START, FY_END + 1)
    progs = [v[0] for v in PROGRAMMES.values()]
    grid = frame.merge(pd.DataFrame({"fy": list(years)}), how="cross").merge(pd.DataFrame({"programme": progs}), how="cross")
    panel = grid.merge(agg("rec"), on=["county_fips", "fy", "programme"], how="left") \
                .merge(agg("pop"), on=["county_fips", "fy", "programme"], how="left")
    for col in panel.columns:
        if col.startswith(("rec_", "pop_")):
            panel[col] = panel[col].fillna(0)
            panel[col] = panel[col].round(2) if col.endswith("obligations") else panel[col].astype(int)
    panel["assistance_listing"] = panel["programme"].map({v[0]: k for k, v in PROGRAMMES.items()})
    panel["rec_any_award"] = (panel["rec_awards_active"] > 0).astype(int)
    panel["pop_any_award"] = (panel["pop_awards_active"] > 0).astype(int)
    order = ["county_fips", "state_fips", "state", "county_name", "fy", "programme", "assistance_listing",
             "rec_new_awards", "rec_actions", "rec_awards_active", "rec_recipients", "rec_obligations", "rec_any_award",
             "rec_core_new_awards", "rec_core_awards_active", "rec_core_obligations",
             "pop_new_awards", "pop_actions", "pop_awards_active", "pop_recipients", "pop_obligations", "pop_any_award",
             "pop_core_new_awards", "pop_core_awards_active", "pop_core_obligations"]
    panel = panel[order].sort_values(["county_fips", "fy", "programme"])
    LOG["n_panel_rows"] = len(panel)

    # ---- state x FY companion: totals and what could not be put in a county
    def state_side(basis):
        sf = f"{basis}_state_fips"
        alloc = tx[f"{basis}_county_fips"].notna()
        t = tx.assign(amt_in=tx["amount"].where(alloc, 0.0), key_out=tx["award_key"].where(~alloc),
                      core_all=tx["amount"].where(tx["core_coop_dev"] == 1, 0.0),
                      **{sf: tx[sf].fillna("unknown")})
        a = t.groupby([sf, "fy", "programme"]).agg(**{
            f"{basis}_obligations_total": ("amount", "sum"),
            f"{basis}_obligations_in_counties": ("amt_in", "sum"),
            f"{basis}_awards_active": ("award_key", "nunique"),
            f"{basis}_awards_not_in_county": ("key_out", "nunique"),
            f"{basis}_core_obligations_total": ("core_all", "sum"),
        }).reset_index().rename(columns={sf: "state_fips"})
        a[f"{basis}_obligations_not_in_county"] = a[f"{basis}_obligations_total"] - a[f"{basis}_obligations_in_counties"]
        return a
    stt = state_side("rec").merge(state_side("pop"), on=["state_fips", "fy", "programme"], how="outer")
    stt = stt.merge(st.rename(columns={"fips": "state_fips", "postal": "state", "name": "state_name"}), on="state_fips", how="left")
    value_cols = [c for c in stt.columns if c.startswith(("rec_", "pop_"))]
    stt[value_cols] = stt[value_cols].fillna(0)
    for c in value_cols:
        stt[c] = stt[c].round(2) if "obligations" in c else stt[c].astype(int)
    stt = stt[["state_fips", "state", "state_name", "fy", "programme"] + value_cols].sort_values(["state_fips", "fy", "programme"])

    LOG["total_obligations_in_window"] = round(float(tx["amount"].sum()), 2)
    LOG["total_obligations_rec_counties"] = round(float(panel["rec_obligations"].sum()), 2)
    LOG["total_obligations_pop_counties"] = round(float(panel["pop_obligations"].sum()), 2)

    keep = ["award_key", "fain", "assistance_listing", "programme", "recipient_name", "recipient_uei", "recipient_duns",
            "recipient_city", "recipient_state", "recipient_zip5", "rec_county_fips", "rec_county_status",
            "recipient_territory_flag", "county_override", "pop_scope", "pop_state", "pop_county_fips", "pop_county_status", "pop_multi_flag",
            "subprogramme", "core_coop_dev", "aggregate_record", "fully_deobligated", "award_description",
            "first_action_date", "last_action_date", "first_action_fy", "new_in_window", "n_actions", "net_obligation",
            "n_listings_on_award", "n_other_listing_actions", "other_listing_amount", "assistance_type", "business_types", "usaspending_permalink"]
    aw = aw[keep].sort_values(["first_action_date", "award_key"])
    aw["new_in_window"] = aw["new_in_window"].astype(int)

    OUT.mkdir(parents=True, exist_ok=True)
    aw.to_csv(OUT / "cdap_awards.csv", index=False)
    panel.to_csv(OUT / "cdap_county_fy.csv", index=False)
    stt.to_csv(OUT / "cdap_state_fy.csv", index=False)
    def _keys(o):
        if isinstance(o, dict):
            return {("(blank)" if pd.isna(k) else str(k)): _keys(v) for k, v in o.items()}
        return o
    (OUT / "build_log.json").write_text(json.dumps(_keys(LOG), indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: LOG[k] for k in ["n_raw_rows", "n_in_programmes", "n_awards", "n_panel_rows",
                                          "total_obligations_in_window"]}, indent=2))


if __name__ == "__main__":
    main()
