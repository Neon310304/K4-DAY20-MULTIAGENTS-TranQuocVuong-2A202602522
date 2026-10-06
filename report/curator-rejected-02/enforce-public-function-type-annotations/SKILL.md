---
name: enforce-public-function-type-annotations
description: Use when reviewing or writing package code to ensure all public functions have complete type hints on parameters and return values.
---
1. Identify all public functions in the package (functions whose names do not start with an underscore).
2. For each public function, check that every parameter has an explicit type annotation.
3. Check that the function has an explicit return type annotation.
4. If any parameter or the return type lacks annotation, add the appropriate type hints based on the function’s logic and expected inputs/outputs.
5. Use standard Python typing conventions and imports as needed.
6. After adding annotations, run static type checking tools (e.g., mypy) to verify correctness.
7. Confirm no public function remains without full type annotations before finalizing code.
