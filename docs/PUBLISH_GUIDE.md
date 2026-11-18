# Publish guide: Cooperative Development Award Panel v1.0.0

The DOI is already reserved: **10.5281/zenodo.24287714**. It is in the README and CITATION.cff, and becomes live when you click Publish on Zenodo. The whole process takes about 30–40 minutes. Do it in this order.

## A. GitHub (GitHub Desktop), about 10 minutes

1. On github.com, signed in as **Tlayem**, click **+ → New repository**:
   - Name: `cooperative-development-award-panel`
   - **Public**
   - Do **not** add a README, .gitignore or licence; the folder already has them.

   Click **Create repository**.
2. In GitHub Desktop, choose **File → Add local repository** and pick the folder `github_repo\cooperative-development-award-panel` from the release package.
   - Keep it out of OneDrive.
   - Make sure the path has no leading space.
   - If it says "not a Git repository", click **create a repository** and keep the same name.
3. Commit everything. Summary: `v1.0.0`. Then click **Publish repository**, untick "Keep this code private", and click **Publish**.
   - The raw USAspending CSVs and zips are ignored on purpose (`.gitignore`). They go to Zenodo instead.
4. On github.com, open the repository and go to **Releases → Draft a new release**:
   - Tag: `v1.0.0`
   - Title: `The Cooperative Development Award Panel v1.0.0 (FY2008–FY2026)`
   - Body: the README "Summary" block and the DOI link.

   Click **Publish release**.
5. In Zenodo **Settings → GitHub**, if this repository appears in the list, **leave its switch OFF**. Otherwise a second DOI would be created.

## B. Zenodo: finish the draft you saved, about 20 minutes

Go to **zenodo.org → My dashboard → Uploads** and open the draft "The Cooperative Development Award Panel" (DOI 10.5281/zenodo.24287714).

1. **Files.** Upload these five files from the `zenodo_upload` folder of the release package:
   - `cooperative-development-award-panel-v1.0.0.zip`: the full repository, including processed data, docs and code
   - `cdap_county_fy.csv`
   - `cdap_awards.csv`
   - `cdap_state_fy.csv`
   - `usaspending_inputs_v1.0.0.zip`: your two USAspending downloads, exactly as downloaded (U.S. Government works)
2. **Metadata.** Paste each field from `zenodo_upload\ZENODO_METADATA.md`, using Ctrl+Shift+V to paste without formatting.
3. Click **Preview** and check that the title, author, ORCID, licence and DOI are right.
4. Click **Publish**. Then open the record page and check that it shows the DOI and "Published" with today's date.

## C. After publishing, about 5 minutes

1. Save PDFs (Ctrl+P → Save as PDF) of:
   - the Zenodo record page
   - the GitHub release page
2. Add a row to your `evidence_log.csv`. A filled-in row is in `zenodo_upload\evidence_log_row.csv`.
3. Future CV line:

   Adesiyan, T. F. (2026). *The Cooperative Development Award Panel: county-year by CFDA programme* (Version 1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.24287714
4. Tell Claude once it's live, so the project notes record the date and the concept DOI.
