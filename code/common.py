"""Shared constants and helpers for the Cooperative Development Award Panel pipeline."""
import os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("CDAP_RAW", ROOT / "data" / "raw" / "usaspending"))  # override for tests
REF = ROOT / "data" / "reference"
OUT = Path(os.environ.get("CDAP_OUT", ROOT / "data" / "processed"))
FIG = Path(os.environ.get("CDAP_FIG", ROOT / "figures"))

VERSION = "1.0.0"
FY_START, FY_END = 2008, 2026          # v1.0 window; v2.0 adds FY2027, v3.0 adds FY2028

PROGRAMMES = {
    "10.771": ("RCDG", "Rural Cooperative Development Grant"),
    "10.871": ("SDGG", "Socially Disadvantaged Groups Grant (formerly Small Socially-Disadvantaged Producer Grant)"),
}

# County codes that existed during FY2008-FY2026 but are not in the Census 2020 county vintage.
# One-to-one renames/absorptions are recoded; splits cannot be allocated to one 2020 county.
RECODE_TO_2020 = {
    "46113": "46102",  # Shannon County SD -> Oglala Lakota County (2015)
    "02270": "02158",  # Wade Hampton CA AK -> Kusilvak CA (2015)
    "51515": "51019",  # Bedford city VA absorbed into Bedford County (2013)
    "12025": "12086",  # Dade -> Miami-Dade (1997; legacy code still seen)
}
UNALLOCATABLE = {
    "02261": "Valdez-Cordova CA split into 02063/02066 (2019)",
    "02232": "Skagway-Hoonah-Angoon CA split (2007)",
    "02280": "Wrangell-Petersburg CA split (2008)",
    "02201": "Prince of Wales-Outer Ketchikan CA split (2008)",
}
CT_PLANNING_REGIONS = {f"09{c}" for c in ("110", "120", "130", "140", "150", "160", "170", "180", "190")}

# place-of-performance scopes that do not identify a single county
MULTI_SCOPES = {"STATE-WIDE", "STATEWIDE", "MULTI-STATE", "MULTI-COUNTY", "FOREIGN"}


def county_frame() -> pd.DataFrame:
    """Census 2020 county vintage, 50 states + DC (3,143 counties)."""
    c = pd.read_csv(REF / "counties_2020.csv", dtype=str)
    c["county_fips"] = c["statefp"] + c["countyfp"]
    c = c.drop_duplicates("county_fips", keep="last")   # file lists old and new names for renamed codes
    c = c[c["statefp"].astype(int) <= 56]
    c = c[~c["county_fips"].isin(["02261", "51515"])]  # not in 2020 vintage
    extra = pd.DataFrame([{"statefp": "02", "countyfp": "063", "name": "Chugach Census Area", "county_fips": "02063"}])
    c = pd.concat([c, extra], ignore_index=True)
    st = states().rename(columns={"fips": "statefp", "postal": "state", "name": "state_name"})
    c = c.merge(st, on="statefp", how="left").rename(columns={"name": "county_name", "statefp": "state_fips"})
    return c[["county_fips", "state_fips", "state", "state_name", "county_name"]].sort_values("county_fips").reset_index(drop=True)


def states() -> pd.DataFrame:
    """One row per state FIPS (the source file lists alternate names, e.g. 'D.C.')."""
    return pd.read_csv(REF / "states.csv", dtype=str).drop_duplicates("fips", keep="first")


def fiscal_year(dates: pd.Series) -> pd.Series:
    d = pd.to_datetime(dates, errors="coerce")
    return (d.dt.year + (d.dt.month >= 10)).astype("Int64")


# Sub-programme tags from the award description (10.771 carries more than co-op centre grants on USAspending).
# Order matters: first match wins. Core co-op development = COOP_CENTRE + SDGG.
SUBPROGRAMME_RULES = [
    ("ATTRA", ("ATTRA", "APPROPRIATE TECHNOLOGY")),
    ("AGMRC", ("MARKETING RESOURCE CENTER", "AGMRC", "AGRI MARKETING RESOURCE")),
    ("VALUE_ADDED", ("VALUE-ADDED", "VALUE- ADDED", "VALUE ADDED", "PMDG", "PRODUCT MARKET DEVELOPMENT")),
    ("REAP", ("RURAL ENERGY FOR AMERICA", "SEC. 9007")),
    ("MINORITY_PRODUCER", ("ASSIST MINORITY PROD", "ASST MINORITY PROD")),
    ("COOP_RESEARCH", ("COOPERATIVE RESEARCH",)),
]
# MINORITY_PRODUCER = the "grants to assist minority producers" line (the SDGG's predecessor) where it was filed under 10.771
CORE_SUBPROGRAMMES = {"COOP_CENTRE", "MINORITY_PRODUCER", "SDGG"}


def subprogramme(listing: str, description) -> str:
    if listing == "10.871":
        return "SDGG"
    d = "" if pd.isna(description) else str(description).upper()
    for tag, keys in SUBPROGRAMME_RULES:
        if any(k in d for k in keys):
            return tag
    return "COOP_CENTRE"
