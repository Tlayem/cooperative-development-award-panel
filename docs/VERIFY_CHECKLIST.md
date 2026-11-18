# Verification checklist: Taiwo completes this before release

Initial and date each line. The publish gate (run by Claude before release) checks the mechanical items. The items below are yours.

## Reproduce

- [x] (15–16 Nov 2026) Rebuild from your own download: on Windows double-click `run_all.bat` (see START_HERE_WINDOWS.txt); on macOS/Linux `bash run_all.sh <zip>`. Your `data/processed/qa_report.txt` matches `docs/qa_report_REFERENCE.txt`.
- [x] (15 Nov 2026) Every number in the README summary matches `stats.json`. It is generated, but read it once anyway.
- [x] (15 Nov 2026) `python -m pytest -q tests/` passes.

## Source-level checks

- [x] (15–16 Nov 2026) Spot checks: 11 awards from qa_report §4 (the random draws overlapped). #1, 2, 4, 5, 6, 7, 9 and 11 match. #3: amount and FY match, but the county was wrong in USAspending (led to R11). #6 led to R13. #8 is an aggregate record with no award page (R9). #10 led to R14.
- [x] (13–16 Nov 2026) National total checked against USAspending: the 10.771 + 10.871 actions sum to $291,435,578.88, matching the Advanced Search total for the same filters ($277.64m Rural Business-Cooperative Service + $13.80m NIFA = $291.44m). After the R14 corrections the panel total is $286,069,884.61.
- [x] (16 Nov 2026) Checked against USDA RD's FY2024 RCDG awardee list (rd.usda.gov, fy2024-awardees-rcdg.pdf). University of Northern Iowa (IA, FY2024, $198,164.68), Clemson University (SC, FY2024, $199,890.72) and Indiana Cooperative Development Center (IN, FY2024, $200,000) all appear in the panel. Northcountry Cooperative Foundation appears under its current name, CoNorth (MN, FY2024).
- [x] (16 Nov 2026) USAspending data are U.S. Government works (17 U.S.C. §105). data.gov lists the USAspending award data with access level "public" and no licence restriction.

## Judgment calls to own (agree, or edit and note)

- [x] **R1** All of an award's dollars follow the location of its earliest action, even when later modifications report a different place. (agreed by Taiwo, 16 Nov 2026)
- [x] **R2** A "new award" means the earliest action in the download is a new-award action (action type A or modification 0) within FY2008–FY2026. (agreed by Taiwo, 16 Nov 2026)
- [x] **R3** County frame is Census 2020. Shannon → Oglala Lakota, Wade Hampton → Kusilvak, and Bedford city → Bedford County are recoded. Split Alaska areas and Connecticut planning regions go to the state table. (agreed by Taiwo, 16 Nov 2026)
- [x] **R4** Statewide, multi-county, multi-state and foreign performance scopes get no place-of-performance county. Their dollars go to the state table. (agreed by Taiwo, 16 Nov 2026)
- [x] **R5** Obligations are net and nominal, with no deflation. (agreed by Taiwo, 16 Nov 2026)
- [x] **R6** Recipient identity uses UEI, falling back to DUNS and then the name in upper case. (agreed by Taiwo, 16 Nov 2026)
- [x] **R7** Programme scope is 10.771 and 10.871 only. Every 10.771 record is kept as reported, including value-added, AgMRC and ATTRA awards. (agreed by Taiwo, 16 Nov 2026)
- [x] **R8** Sub-programme tags come from the award description by keyword (see CODEBOOK). Core co-op development means `COOP_CENTRE` + `MINORITY_PRODUCER` + `SDGG`. Review the "Most common descriptions tagged COOP_CENTRE" list in `qa_report.txt` and check that nothing is mis-tagged. (agreed by Taiwo, 16 Nov 2026)
- [x] **R9** Aggregate records (`ASST_AGG`) keep their dollars but do not count as awards or recipients. (agreed by Taiwo, 16 Nov 2026)
- [x] **R10** Award-summary totals are used only as a cross-check. After R14, any remaining differences come from awards that began before FY2008, whose base obligation falls outside the window. (agreed by Taiwo, 16 Nov 2026)
- [x] **R12** SDGG (10.871) shows $0 in FY2008–FY2013 and FY2025–FY2026 in the USAspending download. The data are kept as reported, and no document gives a cause for the gap. The FY2008–13 "grants to assist minority producers" awards filed under 10.771 are tagged MINORITY_PRODUCER and counted as core. (agreed by Taiwo, 16 Nov 2026)
- [x] **R14** Actions under another listing (10.352) on an award that has 10.771/10.871 actions are kept as corrections, credited to the award's own programme and flagged. Unrelated 10.352 awards are not included. Decided by Taiwo on 15 Nov 2026 after spot checks #4 (Sigrah) and #10 (Three Sisters).
- [x] **R13** Awards whose actions net to exactly $0 (made then fully cancelled) are flagged `fully_deobligated` and not counted as new awards. Decided by Taiwo on 15 Nov 2026 after spot check #6 (Winrock).
- [x] **R11** USAspending county codes are kept as reported, except where the author has verified an error. Verified corrections are listed, with evidence, in `data/reference/county_overrides.csv` and flagged `county_override` (status `verified_override`). The first case is Appalachian Sustainable Development, Duffield VA: USAspending codes it as Lee, but the Census Geocoder places it in Scott (51169). Recipient county only. Decided by Taiwo on 16 Nov 2026 after spot check #3.
- [x] Every QA FAIL line in `qa_report.txt` is resolved or explained. The final build has 0 failures (16 Nov 2026).

## Before it goes public

- [x] (16 Nov 2026) README and LIMITATIONS read and approved by Taiwo.
- [x] (16 Nov 2026) Final build made with `--final`. The publish gate passes except for one accepted exception: the words "draft bylaws" inside a real USAspending award description (cdap_awards.csv and the raw CSVs). That is source text, not a draft marker.
- [x] (16 Nov 2026) Author block correct: Taiwo Fausiyat Adesiyan, ORCID 0000-0002-2023-3624, Middle Tennessee State University. DOI reserved: 10.5281/zenodo.24287714.
- [ ] Evidence log row written on the day of release.
