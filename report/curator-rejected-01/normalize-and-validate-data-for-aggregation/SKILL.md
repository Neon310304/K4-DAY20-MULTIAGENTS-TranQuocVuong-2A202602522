---
name: normalize-and-validate-data-for-aggregation
description: Use when preparing raw data for aggregation to ensure consistent formatting, correct missing values, and accurate calculations.
---
1. Load the raw data into a DataFrame or equivalent structure.
2. Normalize categorical fields (e.g., region names) by stripping whitespace and applying consistent capitalization.
3. Replace sentinel values for missing data (e.g., -999) with proper nulls (e.g., NaN).
4. Parse date/time fields using robust parsers that handle mixed formats and timezones.
5. Convert all datetime values to a common timezone (UTC) and make them timezone-naive for uniform comparison.
6. Remove duplicate rows and record the count of duplicates removed.
7. Filter out rows with missing critical values (e.g., missing amounts) before aggregation.
8. Perform aggregations (e.g., sum, count) on cleaned data subsets as required.
9. Convert monetary values to integer cents for consistent representation.
10. Validate that output data matches expected formats and rules (e.g., JSON meta block with source, rows_in, rows_used).
11. Save cleaned data and results to specified output files.
12. Confirm all steps complete without errors and results pass validation checks.
