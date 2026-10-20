---
name: data-and-artifact-management
description: Guidelines for managing SQLite experiment storage, disk artifact quotas, and directory policies.
---

# Data and Artifact Management Skill

## Principles
1. Store experiment metadata, run parameters, job states, and calculated metrics in SQLite (`data/ecocompress.db`).
2. Heavy model weights and serialized checkpoints must live on disk in `artifacts/`, never stored as database blobs.
3. Keep all artifacts on `D:` drive. Verify free space before allocating disk for model checkpoints.
4. Temporary scratch files must be strictly isolated to `D:\Temp` or `artifacts/tmp` and purged upon completion.
5. All artifact and cache directories must be ignored by Git.
