# Medical Supply Project - Analysis of Issues in the Analysis Process

## Executive Summary

This document identifies issues in the medical supply data analysis pipeline, categorized by severity and type. The project analyzes the ICIJ Faulty Medical Devices Global Dataset through a reproducible ETL pipeline producing a static dashboard.

---

## Critical Issues (Data Quality / Analysis Validity)

### 1. Severe Selection Bias in Device Cleaning (Complete-Case Analysis)
**Location:** `src/transform.py:83` - `df = df.dropna()`
**Impact:** Removes 87,693 of 118,249 device rows (74.2% data loss)
**Problem:** The complete-case filter keeps only rows where ALL fields are populated. This heavily biases toward US FDA records with complete data. The dashboard explicitly states "the device-linked subset is United States only, because complete device rows come from the FDA source."
**Evidence:** `etl_report.json` shows 30,556 clean rows from 118,249 raw rows.
**Recommendation:** Consider imputation strategies or separate analyses for different data sources rather than complete-case filtering.

### 2. Arbitrary Events Threshold (15/19 Non-Null Values)
**Location:** `src/config.py:26` - `EVENTS_MIN_NON_NULL = 15`, `src/transform.py:129` - `df = df.dropna(thresh=EVENTS_MIN_NON_NULL)`
**Impact:** Removes 85,449 of 124,969 event rows (68.4% data loss)
**Problem:** The threshold of 15 is not justified statistically. Why 15 and not 14 or 16? No sensitivity analysis shown.
**Evidence:** `etl_report.json` shows "rows_removed_by_threshold": 85449
**Recommendation:** Document the rationale, perform sensitivity analysis, or use a principled approach (e.g., based on missingness patterns).

### 3. Manufacturer Name Non-Uniqueness Not Handled in Aggregations
**Location:** `notebooks/notes/eda_decisions.md:97` - "name is not unique (20,049 distinct names over 31,790 ids)"
**Impact:** Dashboard counts by `manufacturer_id` but displays `manufacturer_name`, causing potential misinterpretation
**Problem:** Multiple manufacturer IDs can have the same name. Top manufacturer "Customed, Inc." (695 recalls) - is this one entity or multiple?
**Recommendation:** Either deduplicate by name before aggregation, or clearly label that counts are by ID not name.

### 4. Distribution Scope Normalization is Rule-Based, Not Authoritative
**Location:** `src/metrics.py:97-120` - `_distribution_index()` with regex patterns
**Problem:** Free-text `distributed_to` field has >11,000 distinct values. Normalized into 4 buckets using simple regex (nationwide, worldwide, both, other). The README admits "the four buckets are directional rather than authoritative."
**Recommendation:** Add confidence scores, or use a geographic gazetteer for more accurate classification.

### 5. Missing Dates Excluded from Temporal Analysis
**Location:** `src/metrics.py:200-209` - `date_min`/`date_max` only from parsed dates
**Impact:** 973 recalls (2.5% of cleaned events) have no parsable `date_initiated_by_firm`
**Problem:** These recalls appear in totals but not in year trend charts, creating silent data loss in temporal analysis.
**Recommendation:** Show "Unknown year" bucket in charts, or impute based on other date fields.

---

## High Issues (Methodology / Reproducibility)

### 6. No Automated Test Suite
**Location:** Entire project - no `tests/` directory, no pytest configuration
**Problem:** No unit tests for transform, merge, metrics, or validation logic. Changes cannot be verified automatically.
**Recommendation:** Add pytest tests for each module, especially:
- Transform functions with known inputs/outputs
- Merge logic (left/inner join behavior)
- Metrics aggregation correctness
- Validation checks

### 7. Hardcoded Thresholds Not Configurable via CLI
**Location:** `src/config.py` - `NULL_DROP_THRESHOLD=0.40`, `EVENTS_MIN_NON_NULL=15`, `CATEGORY_CARDINALITY=0.05`, `TOP_DIM_VALUES=15`
**Problem:** Thresholds are in config.py but not exposed as CLI arguments. Changing them requires code edits.
**Recommendation:** Add CLI arguments to `pipeline.py` for key thresholds to enable sensitivity analysis.

### 8. Validation Checks Not Re-Run in `--skip-etl` Mode
**Location:** `src/pipeline.py:41-59` - Loads validation from etl_report.json instead of re-running
**Problem:** If enriched CSV is modified externally, validation becomes stale. The dashboard shows old validation results.
**Recommendation:** Re-run validation on loaded data, or add a `--revalidate` flag.

### 9. Date Parsing Uses Deprecated `format="mixed"`
**Location:** `src/transform.py:136-138`, `src/merge.py:72-74`, `src/merge.py:110-112`
**Problem:** `pd.to_datetime(..., format="mixed")` is deprecated in pandas 2.0+. Should use `format="ISO8601"` or infer.
**Recommendation:** Update to modern pandas API.

### 10. No Logging Framework - Uses Print Statements
**Location:** `src/pipeline.py` - Multiple `print()` calls
**Problem:** No log levels, no file output, no structured logging. Difficult to debug in production.
**Recommendation:** Use Python `logging` module with configurable levels.

---

## Medium Issues (Code Quality / Maintainability)

### 11. Template and Generated Dashboard JS Are Identical
**Location:** `src/templates/app.js` vs `dashboard/app.js`
**Problem:** The template contains the placeholder `/*__DATA__*/` but the generated file has the same code. The comment says "edit the template in src/templates/app.js instead of this generated file" but both are identical. This is confusing.
**Recommendation:** Either make the template clearly distinct (minimal scaffold) or remove the template and document that `dashboard/app.js` is the source.

