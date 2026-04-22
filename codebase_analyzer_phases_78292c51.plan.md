---
name: Codebase Analyzer Phases
overview: Implement the PRD-defined Codebase Complexity Analyzer from a currently empty code workspace, in strict phased increments that map directly to required functionality, testing, reporting, and CS50P compliance artifacts.
todos:
  - id: phase-1-skeleton
    content: Create required files/folders and scaffold all mandatory top-level functions and constants.
    status: in_progress
  - id: phase-2-to-6-core-pipeline
    content: Implement CLI validation, file discovery, LOC counting, AST metrics, warnings/scoring, parse-safe per-file loop, and summary aggregation.
    status: pending
  - id: phase-7-8-reporting
    content: Implement full terminal and PDF reporting per PRD layout/format contracts.
    status: pending
  - id: phase-9-10-flags-tests
    content: Complete optional PRD flags and implement required pytest suite with scenario coverage.
    status: pending
  - id: phase-11-docs-compliance
    content: Write final README and run PRD/CS50P compliance audit checklist before handoff.
    status: pending
isProject: false
---

# Codebase Complexity Analyzer Implementation Plan

## Current State Assessment
- Repository currently contains planning artifacts only: [prd_content.txt](prd_content.txt), [Codebase_Complexity_Analyzer_PRD.docx](Codebase_Complexity_Analyzer_PRD.docx), and extracted document XML under [temp_docx/](temp_docx).
- Required deliverables from PRD do not yet exist: [project.py](project.py), [test_project.py](test_project.py), [requirements.txt](requirements.txt), [README.md](README.md), and [sample_code/](sample_code/).
- Implementation should therefore be treated as a **greenfield build** constrained strictly by PRD sections §5, §9, §10, §11, §12, §13, §14, §21.

## Execution Rules (Apply In Every Phase)
- Implement only behaviors explicitly required by PRD; do not add extra features.
- Keep architecture function-based in [project.py](project.py); no class-based app architecture.
- Keep all scoring/warning thresholds and weights centralized in module constants (`SCORING_CONFIG`, warning thresholds).
- Keep core calculation functions pure and deterministic where PRD requires purity.
- Every new behavior must be covered by either unit tests or manual acceptance checks listed in each phase.
- Maintain cross-platform compatibility (Windows/macOS/Linux) with standard library + `fpdf2` only.

## Phase 1 — Project Skeleton and Dependency Baseline

### Objective
Create the mandatory file/folder structure exactly as defined in PRD §9 so later phases can implement functionality without structural ambiguity.

### Files To Create
- [project.py](project.py)
- [test_project.py](test_project.py)
- [requirements.txt](requirements.txt)
- [README.md](README.md)
- [sample_code/clean.py](sample_code/clean.py)
- [sample_code/complex.py](sample_code/complex.py)
- [sample_code/empty.py](sample_code/empty.py)
- [sample_code/broken.py](sample_code/broken.py)

### Detailed Tasks
- Initialize [requirements.txt](requirements.txt) with only:
  - `fpdf2>=2.7.4`
  - `pytest>=7.0.0`
- Scaffold [project.py](project.py):
  - Add module docstring describing CLI purpose.
  - Add all required top-level function stubs from PRD §10:
    - `main`
    - `get_python_files`
    - `count_lines_of_code`
    - `analyze_ast`
    - `detect_warnings`
    - `calculate_complexity_score`
    - `generate_terminal_report`
    - `generate_pdf_report`
    - `summarize_results`
  - Add `if __name__ == '__main__': main()` entrypoint.
  - Add placeholder constants for `SCORING_CONFIG` and default warning thresholds.
- Scaffold [test_project.py](test_project.py):
  - Add imports for `pytest` and functions under test.
  - Add placeholder test functions matching PRD naming convention.
- Create [sample_code/](sample_code/) fixtures:
  - `clean.py`: simple valid small script.
  - `complex.py`: intentionally nested loops and multiple functions.
  - `empty.py`: empty file.
  - `broken.py`: intentional syntax error file.

### Exit Criteria
- All required files/folders exist.
- `python project.py --help` runs (may still show incomplete behavior but argparse stub should execute).

---

## Phase 2 — CLI Contract and Input Validation

### Objective
Implement argument parsing and fatal error handling exactly as required in FR-1 and §10 `main()` contract.

### Detailed Tasks
- In [project.py](project.py), implement argparse parser with exact flags:
  - positional `folder`
  - `--output/-o` default `complexity_report.pdf`
  - `--verbose/-v` boolean
  - `--json/-j` boolean
  - `--max-func-len` int default `50`
  - `--max-depth` int default `3`
  - `--no-recurse` boolean
- Implement startup validation in `main()`:
  - folder exists -> else print `Error: folder not found` and `sys.exit(1)`.
  - call `get_python_files` with recursion controlled by `--no-recurse`.
  - if no `.py` files discovered -> print `Error: no Python files found in <folder>` and exit 1.
