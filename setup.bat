@echo off
REM setup.bat — Bootstrap the Sudoku Solver development environment (Windows)
SETLOCAL ENABLEDELAYEDEXPANSION

SET VENV_DIR=.venv
SET PYTHON_MIN_MAJOR=3
SET PYTHON_MIN_MINOR=11

echo.
echo   ╔══════════════════════════════════════╗
echo   ║     Sudoku Solver — setup.bat        ║
echo   ╚══════════════════════════════════════╝
echo.

REM ── Check Python ────────────────────────────────────────────────────────────
echo [INFO]  Checking Python version...
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] python not found. Install Python 3.11+ and add it to PATH.
    EXIT /B 1
)

FOR /F "tokens=2" %%V IN ('python --version 2^>^&1') DO SET PY_VERSION=%%V
FOR /F "tokens=1,2 delims=." %%A IN ("%PY_VERSION%") DO (
    SET PY_MAJOR=%%A
    SET PY_MINOR=%%B
)

IF !PY_MAJOR! LSS %PYTHON_MIN_MAJOR% (
    echo [ERROR] Python 3.11+ required. Found !PY_VERSION!.
    EXIT /B 1
)
IF !PY_MAJOR! EQU %PYTHON_MIN_MAJOR% IF !PY_MINOR! LSS %PYTHON_MIN_MINOR% (
    echo [ERROR] Python 3.11+ required. Found !PY_VERSION!.
    EXIT /B 1
)
echo [OK]    Python !PY_VERSION! found.

REM ── Virtual environment ──────────────────────────────────────────────────────
IF EXIST "%VENV_DIR%\" (
    echo [WARN]  Virtual environment already exists at %VENV_DIR% — skipping creation.
) ELSE (
    echo [INFO]  Creating virtual environment at %VENV_DIR%...
    python -m venv %VENV_DIR%
    echo [OK]    Virtual environment created.
)

REM ── Activate ─────────────────────────────────────────────────────────────────
CALL %VENV_DIR%\Scripts\activate.bat

REM ── Upgrade pip + install ────────────────────────────────────────────────────
echo [INFO]  Upgrading pip...
pip install --upgrade pip --quiet

echo [INFO]  Installing project + dev dependencies...
pip install -e ".[dev]" --quiet
echo [OK]    Dependencies installed.

REM ── Pre-commit ───────────────────────────────────────────────────────────────
WHERE pre-commit >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo [INFO]  Installing pre-commit hooks...
    pre-commit install --quiet
    echo [OK]    Pre-commit hooks installed.
) ELSE (
    echo [WARN]  pre-commit not found — skipping hook installation.
)

REM ── Health check ─────────────────────────────────────────────────────────────
echo [INFO]  Running health check...
python -c "import pygame; print('  pygame-ce', pygame.__version__, 'OK')"
IF ERRORLEVEL 1 (
    echo [ERROR] pygame-ce import failed.
    EXIT /B 1
)
echo [OK]    Health check passed.

REM ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo   Setup complete!
echo.
echo   Activate the environment:   %VENV_DIR%\Scripts\activate.bat
echo   Run the solver:             python -m sudoku.app
echo   Run tests:                  pytest
echo.
ENDLOCAL