### 12. Spanish Comments Mixed with English in Notebooks
**Location:** `notebooks/notes/eda_decisions.md` - Lines 16-17, 34-37, 46-50
**Problem:** Inconsistent documentation language reduces maintainability for English-speaking collaborators.
**Example:** "Puedo hacer un drop de los valores nulls por rows...", "Para este análisis haré el drop..."
**Recommendation:** Standardize on English for all documentation.

### 13. No Version Pinning for Chart.js CDN
**Location:** `dashboard/index.html:343` - `chart.js@4.4.7`
**Problem:** Pinned version is good, but no Subresource Integrity (SRI) hash. If CDN is compromised, dashboard loads malicious code.
**Recommendation:** Add SRI hash: `integrity="sha384-..."`

### 14. Pipeline Doesn't Handle Missing Raw Data Gracefully
**Location:** `src/extract.py:20-25` - Raises `FileNotFoundError` with no guidance
**Problem:** If raw CSVs are missing, user gets a raw exception with no instructions on where to get data.
**Recommendation:** Add helpful error message with download instructions.

### 15. ETL Report Overwritten Without Versioning
**Location:** `src/pipeline.py:115-117` - Writes to same `etl_report.json` path
**Problem:** No history of pipeline runs. Cannot compare runs or rollback.
**Recommendation:** Add timestamped copies or use a run ID.

### 16. Device Name Cleaning Only Removes "Device Recall" Prefix
**Location:** `src/metrics.py:90-94` - `_clean_device_names()`
**Problem:** Only strips "Device Recall" prefix. Other noise (trailing spaces, case variations) handled by generic strip, but no handling of manufacturer prefixes, model numbers, etc.
**Recommendation:** More comprehensive device name normalization.

---

## Low Issues (Documentation / UX)

### 17. Dashboard Year Range Hint Element Doesn't Exist
**Location:** `src/templates/app.js:169` - `document.getElementById("yearRangeHint")`
**Problem:** No element with id `yearRangeHint` in `dashboard/index.html`. Code silently fails.
**Recommendation:** Either add the element to HTML or remove the code.

### 18. No CI/CD Configuration
**Location:** Project root - no GitHub Actions, GitLab CI, etc.
**Problem:** No automated testing, linting, or deployment.
**Recommendation:** Add basic CI pipeline.

### 19. Requirements.txt Lacks Version Upper Bounds
**Location:** `requirements.txt` - Only lower bounds (`>=`)
**Problem:** Future package updates could break the pipeline without warning.
**Recommendation:** Pin to compatible versions or use `pip-tools`/`poetry` for lock files.

### 20. AGENTS.md References Non-Existent Commands
**Location:** `AGENTS.md` - References to commands not in `.kilo/command/`
**Problem:** The AGENTS.md file appears to be a template or from another project.
**Recommendation:** Update or remove if not used.

---

## Data Lineage Issues

### 21. Raw Data Source Not Documented with Checksums
**Location:** `data/raw/` - Files named with timestamps (e.g., `devices-1681209661.csv`)
**Problem:** No SHA256 checksums recorded. Cannot verify data integrity or reproduce exact results if files change.
**Recommendation:** Record checksums in `etl_report.json` or separate manifest.

### 22. Kaggle Dataset Version Not Pinned
**Location:** README.md - References Kaggle dataset URL
**Problem:** Kaggle datasets can be updated. No version/timestamp recorded for reproducibility.
**Recommendation:** Document exact dataset version/download date.

---

## Dashboard Usability Issues

### 23. Manufacturer Scorecard Shows ID-Based Counts with Names
**Location:** `src/templates/app.js:585-616` - `renderManufacturerTable()`
**Problem:** Table shows manufacturer names but counts are by `manufacturer_id`. If multiple IDs share a name, they appear as separate rows with split counts.
**Recommendation:** Aggregate by name for display, or show ID alongside name.

### 24. "Other (grouped)" Category Not Explained in UI
**Location:** Dashboard charts - Top 15 + grouped tail
**Problem:** Users see "Other (grouped)" but don't know what's included or how many items.
**Recommendation:** Add tooltip or legend explaining the grouping threshold.

### 25. No Export/Download Functionality in Dashboard
**Problem:** Users cannot export filtered data or charts.
**Recommendation:** Add CSV export button for current filter state.

---

## Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Data Quality | 5 | 0 | 0 | 0 | 5 |
| Methodology | 0 | 4 | 0 | 0 | 4 |
| Code Quality | 0 | 1 | 4 | 0 | 5 |
| Documentation | 0 | 0 | 1 | 2 | 3 |
| Data Lineage | 0 | 0 | 0 | 2 | 2 |
| Dashboard UX | 0 | 0 | 0 | 3 | 3 |
| **Total** | **5** | **5** | **5** | **7** | **22** |

---

## Recommended Priority Order

1. **Add test suite** (Issue #6) - Foundation for safe refactoring
2. **Document/justify cleaning thresholds** (Issues #1, #2) - Core analysis validity
3. **Fix deprecated date parsing** (Issue #9) - Technical debt
4. **Add logging** (Issue #10) - Operational visibility
5. **Make thresholds configurable** (Issue #7) - Enable sensitivity analysis
6. **Fix manufacturer name aggregation** (Issue #3) - Correctness of key metrics
7. **Add data checksums** (Issue #21) - Reproducibility
8. **Fix validation in skip-etl mode** (Issue #8) - Correctness
9. **Standardize documentation language** (Issue #12) - Maintainability
10. **Add SRI to Chart.js** (Issue #13) - Security

---

## Next Steps

Would you like me to:
1. Create a detailed implementation plan for the top N issues?
2. Focus on a specific category (data quality, testing, dashboard)?
3. Implement fixes for any specific issue?

Please indicate your priority and I'll create an actionable plan.