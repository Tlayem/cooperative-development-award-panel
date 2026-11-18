"""Pipeline tests on a SYNTHETIC fixture (invented rows; not USAspending data).

Run:  python -m pytest -q tests/
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

COLS = ["assistance_transaction_unique_key", "assistance_award_unique_key", "award_id_fain", "modification_number",
        "federal_action_obligation", "action_date", "action_date_fiscal_year", "action_type_code",
        "correction_delete_indicator_code", "recipient_uei", "recipient_name", "recipient_country_code",
        "recipient_city_name", "recipient_county_fips_code", "recipient_state_code", "recipient_state_fips_code",
        "recipient_zip_code", "primary_place_of_performance_scope", "primary_place_of_performance_country_code",
        "primary_place_of_performance_county_fips_code", "primary_place_of_performance_state_code",
        "primary_place_of_performance_state_fips_code", "cfda_number", "assistance_type_code"]


def row(tk, ak, mod, amt, date, fy, at, rfips, rst, rsf, scope, pfips, pst, psf, cfda, cdi="", country="USA", uei="U1"):
    return [tk, ak, ak.split("_")[-1], mod, amt, date, fy, at, cdi, uei, f"Org {uei}", country, "Town", rfips, rst, rsf,
            "37130", scope, "USA", pfips, pst, psf, cfda, "04"]


ROWS = [
    # A1: RCDG, new FY2010, TN Rutherford, 2 actions incl. a deobligation in FY2011
    row("t1", "ASST_A1", "0", "200000", "2010-08-15", "2010", "A", "47149", "TN", "47", "Single ZIP Code", "47149", "TN", "47", "10.771", uei="U1"),
    row("t2", "ASST_A1", "1", "-5000", "2011-03-01", "2011", "C", "47149", "TN", "47", "Single ZIP Code", "47149", "TN", "47", "10.771", uei="U1"),
    row("t2", "ASST_A1", "1", "-5000", "2011-03-01", "2011", "C", "47149", "TN", "47", "Single ZIP Code", "47149", "TN", "47", "10.771", uei="U1"),  # duplicate
    # A2: SDGG, statewide performance, recipient in Shannon County SD (legacy code -> 46102)
    row("t3", "ASST_A2", "0", "175000", "2015-09-20", "2015", "A", "46113", "SD", "46", "State-wide", "", "SD", "46", "10.871", uei="U2"),
    # A3: RCDG in Valdez-Cordova (split code) -> not in a county
    row("t4", "ASST_A3", "0", "100000", "2012-09-01", "2012", "A", "02261", "AK", "02", "County-wide", "02261", "AK", "02", "10.771", uei="U3"),
    # A4: other listing, must be dropped
    row("t5", "ASST_A4", "0", "999999", "2012-09-01", "2012", "A", "47149", "TN", "47", "Single ZIP Code", "47149", "TN", "47", "10.352", uei="U4"),
    # A5: deleted record, must be dropped
    row("t6", "ASST_A5", "0", "50000", "2013-09-01", "2013", "A", "47149", "TN", "47", "Single ZIP Code", "47149", "TN", "47", "10.771", cdi="D", uei="U5"),
    # A6: CT planning-region code
    row("t7", "ASST_A6", "0", "120000", "2024-09-01", "2024", "A", "09110", "CT", "09", "County-wide", "09110", "CT", "09", "10.771", uei="U6"),
    # A7: FY2007 action outside the window (continuing award), plus an FY2008 mod
    row("t8", "ASST_A7", "0", "80000", "2007-09-01", "2007", "A", "47037", "TN", "47", "Single ZIP Code", "47037", "TN", "47", "10.771", uei="U7"),
    row("t9", "ASST_A7", "1", "10000", "2008-01-15", "2008", "C", "47037", "TN", "47", "Single ZIP Code", "47037", "TN", "47", "10.771", uei="U7"),
    # A8: SDGG made and cancelled the same day (net $0) -> not a new award (R13)
    row("t10", "ASST_A8", "0500", "175000", "2024-09-25", "2024", "A1", "05119", "AR", "05", "", "05119", "AR", "05", "10.871", uei="U8"),
    row("t11", "ASST_A8", "0501", "-175000", "2024-09-25", "2024", "EX", "05119", "AR", "05", "", "05119", "AR", "05", "10.871", uei="U8"),
    # A9: value-added grant filed under 10.771, moved out by a 10.352 correction the same day (R14)
    row("t12", "ASST_A9", "0200", "10000", "2013-08-06", "2013", "A1", "49043", "UT", "49", "", "49043", "UT", "49", "10.771", uei="U9"),
    row("t13", "ASST_A9", "0227", "-10000", "2013-08-06", "2013", "EX", "49043", "UT", "49", "", "49043", "UT", "49", "10.352", uei="U9"),
]


DESC = {"ASST_A1": "RCDG - COOPERATIVE DEVELOPMENT CENTER", "ASST_A3": "VALUE- ADDED AGRICULTURAL PRODUCT MARKET DEVELOPMENT GRANTS",
        "ASST_A6": "RCDG - APPROPRIATE TECHNOLOGY TO RURAL AREAS",
        "ASST_A7": "VALUE-ADDED AGRICULTURAL MARKETING RESOURCE CENTER GRANT"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw"); out = tmp_path_factory.mktemp("out")
    fx = pd.DataFrame(ROWS, columns=COLS)
    fx["prime_award_base_transaction_description"] = fx["assistance_award_unique_key"].map(DESC).fillna("")
    fx.to_csv(raw / "SYNTHETIC_Assistance_PrimeTransactions_1.csv", index=False)
    env = dict(os.environ, CDAP_RAW=str(raw), CDAP_OUT=str(out))
    subprocess.run([sys.executable, str(ROOT / "code" / "02_build.py")], check=True, env=env, cwd=ROOT / "code")
    return {n: pd.read_csv(out / f"cdap_{n}.csv", dtype={"county_fips": str, "rec_county_fips": str,
                                                         "pop_county_fips": str, "state_fips": str})
            for n in ["awards", "county_fy", "state_fy"]} | {"log": json.loads((out / "build_log.json").read_text())}


def test_filters(built):
    log = built["log"]
    assert log["n_in_programmes"] == 12 and log["n_delete_flag_dropped"] == 1
    assert log["n_other_listing_corrections"] == 1
    assert log["n_duplicate_transactions_dropped"] == 1
    assert set(built["awards"].award_key) == {"ASST_A1", "ASST_A2", "ASST_A3", "ASST_A6", "ASST_A7", "ASST_A8", "ASST_A9"}


def test_panel_shape(built):
    p = built["county_fy"]
    assert len(p) == 3143 * 19 * 2
    assert not p.duplicated(["county_fips", "fy", "programme"]).any()


def test_values(built):
    p = built["county_fy"].set_index(["county_fips", "fy", "programme"])
    assert p.loc[("47149", 2010, "RCDG"), "rec_obligations"] == 200000
    assert p.loc[("47149", 2011, "RCDG"), "rec_obligations"] == -5000
    assert p.loc[("47149", 2010, "RCDG"), "rec_new_awards"] == 1
    assert p.loc[("47149", 2011, "RCDG"), "rec_new_awards"] == 0
    assert p.loc[("46102", 2015, "SDGG"), "rec_obligations"] == 175000      # recoded legacy FIPS
    assert p.loc[("46102", 2015, "SDGG"), "pop_obligations"] == 0           # statewide, not in county
    assert p.loc[("47037", 2008, "RCDG"), "rec_obligations"] == 10000      # FY2007 action excluded
    assert p.loc[("47037", 2008, "RCDG"), "rec_new_awards"] == 0           # continuing award, not new


def test_no_dollars_lost(built):
    s, log = built["state_fy"], built["log"]
    assert round(s.rec_obligations_total.sum(), 2) == log["total_obligations_in_window"] == 600000
    assert round(s.rec_obligations_in_counties.sum(), 2) == log["total_obligations_rec_counties"] == 380000
    assert round(s.pop_obligations_not_in_county.sum(), 2) == 175000 + 100000 + 120000


def test_statuses(built):
    a = built["awards"].set_index("award_key")
    assert a.loc["ASST_A2", "rec_county_status"] == "recoded"
    assert a.loc["ASST_A2", "pop_county_status"] == "multi_county_or_statewide"
    assert a.loc["ASST_A3", "rec_county_status"] == "split_unallocatable"
    assert a.loc["ASST_A6", "rec_county_status"] == "ct_planning_region"
    assert a.loc["ASST_A7", "new_in_window"] == 0


def test_subprogramme(built):
    a = built["awards"].set_index("award_key")
    assert a.loc["ASST_A1", "subprogramme"] == "COOP_CENTRE" and a.loc["ASST_A1", "core_coop_dev"] == 1
    assert a.loc["ASST_A2", "subprogramme"] == "SDGG" and a.loc["ASST_A2", "core_coop_dev"] == 1
    assert a.loc["ASST_A3", "subprogramme"] == "VALUE_ADDED"
    assert a.loc["ASST_A6", "subprogramme"] == "ATTRA"
    assert a.loc["ASST_A7", "subprogramme"] == "AGMRC"            # AgMRC wins over "VALUE-ADDED"
    p = built["county_fy"].set_index(["county_fips", "fy", "programme"])
    assert p.loc[("47149", 2010, "RCDG"), "rec_core_obligations"] == 200000
    assert p.loc[("47037", 2008, "RCDG"), "rec_core_obligations"] == 0   # AgMRC not core
    assert p.loc[("47037", 2008, "RCDG"), "rec_obligations"] == 10000
    assert round(built["state_fy"].rec_core_obligations_total.sum(), 2) == 200000 - 5000 + 175000


def test_fully_deobligated_not_new(built):
    a = built["awards"].set_index("award_key")
    assert a.loc["ASST_A8", "fully_deobligated"] == 1 and a.loc["ASST_A8", "new_in_window"] == 0
    assert a.loc["ASST_A1", "fully_deobligated"] == 0 and a.loc["ASST_A1", "new_in_window"] == 1
    p = built["county_fy"].set_index(["county_fips", "fy", "programme"])
    assert p.loc[("05119", 2024, "SDGG"), "rec_new_awards"] == 0
    assert p.loc[("05119", 2024, "SDGG"), "rec_awards_active"] == 1


def test_other_listing_correction(built):
    a = built["awards"].set_index("award_key")
    assert str(a.loc["ASST_A9", "assistance_listing"]) == "10.771" and a.loc["ASST_A9", "n_other_listing_actions"] == 1
    assert a.loc["ASST_A9", "net_obligation"] == 0 and a.loc["ASST_A9", "new_in_window"] == 0
    assert "ASST_A4" not in a.index                                   # unrelated 10.352 award still dropped
    p = built["county_fy"].set_index(["county_fips", "fy", "programme"])
    assert p.loc[("49043", 2013, "RCDG"), "rec_obligations"] == 0
    assert p.loc[("49043", 2013, "RCDG"), "rec_new_awards"] == 0
