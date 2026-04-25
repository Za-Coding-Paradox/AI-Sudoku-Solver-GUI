#!/usr/bin/env bash
# setup.sh — Bootstrap the Sudoku Solver development environment (Linux / macOS)
set -euo pipefail

PYTHON_MIN="3.11"
VENV_DIR=".venv"

# ── Colour helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Banner ──────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Sudoku Solver — setup.sh         ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── Check Python version ────────────────────────────────────────────────────
info "Checking Python version..."
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python $PYTHON_MIN or higher."
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_MAJOR=3; REQUIRED_MINOR=11

ACTUAL_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
ACTUAL_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$ACTUAL_MAJOR" -lt "$REQUIRED_MAJOR" ]] || \
   [[ "$ACTUAL_MAJOR" -eq "$REQUIRED_MAJOR" && "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]]; then
    error "Python $PYTHON_MIN+ required. Found $PYTHON_VERSION."
fi
success "Python $PYTHON_VERSION found."

# ── Create virtual environment ───────────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    warn "Virtual environment already exists at $VENV_DIR — skipping creation."
else
    info "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    success "Virtual environment created."
fi

# ── Activate + install ──────────────────────────────────────────────────────
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

info "Upgrading pip..."
pip install --upgrade pip --quiet

info "Installing project + dev dependencies..."
pip install -e ".[dev]" --quiet
success "Dependencies installed."

# ── Pre-commit hooks ─────────────────────────────────────────────────────────
if command -v pre-commit &>/dev/null; then
    info "Installing pre-commit hooks..."
    pre-commit install --quiet
    success "Pre-commit hooks installed."
else
    warn "pre-commit not found in PATH — skipping hook installation."
fi

# ── Health check ─────────────────────────────────────────────────────────────
info "Running health check..."
python3 -c "import pygame; print(f'  pygame-ce {pygame.__version__} OK')" || \
    error "pygame-ce import failed."
python3 -c "import sudoku; print(f'  sudoku package OK')" 2>/dev/null || \
    warn "sudoku package not importable yet (normal before first run)."
success "Health check passed."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo "  Activate the environment:   source $VENV_DIR/bin/activate"
echo "  Run the solver:             make run"
echo "  Run tests:                  make test"
echo ""
