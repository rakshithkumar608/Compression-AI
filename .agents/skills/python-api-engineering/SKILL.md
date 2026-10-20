---
name: python-api-engineering
description: Standards for FastAPI service design, Pydantic data schemas, and request-worker decoupling.
---

# Python API Engineering Skill

## Principles
1. Use FastAPI with strict Pydantic v2 schemas for all requests, responses, and database projections.
2. Long-running model benchmarks, quantization jobs, or heavy calculations must **never** run synchronously inside HTTP request handlers.
3. Endpoints must enqueue jobs into SQLite / task storage and return immediate job IDs with status endpoints (`/jobs/{id}`).
4. Validate input paths and model identifiers to prevent path traversal or SSRF vulnerabilities.
5. Provide structured, predictable JSON error responses with standard error codes and human-readable recovery advice.