- Initialize runtime thresholds from CLI overrides while preserving default constants.

### Acceptance Checks
- Running without folder arg should produce argparse usage exit code 2.
- Nonexistent folder returns required error + code 1.
- Existing folder with no `.py` files returns required error + code 1.

---

## Phase 3 — File Discovery and LOC Metric

### Objective
Implement deterministic Python file discovery and robust LOC counting behavior from FR-1 + PRD specs for `get_python_files` and `count_lines_of_code`.

### Detailed Tasks
- Implement `get_python_files(folder, recursive=True)`:
  - Raise `FileNotFoundError` for missing folder.
  - Recursive mode: `os.walk`, collect `.py` files only.
  - Non-recursive mode: `os.listdir`, top-level `.py` only.
  - Convert every result to absolute path via `os.path.abspath`.
  - Sort lexicographically for deterministic output.
  - Handle subtree `PermissionError` gracefully (skip + warning output).
- Implement `count_lines_of_code(filepath)`:
  - Read UTF-8 first.
  - On `UnicodeDecodeError`, retry latin-1.
  - Count only non-blank, non-comment lines where first non-whitespace char is not `#`.
  - Count inline-comment code lines as code.

### Acceptance Checks
- Test scenarios for empty folder, recursive scan, no recursion, nonexistent path.
- LOC scenarios: empty file, comments only, mixed, inline comments.

---

## Phase 4 — AST Metric Extraction Engine

### Objective
Implement FR-3 metric extraction (M-02..M-09 except LOC/file_size integration done in orchestration).

### Detailed Tasks
- In `analyze_ast(tree)` implement extraction of:
  - `num_functions` (`FunctionDef` + `AsyncFunctionDef`)
  - `num_classes` (`ClassDef`)
  - `func_lengths` via `end_lineno - lineno + 1`
  - `avg_func_len`, `max_func_len`
  - `num_loops` (`For`, `While`, `AsyncFor`)
  - `nesting_depth` maximum for loop nesting via recursive depth traversal
- Add zero-value safe return if tree is `None` or invalid AST instance.
- Handle missing `lineno/end_lineno` by recording function length `0` while still counting function.

### Acceptance Checks
- Manual AST fixture checks against crafted code in [sample_code/complex.py](sample_code/complex.py).
- Verify zero-value dict behavior on invalid input.

---

## Phase 5 — Warning Engine and Complexity Scoring

### Objective
Implement FR-4 and FR-5 exactly (IDs, thresholds, severities, formulas, clamping).

### Detailed Tasks
- Implement module default threshold mapping for warnings W-01..W-06.
- Implement `detect_warnings(metrics, thresholds=None)`:
  - Evaluate each PRD condition.
  - Emit list of dicts with keys: `id`, `message`, `severity`.
  - Handle missing metric keys by skipping that check and appending LOW warning `Missing metric: <key>`.
  - Validate numeric thresholds; raise `ValueError` if invalid.
- Implement `calculate_complexity_score(metrics)` using PRD additive penalties:
  - max function length penalty cap 30
  - nesting penalty cap 25
  - LOC penalty cap 20
  - function-count penalty cap 15
  - avg-length penalty cap 10
  - final clamp to `100` and round to 2 decimals
- Ensure missing keys are treated as no penalty contributions.

### Acceptance Checks
- Unit tests for zero score, single-dimension penalties, deep nesting=24.0 case, and clamp-to-100 case.

---

## Phase 6 — Per-File Analysis Loop and Summary Aggregation

### Objective
Build end-to-end per-file processing with parse error resilience and aggregate summaries per FR-2 and FR-8.

### Detailed Tasks
- In `main()` per file:
  - Compute LOC.
  - Parse source with `ast.parse` wrapped for `SyntaxError` and `UnicodeDecodeError`.
  - For parse errors:
    - set `parse_error=True`
    - include warning note (W-00 handling per PRD §13)
    - continue processing next file without crashing.
  - For successful parse:
    - run `analyze_ast`
    - compute file size via `os.path.getsize`
    - run `detect_warnings`
    - run `calculate_complexity_score`
  - Build standardized `file_result` dict for all downstream reporters.
- Implement `summarize_results(results)`:
  - Return full summary schema from PRD §10.
  - Include parse-error contribution rule: score 75 for parse_error files.
  - Compute warning distribution LOW/MEDIUM/HIGH.
  - Handle empty result list with zero-value summary.

### Acceptance Checks
- Mixed run over [sample_code/](sample_code/) should include one parse error record and valid overall score.

---

## Phase 7 — Terminal Report Rendering

### Objective
Implement FR-6 terminal report formatting with metrics, warnings, score bar, and summary.

