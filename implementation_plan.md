# Codebase Complexity Analyzer - Implementation Plan

This document outlines the detailed, step-by-step implementation plan for the Codebase Complexity Analyzer with PDF Reporting, based on the approved PRD. As per the extended requirements, this plan encompasses 13 development phases and introduces both an embedded database for historical tracking and comprehensive session logging.

## Core Architectural Additions
- **Database**: SQLite3 will be embedded to store historical metric runs (timestamps, target folders, scores). This allows for future trend analysis.
- **Log File**: Python's built-in `logging` module will be used to maintain a persistent `analyzer_session.log` capturing every execution run, errors, and debug traces.

---

## Phase 1: Project Initialization & Scaffold Setup
- Initialize the target directory with the file hierarchy (`project.py`, `test_project.py`, `requirements.txt`, `README.md`).
- Define the module-level constants, specifically `SCORING_CONFIG` and `DEFAULT_THRESHOLDS`.
- Setup a blank `main()` entrypoint wrapped in the standard `if __name__ == "__main__":` block.
- Install necessary dependencies (`pip install fpdf2 pytest`).

## Phase 2: Session Logging Architecture
- Implement a standard Python `logging` configuration inside `project.py`.
- Configure a FileHandler to append logs to `analyzer_session.log` (format: `[TIMESTAMP] [LEVEL] MESSAGE`).
- Configure a stream handler appropriately, ensuring error traces flow into the file without muddying the CLI report.
- Instrument foundational start and stop log events inside `main()`.

## Phase 3: Database Integration for Run History
- Introduce an SQLite3 layer (utilizing the built-in `sqlite3` library) to initialize a local database (`metrics_history.db`) automatically upon the first run.
- Create a `runs_history` table with the schema: `run_id` (PRIMARY KEY), `run_timestamp`, `target_folder`, `total_files`, `overall_score`, `total_parse_errors`, and `total_warnings`.
- Write modular helper functions, e.g., `init_db()` and `record_run(summary)`, to insert records post-analysis safely.

## Phase 4: CLI Parsing & Input Validation
- Implement `argparse` configuration within `main()`.
- Define positional arguments (target folder) and optional flags (`--output`, `--verbose`, `--json`, `--max-func-len`, `--max-depth`, `--no-recurse`).
- Apply rigid error handling to ensure the target folder exists and is non-empty, logging any rapid application exits.

## Phase 5: Directory Scanner & File Discovery 
- Implement `get_python_files(folder, recursive=True)`.
- Use `os.walk` to traverse directories, capturing `.py` files securely.
- Apply filtering to ignore unreadable paths, utilizing the logging engine to record warnings for OS permission faults.
- Write initial `pytest` cases for `get_python_files` covering basic, recursive, and edge-case execution.

## Phase 6: Core Parsing & Source Reading
- Implement the `count_lines_of_code(filepath)` function to properly bypass blank lines and comment-only lines.
- Add robust try/except safeguards for reading file descriptors, dropping down gracefully to `latin-1` encodings upon `UnicodeDecodeError`.
- Read file metrics like `file_size` via `os.path.getsize()`.
- Incorporate base AST parsing: Wrap `ast.parse` evaluations safely. Failures log appropriately and insert the prerequisite static 75-point penalty syntax error record.

## Phase 7: AST Metric Extraction Engine
- Implement `analyze_ast(tree)` using `ast.walk` interspersed with recursive node visitation.
- Isolate and calculate node tallies: `num_functions`, `num_classes`, body line spans, and pinpoint sizes defining `max_func_len`.
- Craft complex loop traversal mechanics to deduce `loop_nesting_depth` (using instances of `ast.For`, `ast.While`, `ast.AsyncFor`).
- Finalize robust unit tests validating pure lines-of-code computations.

## Phase 8: Warning Detection & Custom Thresholds
- Implement `detect_warnings(metrics, thresholds)`.
- Apply conditionals defined explicitly within the PRD checking metrics against upper thresholds (`max_function_length`, `file_size`).
- Assemble output arrays showcasing categorized dictionaries emphasizing ID, Message, and Severity scales (LOW/MEDIUM/HIGH).
- Log instances systematically whenever files provoke `HIGH` severity infractions.

## Phase 9: Complexity Scoring System
- Implement `calculate_complexity_score(metrics)` evaluating metrics through the predefined additive penalty logic formula.
- Synthesize sub-scores analyzing function depth, line count, and function counts proportionally.
- Hard clamp the formulated overall score tightly bridging boundaries of `0` to `100`.
- Compose specific `pytest` verifications guaranteeing accuracy corresponding exactly to metric inputs.

## Phase 10: Aggregation & SQLite Action Invocation
- Construct `summarize_results(results)` aggregating metrics extracted successfully across all scanned modules.
- Deduce universal tallies: averages, errors, and an unweighted arithmetic median.
- Connect outputs seamlessly to execute `record_run(summary)` from Phase 3, securely inserting the summary trace cleanly into `metrics_history.db`.

## Phase 11: Terminal Interface Construction and JSON Implementation
- Construct `generate_terminal_report(results, summary)`.
- Program meticulously structured console reporting displaying summary data alongside visually colored ANSI severity indicator displays.
- Deploy the functional execution bound by the `--json` flag producing raw dictionary exports output into `results.json`.

## Phase 12: PDF Document Delivery Engine
- Deploy `generate_pdf_report(results, summary, output_path)` relying centrally on the `fpdf2` library framework.
- Designate formatting constraints rigidly replicating PRD dictates (Section 12 Layout): distinct Title Page formatting, File-By-File detailed paginations, consolidated Warning Summaries, and Data charts.
- Utilize automatic FPDF pagination boundaries correctly routing data rendering overflows safely onto new document pages.

## Phase 13: Full Regression Validations & CS50P Compliance Packaging
- Culminate remaining validation protocols within `test_project.py` securing over 90% logic test coverage.
- Prepare `README.md` fulfilling stringent CS50P requirements addressing description elements, features, and narrative architecture constraints reliably.
- Execute live memory stress runs (scaling scans to 50+ files to guarantee peak memories remain comfortably beneath upper scale limits ~200MB).
- Review historical data traces validating clean DB inserts internally logging to verify session consistencies prior to deployment lock.
