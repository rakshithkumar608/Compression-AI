---
name: testing-and-quality
description: Guidelines for test coverage, contract validation, and reproducible verification in EcoCompress AI.
---

# Testing and Quality Skill

## Principles
1. Maintain automated tests for metric calculation formulas, acceptance threshold logic, and API request schemas.
2. Maintain UI component rendering tests and lint checks for the Next.js frontend.
3. Every milestone report must include the exact test commands run, actual execution output, and pass/fail counts.
4. Never replace real implementation with mocks just to make tests pass; use mocks only for external network or hardware boundaries during isolated unit tests.
