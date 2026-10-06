---
name: structured-log-parsing-and-normalization
description: Use when parsing raw log files to produce normalized, filtered, and sorted structured JSON outputs with correct schema and naming conventions.
---
1. Read the entire log file, preserving message order and multi-line entries.
2. Identify and parse log entries with levels ERROR or CRITICAL (case insensitive).
3. Normalize service names to lower-case and replace hyphens with underscores.
4. Convert all timestamps to UTC timezone and format as ISO 8601 with 'Z' suffix (YYYY-MM-DDTHH:MM:SSZ).
5. Extract the first line message text after the service name and log level.
6. Extract the last line of any traceback or exception text if present; otherwise, set exception field to null.
7. Detect and sum repeat counts from lines of the form `-- last message repeated N times --` following each entry.
8. Count total entries and verify the count matches expected values.
9. Sort the final errors array by service name ascending, then by timestamp_utc ascending.
10. Produce a top-level JSON object with fields:  
    - schema_version: 2  
    - generated_by: "log-triage"  
    - errors: [array of parsed error entries]
11. Validate that all required fields are present and correctly formatted.
12. Confirm no extraneous or missing entries and that repeat counts are accurate.
13. Write the output to workspace/errors.json exactly as specified.
