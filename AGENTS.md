# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

KRI (Kommunal Finansiell Riskindikator) is a Streamlit dashboard ranking Sweden's 290 municipalities on a composite financial risk index (2010-2024). Pure Python, no Docker, no database, no authentication. See `README.md` for full docs.

### Prerequisites

- Python 3.12 (available on the VM). `python3.12-venv` must be installed for the venv.
- Virtual environment lives at `/workspace/venv`. Activate with `source venv/bin/activate`.

### Data pipeline

The dashboard requires two Parquet files in `data/processed/`:

1. `kri_base_data.parquet` — produced by `python scripts/run_pipeline.py` (fetches from public SCB + Kolada APIs, ~70s first run, uses 7-day cache in `data/cache/`).
2. `kri_results.parquet` — produced by running the KRI index builder after the base data exists:
   ```
   python -c "from src.index_builder import KRIBuilder; KRIBuilder().build()"
   ```
   The dashboard will show an error and stop if `kri_results.parquet` is missing.

Both steps are needed before the dashboard or most tests will work.

### Running the app

```
source venv/bin/activate
streamlit run app/main.py --server.port 8501 --server.headless true
```

### Running tests

```
source venv/bin/activate
python -m pytest tests/ -v
```

All 28 tests require `kri_results.parquet` to exist (they skip otherwise).

### Linting

No linter is configured in this project. If you need basic validation, use `python -m py_compile <file>`.

### Key gotchas

- The setup script (`scripts/setup.sh`) requires `python3.12-venv` apt package. The update script handles this.
- `pytest` is not in `requirements.txt`; it is installed separately by the update script.
- The `run_pipeline.py` script only generates `kri_base_data.parquet`. You must separately run `KRIBuilder().build()` to generate `kri_results.parquet`.
- All UI text is in Swedish; code and comments are in English.
- There is a Swedish UI verification skill at `.cursor/skills/swedish-ui-check/SKILL.md` — use it when modifying files under `app/`.
