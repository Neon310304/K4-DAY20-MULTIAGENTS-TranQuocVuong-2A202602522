---
name: maintain-regression-tests-and-changelog-for-fixes
description: Use when fixing bugs to add regression tests and record fixes in the changelog following organisation-wide conventions.
---
1. For each bug fix, write at least one dedicated regression test function that reproduces the bug scenario and verifies the fix.
2. Collect all regression tests in the file tests/test_regressions.py.
3. Ensure tests/test_regressions.py passes successfully with all tests.
4. Open CHANGELOG.md and locate the section headed "## Unreleased".
5. Add a bullet point for each fix in this section using the format: `- fix(<function name>): <short description>`.
6. Include at least three such bullet points if three or more bugs were fixed.
7. Commit the updated tests and changelog together with the fix.
8. Verify that the changelog entries are clear, concise, and follow the exact bullet format.
