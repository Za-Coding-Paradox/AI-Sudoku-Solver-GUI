@echo off
REM setup.bat — Bootstrap the Sudoku Solver development environment (Windows)
REM
REM Usage:
REM   setup.bat                install everything (default)
REM   setup.bat --test         install + run full test suite
REM   setup.bat --test-only    run tests only (venv must already exist)
REM   setup.bat --help         show this help

SETLOCAL ENABLEDELAYEDEXPANSION

SET VENV_DIR=.venv
SET PYTHON_MIN_MAJOR=3
SET PYTHON_MIN_MINOR=11
SET RUN_TESTS=0
SET TEST_ONLY=0
SET TEST_EXIT=0

REM ── Parse arguments ──────────────────────────────────────────────────────────
IF "%~1"=="--help"      GOTO :SHOW_HELP
IF "%~1"=="-h"          GOTO :SHOW_HELP
IF "%~1"=="--test"      SET RUN_TESTS=1
IF "%~1"=="--test-only" SET RUN_TESTS=1 & SET TEST_ONLY=1
IF NOT "%~1"=="" IF NOT "%~1"=="--test" IF NOT "%~1"=="--test-only" (
    echo [ERROR] Unknown argument: %~1
    echo         Run 'setup.bat --help' for usage.
    EXIT /B 1
)

REM ── Banner ────────────────────────────────────────────────────────────────────
echo.
echo   +==========================================+
echo   ^|      Sudoku Solver -- setup.bat          ^|
echo   +==========================================+
echo.

REM ────────────────────────────────────────────────────────────────────────────
REM INSTALL SECTION (skipped with --test-only)
REM ────────────────────────────────────────────────────────────────────────────
IF %TEST_ONLY%==1 GOTO :ACTIVATE_ONLY

REM ── Check Python ─────────────────────────────────────────────────────────────
echo --- Step 1 ^| Checking Python ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] python not found. Install Python 3.11+ and add it to PATH.
    EXIT /B 1
)

FOR /F "tokens=2" %%V IN ('python --version 2^>^&1') DO SET PY_VERSION=%%V
FOR /F "tokens=1,2 delims=." %%A IN ("!PY_VERSION!") DO (
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

REM ── Virtual environment ───────────────────────────────────────────────────────
echo.
echo --- Step 2 ^| Virtual environment ---
IF EXIST "%VENV_DIR%\" (
    echo [WARN]  Virtual environment already exists at %VENV_DIR% -- skipping creation.
) ELSE (
    echo [INFO]  Creating virtual environment at %VENV_DIR% ...
    python -m venv %VENV_DIR%
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to create virtual environment.
        EXIT /B 1
    )
    echo [OK]    Virtual environment created.
)

REM ── Activate ─────────────────────────────────────────────────────────────────
CALL %VENV_DIR%\Scripts\activate.bat
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to activate virtual environment.
    EXIT /B 1
)

REM ── Install dependencies ──────────────────────────────────────────────────────
echo.
echo --- Step 3 ^| Installing dependencies ---
echo [INFO]  Upgrading pip ...
pip install --upgrade pip --quiet

echo [INFO]  Installing project + dev dependencies (pygame-ce, pytest, ruff, mypy, ...) ...
pip install -e ".[dev]" --quiet
IF ERRORLEVEL 1 (
    echo [ERROR] Dependency installation failed.
    EXIT /B 1
)
echo [OK]    All dependencies installed.

REM ── Health check ─────────────────────────────────────────────────────────────
echo.
echo --- Step 4 ^| Health check ---
echo [INFO]  Verifying core imports ...
python -c "import pygame; print('  pygame-ce', pygame.__version__, ' OK')"
IF ERRORLEVEL 1 (
    echo [ERROR] pygame-ce import failed -- check installation.
    EXIT /B 1
)
python -c "import pytest; print('  pytest', pytest.__version__, '   OK')"
IF ERRORLEVEL 1 (
    echo [ERROR] pytest import failed -- check installation.
    EXIT /B 1
)
echo [OK]    Health check passed.
GOTO :RUN_TESTS_SECTION

REM ── Activate only (--test-only path) ─────────────────────────────────────────
:ACTIVATE_ONLY
IF NOT EXIST "%VENV_DIR%\" (
    echo [ERROR] No virtual environment found at %VENV_DIR%. Run 'setup.bat' first.
    EXIT /B 1
)
CALL %VENV_DIR%\Scripts\activate.bat
echo [INFO]  Using existing virtual environment at %VENV_DIR%.

REM ────────────────────────────────────────────────────────────────────────────
REM TEST SECTION
REM ────────────────────────────────────────────────────────────────────────────
:RUN_TESTS_SECTION
IF %RUN_TESTS%==0 GOTO :SUMMARY

echo.
echo --- Running test suite ---
echo.
echo   Command: pytest --tb=short -v
echo   ----------------------------------------
echo.

pytest --tb=short -v
SET TEST_EXIT=%ERRORLEVEL%

echo.
IF %TEST_EXIT%==0 (
    echo   [OK] All tests passed!
) ELSE (
    echo   [FAIL] Some tests failed ^(exit code %TEST_EXIT%^).
    echo          Review the output above for details.
)

REM ── Summary ───────────────────────────────────────────────────────────────────
:SUMMARY
echo.
echo   ==========================================
IF %TEST_ONLY%==0 echo   Setup complete!
echo.
echo   Activate the environment:
echo     %VENV_DIR%\Scripts\activate.bat
echo.
echo   Run the solver:
echo     python -m sudoku.app
echo.
echo   Run tests (full suite with coverage):
echo     setup.bat --test
echo     setup.bat --test-only    (if env already installed)
echo     pytest                   (inside activated venv)
echo.
echo   Run a specific test file:
echo     pytest tests/test_gui/test_theme.py -v
echo.
echo   Run tests by name pattern:
echo     pytest -k "test_toggle" -v
echo   ==========================================
echo.

IF %RUN_TESTS%==1 EXIT /B %TEST_EXIT%
ENDLOCAL
EXIT /B 0

REM ── Help ─────────────────────────────────────────────────────────────────────
:SHOW_HELP
echo.
echo Usage: setup.bat [OPTION]
echo.
echo   (no flags)    Install venv + dependencies
echo   --test        Install everything, then run full test suite
echo   --test-only   Run tests only (venv must already exist)
echo   --help, -h    Show this message
echo.
EXIT /B 0
