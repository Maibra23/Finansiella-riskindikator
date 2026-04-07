#!/usr/bin/env bash
# =============================================================================
# KRI Dashboard – setup script
# Installs dependencies, fetches data from SCB/Kolada, and builds the index.
#
# Usage:
#   bash scripts/setup.sh          # full setup
#   bash scripts/setup.sh --no-data  # install deps only (skip data fetch)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "========================================"
echo "  KRI Dashboard – Setup"
echo "========================================"
echo ""

# ── 1. Python version check ──────────────────────────────────────────────────
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(sys.version_info >= (3,11))")
        if [ "$version" = "True" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.11+ is required. Please install it and try again."
    exit 1
fi
echo "Python: $($PYTHON_CMD --version)"

# ── 2. Virtual environment ───────────────────────────────────────────────────
VENV_DIR="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

# Activate
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows Git Bash / MSYS2
    source "$VENV_DIR/Scripts/activate"
fi
echo "Virtual environment: $VIRTUAL_ENV"

# ── 3. Install dependencies ──────────────────────────────────────────────────
echo ""
echo "Installing Python dependencies from requirements.txt ..."
pip install --upgrade pip --quiet
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
echo "Dependencies installed."

# ── 4. Create required directories ───────────────────────────────────────────
mkdir -p "$PROJECT_ROOT/data/raw"
mkdir -p "$PROJECT_ROOT/data/cache"
mkdir -p "$PROJECT_ROOT/data/processed"
mkdir -p "$PROJECT_ROOT/data/geo"
mkdir -p "$PROJECT_ROOT/report"

# ── 5. Copy environment file ─────────────────────────────────────────────────
if [ ! -f "$PROJECT_ROOT/.env" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo ".env created from .env.example"
fi

# ── 6. Data pipeline ─────────────────────────────────────────────────────────
if [[ "${1:-}" != "--no-data" ]]; then
    echo ""
    echo "Fetching data from SCB and Kolada APIs ..."
    echo "(This may take 2–5 minutes on first run; subsequent runs use the cache.)"
    echo ""
    "$PYTHON_CMD" "$PROJECT_ROOT/scripts/run_pipeline.py"
    echo ""
    echo "Data pipeline complete."
else
    echo ""
    echo "Skipping data fetch (--no-data flag set)."
    echo "Run 'python scripts/run_pipeline.py' manually to fetch data."
fi

# ── 7. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Setup complete!"
echo ""
echo "  Start the dashboard:"
echo "    streamlit run app/main.py"
echo ""
echo "  Or with the virtual environment:"
echo "    source venv/bin/activate   # Linux/macOS"
echo "    venv\\Scripts\\activate      # Windows"
echo "    streamlit run app/main.py"
echo "========================================"
echo ""