### Detailed Tasks
- Implement `generate_terminal_report(results, summary)` to print:
  - Header banner with tool name, target folder, date/time, file count.
  - Per-file section:
    - relative path
    - all metric outputs M-01 to M-09
    - warning list with severities
    - colored ASCII complexity bar:
      - green <= 30
      - yellow 31–60
      - red > 60
  - Final summary section with:
    - total files analyzed
    - parse error count
    - warning counts by severity
    - average LOC
    - average function length
    - overall complexity score
- Add TTY detection and disable ANSI codes when stdout is not a terminal.
- Handle missing result keys by showing `[N/A]` instead of raising.

### Acceptance Checks
- Visual inspection in terminal and redirected output mode (`> report.txt`) to verify ANSI suppression.

---

## Phase 8 — PDF Report Generation (fpdf2)

### Objective
Implement FR-7 and full §12 layout contract without text clipping and with automatic pagination.

### Detailed Tasks
- Implement `generate_pdf_report(results, summary, output_path)` with guards:
  - path must end in `.pdf` else `ValueError`.
  - output directory must exist else `FileNotFoundError`.
- Configure FPDF document:
  - A4 portrait
  - 15mm margins
  - auto-page-break enabled with 15mm bottom margin
  - metadata title/author/creator
  - footer page numbers `Page N of M` (via FPDF subclass `footer` override)
- Render sections in required order:
  1. Title page (exact required labels and visual hierarchy)
  2. Per-file analysis blocks with shaded headers and metric table
  3. Warning summary section grouped by file, severity badges using `rect`
  4. Final summary table + per-file score bar chart via `rect`
- Ensure long text wraps safely (use `multi_cell` where needed).
- On internal fpdf errors, wrap and raise `RuntimeError` with original message context.
- On success print `PDF saved to <output_path>`.

### Acceptance Checks
- Generate PDF on fixture data and manually verify no clipping/overflow.
- Validate multi-page behavior using expanded fixture set.

---

## Phase 9 — Optional Flags Integration (PRD-Allowed Only)

### Objective
Complete FR-9 optional features required by PRD scope (JSON export, threshold overrides already wired, verbose details, output naming, recursion toggle).

### Detailed Tasks
- Implement `--json/-j` behavior:
  - write results payload to default `results.json`.
  - if PRD interpretation includes configurable JSON path (`--output-json`), either:
    - implement it explicitly, or
    - document omission as out-of-contract if strict CLI list is followed (resolve consistently in README).
- Implement `--verbose/-v` output of AST node counts and raw token-like debug details per file (without breaking normal report readability).
- Ensure `--output/-o` fully controls PDF destination.
- Confirm `--no-recurse` toggles scanner mode correctly.

### Acceptance Checks
- Run matrix of CLI combinations to ensure flags compose correctly (e.g., `--verbose --json --no-recurse`).

---

## Phase 10 — Test Suite Completion and Quality Gate

### Objective
Implement full pytest suite required by §11 and verify core function reliability.

### Detailed Tasks
- In [test_project.py](test_project.py), implement all required test groups:
  - `get_python_files` (>=3 scenarios; target 5 from PRD examples)
  - `count_lines_of_code` (>=4 scenarios; include inline comments)
  - `calculate_complexity_score` (>=4 scenarios; include clamp and deep nesting)
- Use temporary files/directories (`tempfile`) for isolation; no real project data dependency.
- Ensure naming pattern `test_{function_name}_{scenario}`.
- Add assertions for deterministic ordering and expected numeric outputs.

### Acceptance Checks
- `pytest test_project.py -v` passes fully.
- Coverage on required testable functions meets target intent (>=90% per PRD objective).

---

## Phase 11 — Documentation and Submission Readiness

### Objective
Finish mandatory documentation and verify CS50P compliance matrix alignment.

### Detailed Tasks
- Write [README.md](README.md) to 500–700 words with exact required sections and order from §14.
- Document installation, usage examples, CLI flags, design decisions, future improvements.
- Confirm [requirements.txt](requirements.txt) remains minimal and accurate.
- Validate sample fixtures in [sample_code/](sample_code/) match their intended edge-case roles.
- Run final compliance checklist against PRD §21 mapping.

### Final Acceptance Checklist
- All required files from PRD §9 exist and are complete.
- CLI works end-to-end on sample fixtures.
- Terminal report + PDF report generated from one run.
- Parse errors handled gracefully; no crashes.
- Tests pass.
- No behavior added beyond PRD-defined scope.

## Recommended Implementation Order Inside `project.py`
- Constants and imports
- `get_python_files`
- `count_lines_of_code`
- `analyze_ast`
- `detect_warnings`
- `calculate_complexity_score`
- `summarize_results`
- `generate_terminal_report`
- `generate_pdf_report`
- `main`

This ordering reduces forward-reference issues and allows incremental testing after each phase.