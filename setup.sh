#!/usr/bin/env bash
# setup.sh — Bootstrap the Sudoku Solver development environment (Linux / macOS)
#
# Usage:
#   ./setup.sh            — install everything (default)
#   ./setup.sh --test     — install + run full test suite
#   ./setup.sh --test-only — run tests only (skip install, venv must exist)
#
set -euo pipefail

PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=11
VENV_DIR=".venv"
RUN_TESTS=false
TEST_ONLY=false

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --test)      RUN_TESTS=true ;;
        --test-only) RUN_TESTS=true; TEST_ONLY=true ;;
        --help|-h)
            echo "Usage: ./setup.sh [--test] [--test-only]"
            echo ""
            echo "  (no flags)   Install venv + dependencies"
            echo "  --test       Install + run full test suite"
            echo "  --test-only  Run tests only (venv must already exist)"
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown argument: $arg"
            echo "        Run './setup.sh --help' for usage."
            exit 1
            ;;
    esac
done

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       Sudoku Solver — setup.sh           ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ────────────────────────────────────────────────────────────────────────────
# INSTALL SECTION (skipped with --test-only)
# ────────────────────────────────────────────────────────────────────────────
if [[ "$TEST_ONLY" == false ]]; then

    # ── Check Python version ─────────────────────────────────────────────────
    header "Step 1 — Checking Python"
    if ! command -v python3 &>/dev/null; then
        error "python3 not found. Install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+."
    fi

    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [[ "$PY_MAJOR" -lt "$PYTHON_MIN_MAJOR" ]] || \
       [[ "$PY_MAJOR" -eq "$PYTHON_MIN_MAJOR" && "$PY_MINOR" -lt "$PYTHON_MIN_MINOR" ]]; then
        error "Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ required. Found $PY_VERSION."
    fi
    success "Python $PY_VERSION found."

    # ── Virtual environment ──────────────────────────────────────────────────
    header "Step 2 — Virtual environment"
    if [[ -d "$VENV_DIR" ]]; then
        warn "Virtual environment already exists at $VENV_DIR — skipping creation."
    else
        info "Creating virtual environment at $VENV_DIR ..."
        python3 -m venv "$VENV_DIR"
        success "Virtual environment created."
    fi

    # ── Activate ─────────────────────────────────────────────────────────────
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"

    # ── Upgrade pip ──────────────────────────────────────────────────────────
    header "Step 3 — Installing dependencies"
    info "Upgrading pip ..."
    pip install --upgrade pip --quiet

    info "Installing project + dev dependencies (pygame-ce, pytest, ruff, mypy, ...) ..."
    pip install -e ".[dev]" --quiet
    success "All dependencies installed."

    # ── Health check ─────────────────────────────────────────────────────────
    header "Step 4 — Health check"
    info "Verifying core imports ..."
    python3 -c "import pygame; print(f'  pygame-ce {pygame.__version__}  ✓')" \
        || error "pygame-ce import failed — check installation."
    python3 -c "import sudoku; print('  sudoku package       ✓')" 2>/dev/null \
        || warn "sudoku package not importable yet (normal before first run)."
    python3 -c "import pytest; print(f'  pytest {pytest.__version__}        ✓')" \
        || error "pytest import failed — check installation."
    success "Health check passed."

else
    # --test-only: just activate the existing venv
    if [[ ! -d "$VENV_DIR" ]]; then
        error "No virtual environment found at $VENV_DIR. Run './setup.sh' first."
    fi
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    info "Using existing virtual environment at $VENV_DIR."
fi

# ────────────────────────────────────────────────────────────────────────────
# TEST SECTION
# ────────────────────────────────────────────────────────────────────────────
if [[ "$RUN_TESTS" == true ]]; then
    header "Running test suite"
    echo ""
    echo "  Command: pytest --tb=short -v"
    echo "  ─────────────────────────────────────────"
    echo ""

    # Run pytest; capture exit code without letting set -e kill the script
    set +e
    pytest --tb=short -v
    TEST_EXIT=$?
    set -e

    echo ""
    if [[ "$TEST_EXIT" -eq 0 ]]; then
        echo -e "${GREEN}  ✓  All tests passed!${NC}"
    else
        echo -e "${RED}  ✗  Some tests failed (exit code $TEST_EXIT).${NC}"
        echo "     Review the output above for details."
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  ══════════════════════════════════════════${NC}"
if [[ "$TEST_ONLY" == false ]]; then
    echo -e "${GREEN}  Setup complete!${NC}"
fi
echo ""
echo "  Activate the environment:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  Run the solver:"
echo "    python -m sudoku.app"
echo ""
echo "  Run tests (full suite with coverage):"
echo "    ./setup.sh --test"
echo "    ./setup.sh --test-only   (if env already installed)"
echo "    pytest                   (inside activated venv)"
echo ""
echo "  Run a specific test file:"
echo "    pytest tests/test_gui/test_theme.py -v"
echo ""
echo "  Run tests by name pattern:"
echo "    pytest -k 'test_toggle' -v"
echo -e "${GREEN}  ══════════════════════════════════════════${NC}"
echo ""

if [[ "$RUN_TESTS" == true ]] && [[ "$TEST_EXIT" -ne 0 ]]; then
    exit "$TEST_EXIT"
fi
