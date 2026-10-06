---
name: enforce-type-annotations-on-public-functions
description: Use when reviewing or writing package code to ensure all public functions have complete type hints on parameters and return values.
---
1. Identify all public functions in the package (names not starting with '_').
2. For each public function, check if every parameter has a type annotation.
3. Check if the function has a return type annotation.
4. If any annotation is missing, add the appropriate type hint based on the function’s logic and usage.
5. Use standard typing constructs (e.g., Optional, Union) as needed for clarity.
6. Verify that the added type hints are syntactically correct and consistent with the code.
7. Run static type checkers (e.g., mypy) to confirm no type errors.
8. Commit changes only after all public functions have complete type annotations.
