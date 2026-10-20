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

### 3.1 Running Backend & Frontend Together

1. **Start the FastAPI Backend Service:**
   ```powershell
   cd "D:\Projects\Compression AI"
   python services/api/main.py
   ```
   * Live API available at: `http://127.0.0.1:8000`
   * Interactive Swagger documentation at: `http://127.0.0.1:8000/docs`
   * Automatically initializes SQLite database at `data/ecocompress.db`.

2. **Start the Next.js Frontend (in a separate terminal):**
   ```powershell
   cd "D:\Projects\Compression AI\apps\web"
   npm run dev
   ```
   * Open [http://localhost:3000](http://localhost:3000) in your browser.
   * Header status will indicate `🟢 API: Online`.
   * Configured experiments in the "New Experiment" tab are persisted to SQLite and appear in the "Dashboard Overview" table with real-time status and cancellation controls.

---

## 4. Phase 2 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service readiness and phase status. |
| `GET` | `/system` | Read-only hardware telemetry (RAM, drives, RTX 2050 profile). |
| `POST` | `/experiments` | Creates and validates a new experiment record in SQLite. |
| `GET` | `/experiments` | Retrieves paginated experiment summaries ordered by creation date. |
| `GET` | `/experiments/{id}` | Retrieves complete experiment configuration, thresholds, and outcomes. |
| `POST` | `/experiments/{id}/run` | Enqueues an experiment into the background queue (`created` $\rightarrow$ `queued`). |
| `POST` | `/experiments/{id}/cancel` | Cancels an eligible active experiment (rejects terminal states). |

---

## 5. Running Automated Tests

Run the complete backend test suite (contract tests, persistence, state transitions, sanitization):
```powershell
cd "D:\Projects\Compression AI"
python -m unittest discover -s tests -p "test_*.py" -v
```
*(All 14 unit and integration tests run against isolated temporary test databases without altering the dev database).*

Run frontend type checks and static production build:
```powershell
cd "D:\Projects\Compression AI\apps\web"
npm run lint
npm run build
```

---

## 6. Roadmap to Phase 3

Now that Phase 2 (Persistent API & Experiment Lifecycle) is complete, **Phase 3** will introduce:
1. **Model Source & License Verification:** Inspecting Hugging Face repositories, revisions, `.safetensors` header metadata, and license terms without downloading complete weight tensors.
2. **Device & VRAM Feasibility Gates:** Dynamic evaluation of GPU memory headroom vs expected model activation footprint.
3. **Hardware Runtime Detector:** Validating CUDA device capabilities and fallback error paths for unsupported architectures.
