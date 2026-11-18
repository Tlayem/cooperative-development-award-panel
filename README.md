# The Cooperative Development Award Panel

<!-- STATUS -->
**Status: released, v1.0.0, FY2008–FY2026.**
<!-- /STATUS -->

[![Zenodo DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24287714.svg)](https://doi.org/10.5281/zenodo.24287714)

The Cooperative Development Award Panel is a county-by-fiscal-year panel of USDA cooperative development awards. It covers the two federal assistance programmes that fund cooperative development directly:

| Programme | Assistance Listing (CFDA) | Panel code |
|---|---|---|
| Rural Cooperative Development Grant | 10.771 | `RCDG` |
| Socially Disadvantaged Groups Grant (Small Socially-Disadvantaged Producer Grant before 2022) | 10.871 | `SDGG` |

Every U.S. county (Census 2020 vintage, 50 states and DC) appears in every fiscal year for both programmes. A county with no award in a year has zeros. Each award is placed in a county in two ways:

- by where the **recipient** is located;
- by where the work is **performed**.

On USAspending, listing 10.771 also carries value-added producer grants, the Agricultural Marketing Resource Center, ATTRA and some Rural Energy for America awards. Every record is kept. Each award is tagged with a **sub-programme**, and the panel carries a parallel set of `core_` measures for **core co-op development**: co-op development centres and minority-producer grants under 10.771, plus all of 10.871.

Statewide or multi-county work is never forced into one county. It is flagged, and its dollars go to a state-level companion table so that county and state figures add back to the national total.

The panel is planned in three versions under one Zenodo concept DOI:

- **v1.0**: FY2008–FY2026
- **v2.0**: adds FY2027
- **v3.0**: adds FY2028

## Summary

<!-- STATS -->
- **1,843 awards** (1,670 RCDG, 173 SDGG) made through 2,353 obligation actions in FY2008–FY2026. 1,585 of the awards are new within the window.
- **$286.1 million** in net obligations (nominal): $260.6 million RCDG and $25.5 million SDGG.
- Core co-op development (co-op centres, minority-producer grants and SDGG): 987 awards, $160.4 million. Sub-programme counts: VALUE_ADDED 810, COOP_CENTRE 675, SDGG 173, MINORITY_PRODUCER 139, AGMRC 19, REAP 16, ATTRA 8, COOP_RESEARCH 3.
- 891 distinct recipients in 54 states and territories. 664 of 3,143 counties held an award at some point.
- 98.9% of dollars are placed in a county by recipient location, and 91.9% by place of performance. The remainder is territories, one foreign recipient, and records with no usable county.
- The panel has 119,434 rows.
<!-- /STATS -->

## Files

| File | Unit | Description |
|---|---|---|
| `data/processed/cdap_county_fy.csv` | county × FY × programme | The panel. It is balanced and zero-filled. |
| `data/processed/cdap_awards.csv` | award | One row per award, with recipient, both county assignments, status flags, dates, net obligation and the USAspending link. Street addresses are not included. |
| `data/processed/cdap_state_fy.csv` | state × FY × programme | State totals, split into dollars placed in counties and dollars not placed in counties. |
| `data/processed/qa_report.txt` | — | Row counts, match rates, checks and spot checks. |
| `data/processed/stats.json` | — | Every number quoted in this README and on Zenodo. |
| `figures/` | — | Obligations by FY, counties reached, and top states. |
| `docs/CODEBOOK.md` | — | Definition of every column. |
| `docs/LIMITATIONS.md` | — | What the panel cannot tell you. |

## How to rebuild

Requirements: Python 3.10 or later, `pandas`, `matplotlib`, and `pytest` (for the tests only).

1. **Get the raw files.** USAspending.gov → Search → Advanced Search, then set:
   - Time Period: fiscal years 2008–2026
   - Award Type: all Financial Assistance
   - Assistance Listing: 10.771 and 10.871

   Click **Download**, tick both **Awards** and **Transactions**, choose CSV, and save the zip. Then repeat the search with **Assistance Listing 10.352 only** and download **Transactions** (CSV). This supplies the correction actions.
2. Run `bash run_all.sh first.zip second.zip` (macOS/Linux), or on Windows put both zips in the project folder and double-click `run_all.bat`.
3. Run `python -m pytest -q tests/`. The tests use a synthetic fixture.

The script `01_ingest.py` logs the size and SHA-256 of every input in `data/raw/usaspending/PROVENANCE.txt`. A fresh download will differ slightly from the release inputs, because agencies correct records after the fact. The exact inputs used for each release are deposited on Zenodo.

## Method in brief

- Transactions are kept when the Assistance Listing is 10.771 or 10.871. Records flagged for deletion and exact duplicates are dropped.
- Some awards also have actions under 10.352 (Value-Added Producer Grants), usually a correction moving money out of 10.771. These actions are kept, credited to the award's own programme, and flagged. Other 10.352 awards are not part of the panel.
- Fiscal year is USAspending's `action_date_fiscal_year`.
- Obligations are net. They are the sum of `federal_action_obligation`, so deobligations are negative. Amounts are in nominal dollars.
- An award's location comes from its earliest action, and all of its dollars follow that location.
- County codes are USAspending's, except verified errors listed with evidence in `data/reference/county_overrides.csv` and flagged `county_override`. For example, Duffield, VA is coded Lee County but is in Scott County.
- A **new award** is an award whose earliest action is a new-award action within the window. Awards that began before FY2008, and awards that were fully cancelled (net $0), count as active but not as new.
- County codes are harmonised to the 2020 vintage:
  - Shannon SD → Oglala Lakota
  - Wade Hampton AK → Kusilvak
  - Bedford city VA → Bedford County
- Some county codes cannot be placed in a single 2020 county:
  - codes for counties that were later split (Valdez-Cordova and earlier Alaska splits)
  - Connecticut's 2022 planning-region codes

  These stay out of the county panel and are reported in the state table.

## Sources

- USAspending.gov, prime award transactions and award summaries (DATA Act / FABS), U.S. Department of the Treasury. These are U.S. Government works. Access dates are in `PROVENANCE.txt`.
- County and state FIPS codes: U.S. Census Bureau, as packaged in `addfips` 0.4.2 (MIT). See `data/reference/PROVENANCE.txt`.

## Licence

- Data and figures: CC BY 4.0.
- Code: MIT. See `LICENSE`.

## Citation

Adesiyan, T. F. (2026). *The Cooperative Development Award Panel: county-year by CFDA programme* (Version 1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.24287714

## Maintainer

Taiwo Fausiyat Adesiyan, Middle Tennessee State University, Murfreesboro, Tennessee, USA. ORCID [0000-0002-2023-3624](https://orcid.org/0000-0002-2023-3624). GitHub [@Tlayem](https://github.com/Tlayem).
