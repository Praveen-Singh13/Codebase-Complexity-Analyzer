# Codebase Complexity Analyzer

## Video Demo

https://youtu.be/Fo3tPJcLx_4

## Description

The Codebase Complexity Analyzer is a command-line Python tool that scans a folder of `.py` files and reports how difficult the code is to read and maintain. It was built as the CS50P final project so developers can review structure quickly without executing or importing user code.

The tool discovers Python files, measures lines of code and AST-based metrics (functions, classes, loops, nesting depth, function lengths, file size), applies rule-based warnings, and scores each file from 0 to 100. A terminal report shows per-file details with color-coded score bars on TTY output; a PDF report provides the same results in a shareable document. Parse errors are handled gracefully: broken files receive a W-00 warning, a fixed score of 75, and analysis continues for remaining files.

## Features

- Recursive or top-level-only `.py` file discovery with sorted absolute paths
- UTF-8 reading with latin-1 fallback for non-UTF-8 sources
- LOC counting that skips blanks and full-line comments but keeps inline-comment code
- AST metrics: function/class counts, loop count, max nesting depth, function lengths
- Warning engine (W-01–W-06) with configurable length and depth thresholds
- Additive capped complexity scoring with a 100-point ceiling
- Terminal report with metrics, severities, and ASCII complexity bars
- PDF report with title page, tables, warning summary, and score chart
- CLI flags for custom PDF path, recursion toggle, and threshold overrides
- `sample_code/` fixtures for clean, complex, empty, and syntax-error scenarios

## Installation

Requires **Python 3.10+** and `pip`.

```bash
pip install -r requirements.txt
python project.py --help
python project.py sample_code
python project.py sample_code --output my_report.pdf --no-recurse
python project.py sample_code --max-func-len 30 --max-depth 4
python -m pytest test_project.py -v
```

| Flag | Purpose |
|------|---------|
| `folder` | Directory to scan (required) |
| `-o`, `--output` | PDF path (default: `complexity_report.pdf`; overwrites if present) |
| `--max-func-len` | Function-length warning threshold (default: 50) |
| `--max-depth` | Nesting-depth warning threshold (default: 3) |
| `--no-recurse` | Top-level `.py` files only |

## File Breakdown

| Filename | Purpose | Key Functions |
|----------|---------|---------------|
| `project.py` | CLI and analysis pipeline | `main`, `get_python_files`, `count_lines_of_code`, `analyze_ast`, `detect_warnings`, `calculate_complexity_score`, `summarize_results`, `generate_terminal_report`, `generate_pdf_report` |
| `test_project.py` | Pytest suite | `test_get_python_files_*`, `test_count_lines_of_code_*`, `test_calculate_complexity_score_*` |
| `requirements.txt` | Dependencies (`fpdf2`, `pytest`) | — |
| `sample_code/*.py` | Demo and edge-case fixtures | — |

## Design Decisions

**AST over regex.** Structure such as functions and nested loops follows Python grammar; `ast.parse` captures it accurately without running code.

**fpdf2.** The PRD requires a portable PDF with tables and charts; `fpdf2` installs via pip and works on Windows, macOS, and Linux without extra system tools.

**Single `project.py`.** CS50P expects one root entry file with multiple top-level functions. One module keeps discover → parse → score → report flow easy to trace.

**Scoring.** Penalties on function length, nesting, LOC, function count, and average length are each capped; the total clamps at 100. Constants in `SCORING_CONFIG` and `DEFAULT_THRESHOLDS` centralize tuning.

## Future Improvements

- Cyclomatic complexity per function via branch-counting AST walks
- JSON export and baseline comparison for trend tracking across runs
- Interactive HTML reports with sortable tables
- `.complexityrc` configuration for project-wide threshold defaults
- Duplicate-function detection across files as a maintainability signal
