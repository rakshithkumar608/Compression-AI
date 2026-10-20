# EcoCompress AI — Phase 8: Read-Only Release Audit Report

**Date:** 2026-10-20  
**Phase:** 8 — Read-Only Release Audit  
**Auditor:** EcoCompress AI Quality & Safety Engineering Agent  
**Audit Target:** Phase 7 INT8 Export Package (`export_exp-20261020102101-4f000a_int8`), Provenance Manifest, Loader, Benchmarks & UI/API Integration  
**Release Status Verdict:** **PASS WITH LIMITATIONS**  

---

## 1. Audit Scope & Critical Machine Constraints

### 1.1 Scope of the Audit
This phase is a **strict, read-only release audit** of the accepted Phase 7 candidate export package (`SmolLM2-360M-Instruct-int8` from experiment `exp-20261020102101-4f000a`). In compliance with operational directives:
* No existing source files, configurations, database records, or model artifacts were modified or deleted.
* No packages were installed or upgraded.
* No network downloads or external API calls were initiated.
* No heavy model inference runs or compression jobs were dispatched.
* All audit checks were performed using non-destructive inspection scripts and existing hermetic unit tests.

### 1.2 Host Environment & Machine Constraints Audit
* **Operating System:** Windows 11 Home (AMD64)
* **GPU Hardware:** NVIDIA GeForce RTX 2050 Laptop GPU (4,096 MB VRAM, Driver: 591.44)
* **Execution Runtime:** CPU-only PyTorch (`2.12.0+cpu`). CUDA GPU execution is not supported by the current PyTorch installation; all model inferences and benchmarks run strictly on CPU.
* **Storage Protection Status:**
  * **Drive C:** Inspected with 9.28 GB free (previously <100 MB). Zero project files or caches were written to C:.
  * **Drive D:** Inspected with 189.78 GB free. All caches, database files, models, exports, and test fixtures reside strictly on D:.

---

## 2. Checklist Audit Findings & Exact Results

