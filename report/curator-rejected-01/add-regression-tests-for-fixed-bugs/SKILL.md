---
name: add-regression-tests-for-fixed-bugs
description: Use when fixing bugs to create regression tests that verify the bug is resolved and prevent future regressions.
---
1. For each bug fixed, identify the minimal input and expected output that demonstrate the fix.
2. Create a new test function in the designated regression test file.
3. Name the test function clearly to reflect the bug it covers.
4. Write assertions that fail if the bug reappears.
5. Include edge cases related to the bug if applicable.
6. Ensure the test file imports necessary modules and functions.
7. Run the full test suite to confirm all tests pass.
8. Add at least one regression test per bug fixed, with a minimum of three tests if multiple bugs were fixed.
9. Commit the regression test file along with the bug fixes.
