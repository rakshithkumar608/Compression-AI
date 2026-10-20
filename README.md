# EcoCompress AI

> **Evidence-Based AI Model Compression & Benchmarking Workbench**
> 
> *Phase 1 Foundation: Project Scaffold, Agent Skills, and Next.js Dashboard*

EcoCompress AI is a developer tool and evaluation workbench for measuring whether an optimized AI model retains acceptable task quality while reducing storage size, steady-state latency, peak memory, and energy consumption.

---

## 1. Key Principles & Anti-Greenwashing Guarantee
1. **Evidence-Based Comparisons:** Real benchmark runs under deterministic, identical workloads. Never invent, mock, or extrapolate efficiency or quality metrics.
2. **Strict Metric Labeling:**
   - **Measured:** Hardware telemetry from device sensors (e.g. NVIDIA NVML power accumulators, wall-clock timers, `psutil` process memory).
   - **Estimated:** Mathematical derivations with transparent formulas and documented regional constants (e.g. grid emissions factor $\text{gCO}_2/\text{kWh}$).
   - **Unavailable:** Displayed as `Unavailable` with an explanatory reason (e.g. direct water usage is marked unavailable in MVP; it is never inferred from GPU runtime).
3. **Non-Destructive Optimization:** Original baseline models are read-only. Optimized candidates are stored into distinct artifact directories with full provenance tracking.
4. **Decoupled Worker Execution:** Long-running model profiling and quantization benchmarks run in an asynchronous local worker; they never block the HTTP API.
5. **Storage & Hardware Protection:**
   - Host `C:` drive has limited space (<200 MB free).
   - All caches (`HF_HOME`, `PIP_CACHE_DIR`, `UV_CACHE_DIR`, `NPM_CONFIG_CACHE`), virtual environments, node modules, and artifacts are strictly anchored to `D:` drive (~193 GB free).

---

## 2. Repository Structure

```text
EcoCompress AI/
├── .agents/
│   └── skills/                         # 8 Project-Specific Agent Skills
│       ├── project-planning/SKILL.md
│       ├── frontend-engineering/SKILL.md
│       ├── python-api-engineering/SKILL.md
│       ├── ml-model-optimization/SKILL.md
│       ├── benchmarking-and-evaluation/SKILL.md
│       ├── data-and-artifact-management/SKILL.md
│       ├── testing-and-quality/SKILL.md
│       └── secure-model-handling/SKILL.md
├── apps/
│   └── web/                            # Next.js 14 Dashboard (TypeScript, Tailwind)
│       ├── src/app/                    # App Router Layout & Page
│       ├── src/components/             # Modular Views (Overview, Models, Setup, Compare, Eco)
│       ├── src/lib/                    # Telemetry & Illustrative Preview Data
│       └── src/types/                  # Shared TypeScript Interfaces
├── services/
│   └── api/                            # FastAPI Backend Service
│       └── main.py                     # /health and /system diagnostic endpoints
├── workers/
│   └── optimizer/                      # Model Benchmarking & Optimization Engine (Phase 4-5)
├── data/                               # SQLite database directory (ecocompress.db)
├── artifacts/                          # Saved model artifacts & reports (Git ignored)
├── docs/                               # Project Blueprint & Architecture Specs
│   └── EcoCompress_AI_Complete_MVP_Blueprint.docx
├── tests/                              # Automated test suites
│   └── test_api_health.py              # API contract & diagnostic unit tests
├── .env.example                        # Template for environment configuration
├── .gitignore                          # Excludes artifacts, weights, venv, and caches
├── AGENTS.md                           # Main agent instruction contract
└── README.md                           # Project overview & onboarding guide
```

---

## 3. How to Launch and Inspect

### 3.1 Running the Frontend Dashboard
Navigate to `apps/web` and start the development server:

```powershell
cd "D:\Projects\Compression AI\apps\web"
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

**Features in the Phase 1 UI:**
* **Dashboard Overview:** Displays live hardware telemetry (RTX 2050 4GB VRAM, RAM, D: drive free space) and recent experiments.
* **Illustrative Preview Toggle:** Switch between a clean workspace and an illustrative preview of a DistilBERT ONNX INT8 compression benchmark, prominently watermarked as a non-fabricated preview.
* **Model Workspace & Safe Inspector:** Browse supported model presets (`distilbert-base-uncased`, `Qwen/Qwen2.5-0.5B`, `HuggingFaceTB/SmolLM-135M`) or inspect custom Hugging Face model IDs. Automatically evaluates VRAM envelope feasibility against the 4GB hardware limit.
* **Experiment Setup Wizard:** Configure task workloads, evaluation sample sizes, batch sizes, quantization backends, and acceptance thresholds.
* **Results & Comparison View:** Side-by-side comparison of baseline vs candidate metrics (artifact size, latency, memory, task quality, energy, and carbon) with acceptance gate reasoning.
* **Environmental Methodology:** Transparent documentation of measured vs estimated metrics and the anti-greenwashing policy for water consumption.
* **Host Diagnostics:** Hardware and runtime telemetry breakdown.

### 3.2 Running the Backend API
Navigate to `services/api` and start the FastAPI service:

```powershell
cd "D:\Projects\Compression AI"
python services/api/main.py
```

Endpoints available at [http://127.0.0.1:8000](http://127.0.0.1:8000):
* `GET /health` — Service readiness check.
* `GET /system` — Read-only hardware telemetry and storage status.
* `GET /docs` — Interactive OpenAPI / Swagger UI.

### 3.3 Running Automated Tests
Run the API unit test suite:

```powershell
cd "D:\Projects\Compression AI"
python tests/test_api_health.py
```

Run frontend linting & static build validation:

```powershell
cd "D:\Projects\Compression AI\apps\web"
npm run lint
npm run build
```

---

## 4. Roadmap to Phase 2

Now that Phase 1 (Repository Foundation & UI Dashboard) is complete, **Phase 2** will introduce:
1. **SQLite Database Layer:** Schema for `experiments`, `model_profiles`, `benchmark_results`, and `jobs`.
2. **FastAPI Experiment Endpoints:** `POST /experiments`, `GET /experiments`, `GET /experiments/{id}`, and `POST /experiments/{id}/run`.
3. **Decoupled Job Queue Engine:** Background task dispatcher managing job states (`queued` $\rightarrow$ `completed`/`failed`) without blocking HTTP handlers.
4. **Mock Execution Fixture:** End-to-end integration test verifying the API contract and frontend communication prior to downloading real ML model weights.