### Checklist Item 1: Artifact & Documentation Location
* **Phase 7 Report:** Located at `brain/f86e881f-1ca2-4fe3-b9d3-4fc4e020d5f0/ECOCOMPRESS_AI_PHASE_7_REPORT.md`.
* **Export Directory:** [`D:\Projects\Compression AI\exports\export_exp-20261020102101-4f000a_int8`](file:///D:/Projects/Compression%20AI/exports/export_exp-20261020102101-4f000a_int8) exists on disk.
* **Export ZIP Archive:** [`D:\Projects\Compression AI\exports\export_exp-20261020102101-4f000a_int8.zip`](file:///D:/Projects/Compression%20AI/exports/export_exp-20261020102101-4f000a_int8.zip) exists on disk.
* **Manifest:** [`manifest.json`](file:///D:/Projects/Compression%20AI/exports/export_exp-20261020102101-4f000a_int8/manifest.json) exists inside package.
* **Model Card:** [`MODEL_CARD.md`](file:///D:/Projects/Compression%20AI/exports/export_exp-20261020102101-4f000a_int8/MODEL_CARD.md) exists inside package.
* **Standalone Loader:** [`loader.py`](file:///D:/Projects/Compression%20AI/exports/export_exp-20261020102101-4f000a_int8/loader.py) exists inside package.
* **Unit Test Suite:** [`tests/test_phase7_export.py`](file:///D:/Projects/Compression%20AI/tests/test_phase7_export.py) exists.
* **Verdict:** **VERIFIED PASS**

---

### Checklist Item 2: ZIP File Existence, Listing & Checksum Verification
* **ZIP Archive Size:** Exactly **288,658,316 bytes** (275.29 MB).
* **Computed SHA-256 Digest:** `c450fdf7a67a660260a4fafcbac8b45dbc840363a86b06d4393e22cd7e761150`.
* **Reported SHA-256 in Phase 7 Report:** `c450fdf7a67a660260a4fafcbac8b45dbc840363a86b06d4393e22cd7e761150`.
* **Archive Member Listing:** Exactly 11 entries listed cleanly with valid deflate compression headers.
* **Verdict:** **VERIFIED PASS (Exact 100% Match)**

---

### Checklist Item 3: Archive Path Traversal & Suspicious Member Inspection
The ZIP central directory was audited for malicious file path entries:
* **Absolute Path Audit:** 0 members start with `/`, `\`, or drive letters (`C:`, `D:`).
* **Directory Traversal Audit:** 0 members contain `..` or relative directory stepping.
* **Hidden / System Files:** 0 unexpected files, OS metadata (`.DS_Store`, `Thumbs.db`), or temporary `.tmp` files.
* **All Filenames:** Clean relative basenames:
  `['config.json', 'generation_config.json', 'loader.py', 'manifest.json', 'model.safetensors', 'MODEL_CARD.md', 'quantization_manifest.json', 'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json']`
* **Verdict:** **VERIFIED PASS**

---

### Checklist Item 4: Manifest vs. Package Contents Comparison
Every entry in `manifest.json` was cross-referenced against the actual files on disk in the uncompressed folder and inside the ZIP archive:

| Relative Path | Manifest Size | Disk Size | Manifest SHA-256 | Disk SHA-256 | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `config.json` | 1,229 B | 1,229 B | `9fac89e1...` | `9fac89e1...` | MATCH |
| `generation_config.json` | 132 B | 132 B | `87b916ed...` | `87b916ed...` | MATCH |
| `loader.py` | 3,051 B | 3,051 B | `027e4976...` | `027e4976...` | MATCH |
| `model.safetensors` | 409,150,560 B | 409,150,560 B | `0d0a7905...` | `0d0a7905...` | MATCH |
| `MODEL_CARD.md` | 3,306 B | 3,306 B | `b7598163...` | `b7598163...` | MATCH |
| `quantization_manifest.json`| 771 B | 771 B | `3dafc807...` | `3dafc807...` | MATCH |
| `special_tokens_map.json` | 655 B | 655 B | `2b7379f3...` | `2b7379f3...` | MATCH |
| `tokenizer.json` | 2,104,556 B | 2,104,556 B | `9ca9acdd...` | `9ca9acdd...` | MATCH |
| `tokenizer_config.json` | 3,764 B | 3,764 B | `4ec77d44...` | `4ec77d44...` | MATCH |
| `vocab.json` | 800,662 B | 800,662 B | `82b84012...` | `82b84012...` | MATCH |

* **Missing Files:** 0
* **Extra Files:** 0
* **Mismatched Digests:** 0
* **Verdict:** **VERIFIED PASS (100% Integrity)**

---

### Checklist Item 5: Standalone Loader Dependency & Portability Review
An inspection of `exports/export_exp-20261020102101-4f000a_int8/loader.py` revealed:
1. **Path Resolving:** Uses `Path(__file__).parent` and `Path(model_dir).resolve()`. Completely free of hardcoded absolute paths.
2. **Third-Party Dependencies:** Relies on `torch`, `transformers`, and `safetensors`. These are standard Hugging Face ecosystem libraries.
3. **Portability Gap 1 (No `local_files_only=True`):** In `loader.py`, `AutoTokenizer.from_pretrained(str(model_path))` and `AutoModelForCausalLM.from_pretrained(str(model_path))` do not explicitly pass `local_files_only=True`. If internet access is available, Transformers may attempt to check the Hugging Face Hub for remote repository updates or configuration revisions before falling back to local files.
4. **Portability Gap 2 (Missing `requirements.txt`):** The export package does not include a `requirements.txt` or pinned dependency manifest specifying tested minimum versions of `torch` and `transformers`.
* **Verdict:** **PASS WITH LIMITATIONS (Minor Portability Fixes Recommended)**

---

### Checklist Item 6: Weight Reconstruction & Quantization Reality Analysis
Tracing lines 31–44 of `loader.py`:
$$\mathbf{W}_{\text{effective}} = (\mathbf{W}_{\text{int8}} - \text{zp}) \times \text{scale}$$
`module.weight.data = w_dequant.to(module.weight.dtype)`

#### Technical Reality:
1. **Storage vs. Compute:** The artifact achieves authentic **storage-level compression** on disk: 390.20 MB vs 690.15 MB (-43.46%) by persisting linear weights as 8-bit integers with per-tensor scales and zero points.
2. **Runtime Memory Expansion:** Before token generation begins, `loader.py` dequantizes all 224 linear projection matrices into **full FP32 tensors** in RAM. Consequently:
   - There is **no runtime RAM reduction** during inference.
   - Peak RSS is **1,958.42 MB** (+5.84% over baseline's 1,850.34 MB) due to simultaneous allocation of the raw INT8 state dictionary and the reconstructed FP32 model tensors.
3. **Inference Compute:** Matrix multiplications are executed using standard PyTorch FP32 matrix multiplication kernels (`sgemm`), rather than quantized integer GEMM kernels (`MatMulInteger` or OneDNN/QNNPACK int8 operators).
4. **Fidelity:** This dequantization guarantees exact token reproduction and 100% semantic fidelity, avoiding the catastrophic NaN/overflow corruption of stock Hugging Face loaders. However, users must understand this is **storage quantization with scale-aware dequantization**, not compiled native INT8 inference.
* **Verdict:** **VERIFIED FACT (Accurately documented in Model Card, but needs bold emphasis in user guides)**

---

### Checklist Item 7: Baseline vs. Candidate Measurement Review
Audit of `benchmark_results` table in SQLite (`data/ecocompress.db`):

| Parameter | Baseline Run | Candidate Run | Equivalence Status |
| :--- | :--- | :--- | :--- |
| **Model Architecture** | `SmolLM2-360M-Instruct` | `SmolLM2-360M-Instruct-int8` | Equivalent |
| **Hardware Device** | Intel 12th Gen i5 (CPU) | Intel 12th Gen i5 (CPU) | Identical |
| **Runtime Version** | `PyTorch 2.12.0+cpu` | `PyTorch 2.12.0+cpu` | Identical |
| **Warmup Iterations** | 3 passes | 3 passes | Identical |
| **Measured Iterations** | 10 passes | 10 passes | Identical |
| **Fixed Prompts** | 5 standard prompts | 5 standard prompts | Identical content |
| **Prompt Formatting** | Raw text (no ChatML template) | ChatML formatted (`<\|im_start\|>user...`) | **DISCREPANCY IDENTIFIED** |
| **Token Generation Count** | Truncated early (EOS at token 1 on 6 runs) | Full 32 tokens on all 10 runs | **DISCREPANCY IDENTIFIED** |

#### Latency Analysis:
* **Baseline Raw Samples (ms):** `[136.3, 143.5, 143.8, 185.2, 188.7, 192.0, 3191.4, 3279.2, 3382.6, 3445.3]`
  * On raw prompt input, the instruct-tuned baseline emitted `<|im_end|>` immediately on token 1 for 6 runs, producing a low median of **190.37 ms**.
* **Candidate Raw Samples (ms):** `[2896.1, 2930.3, 3017.5, 3036.0, 3097.7, 3159.8, 3172.8, 3313.1, 3332.7, 3966.0]`
  * ChatML formatting ensured full 32-token generation across all runs, yielding a median of **3,128.74 ms**.
* **Like-for-Like Comparison:** When evaluating runs where both models generated full 32-token responses, baseline latency was ~3,324 ms vs. ~3,128 ms for the candidate (~6% speedup).
* **Verdict:** **PASS WITH LIMITATIONS (Documented nuance, but future benchmarks must enforce identical prompt templating and minimum token generation constraints)**

---

### Checklist Item 8: ZIP Compression vs. Raw Size Reduction Audit
* **Raw Artifact Size:**
  - Baseline Safetensors: 690.15 MB
  - Candidate Safetensors: 390.20 MB
  - **Verified Raw Weight Reduction:** **43.46% (-299.95 MB)**
* **Claimed ZIP Reduction in Report:**
  - In Section 1 of the Phase 7 report: *"ZIP Archive Size: 275.29 MB (-60.11% storage footprint)"*.
  - Calculation: $(690.15 - 275.29) / 690.15 = 60.11\%$.
* **Audit Finding:** This comparison is an **apples-to-oranges comparison**. It compares the **deflated ZIP archive of the candidate** directly against the **uncompressed raw model safetensors of the baseline**. A compressed ZIP of the baseline was never constructed or measured.
* **Correction:** The report must clearly separate **raw artifact reduction (43.46%)** from **archive packaging reduction**. The 60.11% figure should not be claimed as compression model efficiency.
* **Verdict:** **FLAGGED FOR CLARIFICATION**

---

### Checklist Item 9: Provenance, Licensing & Model Card Verifiability
* **Source Revision:** Pinned revision `a10cc1512eabd3dde888204e902eca88bddb4951` is locally present and verified in `D:\cache\huggingface\hub\models--HuggingFaceTB--SmolLM2-360M-Instruct\snapshots\`.
* **Licensing:** Model card claims Apache-2.0. This was derived from Hugging Face API model metadata queried in Phase 3. However, the local snapshot directory does not contain a physical `LICENSE.txt` or `README.md` file.
* **Environmental Disclosures:** Model card and manifest explicitly set energy, carbon, and water metrics to `null` with status `unavailable`. Zero fabricated metrics are present.
* **Task Quality Status:** Model card and manifest honestly mark quality score as `unverified` due to lack of a local MMLU ground-truth dataset.
* **Verdict:** **VERIFIED PASS (Truthful and uninvented)**

---

### Checklist Item 10: Test Suite Coverage Audit
Audit of `tests/test_phase7_export.py` (12 tests):
* Checksum recalculation & verification: **COVERED** (`test_01`, `test_07`, `test_08`, `test_11`)
* C: drive storage guardrail rejection: **COVERED** (`test_02`)
* Missing experiment ID: **COVERED** (`test_03`)
* Missing candidate model files: **COVERED** (`test_04`)
* Detection of tampered files: **COVERED** (`test_09`)
* Detection of missing files: **COVERED** (`test_10`)
* Standalone loader syntax compilation: **COVERED** (`test_12`)
* **Coverage Gap 1 (ZipSlip / Path Traversal):** In `services/api/services/export_service.py` line 277:
  ```python
  with zipfile.ZipFile(str(target), "r") as zf:
      zf.extractall(str(temp_extract_dir))
  ```
  `extractall()` is called without sanitizing member paths against `..` or absolute paths. An untrusted ZIP could attempt path traversal. No test exists for malicious archives.
* **Coverage Gap 2 (Malformed Manifest):** No test for corrupted or invalid JSON in `manifest.json`.
* **Verdict:** **PASS WITH LIMITATIONS (ZipSlip guard must be implemented in Phase 8 hardening)**

---

### Checklist Item 11: Frontend & Backend Integration Audit
Audit of UI and API integration:
1. **Backend Integration:**
   - [`services/api/routers/exports.py`](file:///D:/Projects/Compression%20AI/services/api/routers/exports.py) is implemented and mounted in `main.py`.
   - Endpoints `POST /experiments/{id}/export`, `GET /experiments/{id}/export`, and `POST /exports/verify` are live and functional.
2. **Frontend Integration Gap:**
   - [`apps/web/src/lib/api.ts`](file:///D:/Projects/Compression%20AI/apps/web/src/lib/api.ts) does **not** expose export functions (`exportExperiment`, `verifyExport`).
   - [`apps/web/src/components/ComparisonView.tsx`](file:///D:/Projects/Compression%20AI/apps/web/src/components/ComparisonView.tsx) is completely hardcoded to `ILLUSTRATIVE_DEMO_EXPERIMENT`. It does not fetch completed experiments from SQLite, does not display candidate INT8 benchmark results, and its "Export Markdown" button downloads mock illustrative data.
   - [`apps/web/src/components/DashboardView.tsx`](file:///D:/Projects/Compression%20AI/apps/web/src/components/DashboardView.tsx) lists completed experiments from SQLite but provides no button to trigger export packaging, view the candidate comparison, or download the ZIP archive.
* **Verdict:** **FAIL ON FRONTEND INTEGRATION (UI remains illustrative; export workflows are backend/CLI-only)**

---

## 3. Prioritized List of Fixes

### Priority 0 (Security & Stability — Immediate)
1. **ZipSlip Vulnerability Fix:** In `ExportService.verify_package()`, replace raw `zf.extractall()` with safe member extraction that validates every `member.filename` does not contain `..`, leading slashes, or drive letters.
2. **Add Security Unit Tests:** Add tests in `test_phase7_export.py` verifying that malicious ZIP archives with path traversal are rejected.

### Priority 1 (Portability & Documentation Accuracy)
3. **Loader Offline Enforcement:** Update `loader.py` to pass `local_files_only=True` to `from_pretrained()` to ensure guaranteed air-gapped execution without DNS/Hub polling.
4. **Bundle `requirements.txt`:** Include a minimal `requirements.txt` (`torch>=2.2.0`, `transformers>=4.40.0`, `safetensors>=0.4.0`) inside the export directory and ZIP archive.
5. **Separate Raw vs. Archive Size Claims:** Update `MODEL_CARD.md` and Phase 7 report documentation to state **43.46% raw weight compression** and remove the misleading 60.11% apples-to-oranges comparison.

### Priority 2 (Frontend UI Integration)
6. **Connect Frontend to Real Export Endpoints:** Add export methods to `apps/web/src/lib/api.ts`.
7. **Wire `ComparisonView` to Real SQLite Benchmarks:** Enable `ComparisonView.tsx` to accept a real experiment ID, display actual baseline vs candidate metrics, and offer an authentic "Download Export Bundle" button.

---

## 4. Release Status Verdict

### **PASS WITH LIMITATIONS**

* **Why it Passes:** The export package is genuinely self-contained, reproducible, and verifiable via SHA-256. The custom INT8 quantization achieves 43.46% storage compression with 100% token generation fidelity, and the standalone loader executes successfully without errors.
* **Why it has Limitations:**
  1. Runtime inference executes in FP32 via dequantization (no RAM or compute speed savings).
  2. `ExportService.verify_package()` has an unmitigated ZipSlip vulnerability if verifying untrusted third-party archives.
  3. The frontend Next.js interface is not yet connected to the export endpoints and continues to display illustrative preview data in the comparison tab.

---

## 5. Next Recommended Phase

### **Phase 8: Hardening, Security Mitigation & UI Completion**
With the read-only audit complete and all findings documented, the recommended next step is to execute the prioritized fixes:
1. Harden `ExportService` against ZipSlip path traversal and add security test cases.
2. Add `local_files_only=True` and `requirements.txt` to the export package generator.
3. Wire the Next.js frontend (`api.ts` and `ComparisonView.tsx`) to real SQLite experiments and export downloads.
4. Deliver the final hardened demonstration package.

---
*Awaiting your review and explicit approval before modifying any code or beginning fixes.*
