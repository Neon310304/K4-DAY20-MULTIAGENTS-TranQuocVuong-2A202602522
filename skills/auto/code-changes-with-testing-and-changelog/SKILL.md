---
name: code-changes-with-testing-and-changelog
description: Use when modifying code to fix bugs or add features, ensuring type annotations, regression tests, and changelog updates are included.
---
1. For every public function (not starting with '_') in the modified package, add complete type annotations on all parameters and the return value.
2. Implement regression tests for each bug fix or feature change in a dedicated test file named tests/test_regressions.py.
3. Include at least one test function per bug fix or feature, ensuring the test file passes without errors.
4. Update CHANGELOG.md under the heading "## Unreleased" with a bullet for each fix or feature in the format:  
   `- fix(<function name>): <short description>`
5. Verify that all code changes, tests, and changelog entries are consistent and complete before committing.
6. Run the full test suite to confirm no regressions or failures.
7. Ensure no parallel edits conflict in the same file; apply changes sequentially if needed.
8. Confirm that all code formatting and style conventions are respected.
