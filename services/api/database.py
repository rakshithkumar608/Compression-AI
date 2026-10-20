"""
SQLite connection manager and schema initializer for EcoCompress AI.
Ensures ACID safety, WAL mode, foreign keys, and transaction management.
"""

import sqlite3
from pathlib import Path
from typing import Generator
from contextlib import contextmanager
from config import settings


def get_db_path(custom_path: Path | str | None = None) -> Path | str:
    if custom_path is not None:
        return custom_path
    return settings.db_path


def init_db(db_path: Path | str | None = None) -> None:
    """Initializes tables and indexes in the SQLite database."""
    target_path = get_db_path(db_path)
    
    if isinstance(target_path, Path):
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    with conn:
        # 1. Experiments Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model_id TEXT NOT NULL,
                task TEXT NOT NULL,
                optimization_method TEXT NOT NULL,
                workload_config TEXT NOT NULL,
                thresholds TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_summary TEXT,
                acceptance_decision TEXT
            );
        """)

        # 2. Benchmark Results Table (Baseline & Candidate metrics)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                candidate_type TEXT NOT NULL, -- 'baseline' or 'candidate'
                artifact_size_mb REAL,
                median_latency_ms REAL,
                p95_latency_ms REAL,
                peak_memory_mb REAL,
                quality_score REAL,
                quality_metric_name TEXT,
                energy_joules REAL,
                energy_measurement_type TEXT, -- 'measured' or 'estimated'
                carbon_grams REAL,
                carbon_measurement_type TEXT, -- 'estimated'
                water_milliliters REAL,       -- nullable
                water_measurement_type TEXT,  -- 'unavailable'
                measured_runs INTEGER,
                warmup_runs INTEGER,
                hardware_device TEXT,
                recorded_at TEXT NOT NULL,
                runtime_name TEXT,
                model_revision TEXT,
                metadata_json TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
            );
        """)

        # Safe migration for existing databases: check for new columns
        cur = conn.execute("PRAGMA table_info(benchmark_results);")
        existing_cols = [row[1] for row in cur.fetchall()]
        if "runtime_name" not in existing_cols:
            conn.execute("ALTER TABLE benchmark_results ADD COLUMN runtime_name TEXT;")
        if "model_revision" not in existing_cols:
            conn.execute("ALTER TABLE benchmark_results ADD COLUMN model_revision TEXT;")
        if "metadata_json" not in existing_cols:
            conn.execute("ALTER TABLE benchmark_results ADD COLUMN metadata_json TEXT;")

        # 3. Jobs Table (Decoupled background worker dispatch tracking)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT NOT NULL,
                progress_pct INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
            );
        """)

        # Indexes for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_results_exp ON benchmark_results(experiment_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_exp ON jobs(experiment_id);")

    conn.close()


@contextmanager
def get_db(db_path: Path | str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a SQLite connection with row_factory enabled."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
