# Codebook: Cooperative Development Award Panel v1.0.0

All dollar amounts are **net federal obligations in nominal U.S. dollars**. Each one is the sum of USAspending `federal_action_obligation` across obligation actions, so deobligations are negative. Fiscal years are federal fiscal years: FY2008 runs from 1 October 2007 to 30 September 2008.

Prefixes:

- `rec_` means the award is placed in the county where the **recipient** is located.
- `pop_` means the award is placed in the **place-of-performance** county.

## `cdap_county_fy.csv` (county × FY × programme; balanced, zero-filled)

| Column | Definition |
|---|---|
| `county_fips` | 5-digit county FIPS, Census 2020 vintage (3,143 counties, 50 states + DC) |
| `state_fips`, `state`, `county_name` | State FIPS, USPS abbreviation, county name (Census) |
| `fy` | Federal fiscal year, 2008–2026 |
| `programme` | `RCDG` (Rural Cooperative Development Grant) or `SDGG` (Socially Disadvantaged Groups Grant) |
| `assistance_listing` | `10.771` or `10.871` |
| `rec_new_awards` / `pop_new_awards` | Awards whose earliest action is a new-award action (type A…) in this FY. Aggregate records and fully deobligated awards (net $0) are excluded. |
| `rec_actions` / `pop_actions` | Obligation actions (transactions) in this FY |
| `rec_awards_active` / `pop_awards_active` | Distinct awards with at least one action in this FY |
| `rec_recipients` / `pop_recipients` | Distinct recipients (UEI, falling back to DUNS and then name) with an action in this FY. Aggregate records are excluded. |
| `rec_obligations` / `pop_obligations` | Net obligations in this FY ($) |
| `rec_any_award` / `pop_any_award` | 1 if `*_awards_active` > 0 |
| `rec_core_new_awards`, `rec_core_awards_active`, `rec_core_obligations` (and `pop_` versions) | The same measures restricted to **core co-op development** awards: sub-programme `COOP_CENTRE`, `MINORITY_PRODUCER` or `SDGG` |

## `cdap_awards.csv` (one row per award)

| Column | Definition |
|---|---|
| `award_key` | USAspending `assistance_award_unique_key` (falls back to FAIN) |
| `fain` | Federal Award Identification Number |
| `assistance_listing`, `programme` | Listing and programme code of the award's earliest action |
| `recipient_name`, `recipient_uei`, `recipient_duns` | Recipient as reported. DUNS applies to older records and UEI to records from FY2022 on. |
| `recipient_city`, `recipient_state`, `recipient_zip5` | Recipient location. Street address lines are deliberately excluded. |
| `rec_county_fips` | Recipient county, harmonised to the 2020 vintage. Blank when it cannot be placed. |
| `rec_county_status` | One of the status values below |
| `county_override` | 1 if a county code was corrected from `data/reference/county_overrides.csv` (R11). Each row there names the evidence. |
| `recipient_territory_flag` | 1 if the recipient state FIPS is above 56 (territories) |
| `pop_scope` | USAspending place-of-performance scope (e.g. SINGLE ZIP CODE, COUNTY-WIDE, STATE-WIDE) |
| `pop_state`, `pop_county_fips`, `pop_county_status` | Place-of-performance state, county and status |
| `pop_multi_flag` | 1 if the scope is statewide, multi-county, multi-state or foreign |
| `fully_deobligated` | 1 if the award's actions net to exactly $0 (made and then fully cancelled). Not counted as a new award. |
| `award_description` | USAspending base-transaction description |
| `subprogramme` | Tag assigned from the description by keyword rules in `code/common.py`, first match wins (see the table below) |
| `core_coop_dev` | 1 if `subprogramme` is `COOP_CENTRE`, `MINORITY_PRODUCER` or `SDGG` |
| `aggregate_record` | 1 for USAspending aggregate records (`ASST_AGG…`, recipient "MULTIPLE RECIPIENTS"). Each is one county-level row covering many individual recipients. Its dollars count in obligations, but it is not counted as a new award or a recipient. |
| `first_action_date`, `last_action_date`, `first_action_fy` | Range of action dates in the download |
| `new_in_window` | 1 if the earliest action is a new-award action dated FY2008–FY2026 |
| `n_actions` | Obligation actions on the award |
| `net_obligation` | Sum of all actions on the award ($), including any outside the window |
| `n_listings_on_award` | Distinct listings across the award's actions. Normally 1. |
| `n_other_listing_actions`, `other_listing_amount` | Number and net $ of actions on this award filed under another listing (in practice 10.352). These are kept as corrections to the award and credited to its own programme (R14). |
| `assistance_type`, `business_types` | USAspending codes and descriptions |
| `usaspending_permalink` | Link to the award page |

**Status values:**

| Value | Meaning |
|---|---|
| `matched` | In the 2020 county frame |
| `verified_override` | USAspending's code was replaced by a verified one listed in `data/reference/county_overrides.csv` |
| `recoded` | A legacy code mapped one-to-one to a 2020 county (see `code/common.py`) |
| `split_unallocatable` | The county was later split, so the code cannot be placed in one 2020 county |
| `ct_planning_region` | One of Connecticut's 2022 planning-region codes. These do not nest in the 2020 counties. |
| `territory` | A U.S. territory |
| `multi_county_or_statewide` | Performance scope is not a single county (`pop_` only) |
| `non_us` | The recipient is outside the U.S. |
| `invalid` / `missing` | No usable code |

**Sub-programme tags.** On USAspending, Assistance Listing 10.771 also carries awards that are not co-op development centre grants. The tag separates them:

| Tag | Rule (description contains) | What it is |
|---|---|---|
| `ATTRA` | ATTRA, APPROPRIATE TECHNOLOGY | Appropriate Technology Transfer for Rural Areas (NCAT) |
| `AGMRC` | MARKETING RESOURCE CENTER, AGMRC | Agricultural Marketing Resource Center (Iowa State) |
| `VALUE_ADDED` | VALUE-ADDED, VALUE ADDED, PMDG | Value-Added Producer / Product Market Development grants coded to 10.771 |
| `REAP` | RURAL ENERGY FOR AMERICA, SEC. 9007 | Rural Energy for America awards filed under 10.771 |
| `MINORITY_PRODUCER` | ASSIST MINORITY PROD | "Grants to assist minority producers" (the SDGG's predecessor line) filed under 10.771. **Core.** |
| `COOP_RESEARCH` | COOPERATIVE RESEARCH | Cooperative research agreements |
| `COOP_CENTRE` | anything else under 10.771 | Rural Cooperative Development Grant centres |
| `SDGG` | all of 10.871 | Socially Disadvantaged Groups Grant |

## `cdap_state_fy.csv` (state × FY × programme)

| Column | Definition |
|---|---|
| `state_fips`, `state`, `state_name` | Recipient state (`rec_` columns) or performance state (`pop_` columns). `unknown` if blank. |
| `*_obligations_total` | All net obligations for the state, FY and programme |
| `*_obligations_in_counties` | The part placed in a county in the panel |
| `*_obligations_not_in_county` | The remainder, mostly statewide work and codes that cannot be placed |
| `*_awards_active`, `*_awards_not_in_county` | Distinct awards, total and not placed in a county |
| `*_core_obligations_total` | Total net obligations for core co-op development awards |

Identity: the sum of the panel's `*_obligations` plus the sum of `*_obligations_not_in_county` equals the national total. `qa_report.txt` checks this.
