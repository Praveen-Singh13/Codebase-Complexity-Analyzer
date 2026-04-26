
from __future__ import annotations

import argparse
import ast
import os
import sys
from typing import Any


SCORING_CONFIG: dict[str, Any] = {
    "max_func_len_threshold": 50,
    "nesting_depth_threshold": 3,
    "loc_threshold": 300,
    "num_functions_threshold": 20,
    "avg_func_len_threshold": 30,
}

DEFAULT_THRESHOLDS: dict[str, int] = {
    "max_func_len": 50,
    "max_depth": 3,
    "loc": 500,
    "num_functions": 20,
    "file_size": 51200,
    "avg_func_len": 30,
}


def get_python_files(folder: str, recursive: bool = True) -> list[str]:
    """Return Python file paths from a folder."""
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    python_files: list[str] = []

    if recursive:
        def _handle_walk_error(error: OSError) -> None:
            if isinstance(error, PermissionError):
                print(f"Warning: skipping unreadable directory: {error.filename}")

        for root, _, files in os.walk(folder, onerror=_handle_walk_error):
            for filename in files:
                if filename.endswith(".py"):
                    python_files.append(os.path.abspath(os.path.join(root, filename)))
    else:
        for filename in os.listdir(folder):
            if filename.endswith(".py"):
                python_files.append(os.path.abspath(os.path.join(folder, filename)))

    return sorted(python_files)


def count_lines_of_code(filepath: str) -> int:
    """Count non-blank, non-comment lines in a file."""
    def _count_from_lines(lines: list[str]) -> int:
        loc = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if line.lstrip().startswith("#"):
                continue
            loc += 1
        return loc

    try:
        with open(filepath, "r", encoding="utf-8") as source_file:
            return _count_from_lines(source_file.readlines())
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as source_file:
            return _count_from_lines(source_file.readlines())


def analyze_ast(tree: ast.Module) -> dict[str, Any]:
    """Extract AST-based complexity metrics from a parsed module."""
    zero_metrics = {
        "num_functions": 0,
        "num_classes": 0,
        "func_lengths": [],
        "avg_func_len": 0.0,
        "max_func_len": 0,
        "nesting_depth": 0,
        "num_loops": 0,
    }

    if tree is None or not isinstance(tree, ast.AST):
        return zero_metrics

    function_nodes = (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    class_nodes = (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    loop_types = (ast.For, ast.While, ast.AsyncFor)
    loop_nodes = [node for node in ast.walk(tree) if isinstance(node, loop_types)]

    func_lengths: list[int] = []
    for node in function_nodes:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            func_lengths.append(0)
            continue
        func_lengths.append(max(0, end_lineno - lineno + 1))

    def _max_loop_nesting_depth(node: ast.AST, current_depth: int = 0) -> int:
        is_loop = isinstance(node, loop_types)
        depth = current_depth + 1 if is_loop else current_depth
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            child_depth = _max_loop_nesting_depth(child, depth)
            if child_depth > max_depth:
                max_depth = child_depth
        return max_depth

    num_functions = len(func_lengths)
    num_classes = sum(1 for _ in class_nodes)
    avg_func_len = round(sum(func_lengths) / num_functions, 2) if num_functions else 0.0
    max_func_len = max(func_lengths) if func_lengths else 0
    nesting_depth = _max_loop_nesting_depth(tree, 0)
    num_loops = len(loop_nodes)

    return {
        "num_functions": num_functions,
        "num_classes": num_classes,
        "func_lengths": func_lengths,
        "avg_func_len": avg_func_len,
        "max_func_len": max_func_len,
        "nesting_depth": nesting_depth,
        "num_loops": num_loops,
    }


def detect_warnings(
    metrics: dict[str, Any], thresholds: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Generate warning objects based on computed metrics."""
    active_thresholds = DEFAULT_THRESHOLDS if thresholds is None else thresholds

    for name, value in active_thresholds.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"Threshold '{name}' must be numeric.")

    warning_rules = [
        ("W-01", "max_func_len", "MEDIUM", active_thresholds["max_func_len"], "Maximum function length exceeded threshold."),
        ("W-02", "nesting_depth", "HIGH", active_thresholds["max_depth"], "Loop nesting depth exceeded threshold."),
        ("W-03", "loc", "MEDIUM", active_thresholds["loc"], "Lines of code exceeded threshold."),
        ("W-04", "num_functions", "LOW", active_thresholds["num_functions"], "Number of functions exceeded threshold."),
        ("W-05", "file_size", "LOW", active_thresholds["file_size"], "File size exceeded threshold."),
        ("W-06", "avg_func_len", "LOW", active_thresholds["avg_func_len"], "Average function length exceeded threshold."),
    ]

    warnings: list[dict[str, Any]] = []
    for warning_id, metric_name, severity, threshold_value, message in warning_rules:
        if metric_name not in metrics:
            warnings.append(
                {
                    "id": "W-MISSING",
                    "message": f"Missing metric: {metric_name}",
                    "severity": "LOW",
                    "metric": metric_name,
                }
            )
            continue

        metric_value = metrics[metric_name]
        if isinstance(metric_value, (int, float)) and metric_value > threshold_value:
            warnings.append(
                {
                    "id": warning_id,
                    "message": message,
                    "severity": severity,
                    "metric": metric_name,
                }
            )

    return warnings


def calculate_complexity_score(metrics: dict[str, Any]) -> float:
    """Compute a complexity score in the range [0, 100]."""
    max_func_len = metrics.get("max_func_len", 0)
    nesting_depth = metrics.get("nesting_depth", 0)
    loc = metrics.get("loc", 0)
    num_functions = metrics.get("num_functions", 0)
    avg_func_len = metrics.get("avg_func_len", 0)

    score = 0.0

    if max_func_len > 50:
        score += min(30, (max_func_len - 50) * 0.5)

    if nesting_depth > 3:
        score += min(25, (nesting_depth - 3) * 8)

    if loc > 300:
        score += min(20, (loc - 300) * 0.05)

    if num_functions > 20:
        score += min(15, (num_functions - 20) * 1.0)

    if avg_func_len > 30:
        score += min(10, (avg_func_len - 30) * 0.4)

    return float(min(100, round(score, 2)))


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-file results into a summary."""
    raise NotImplementedError("Implemented in later phases.")


def generate_terminal_report(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Print a terminal-formatted analysis report."""
    raise NotImplementedError("Implemented in later phases.")


def generate_pdf_report(
    results: list[dict[str, Any]], summary: dict[str, Any], output_path: str
) -> None:
    """Generate a PDF report using fpdf2."""
    raise NotImplementedError("Implemented in later phases.")


def main() -> None:
    """CLI entry point for argument parsing and orchestration."""
    parser = argparse.ArgumentParser(
        description="Analyze Python codebase complexity and generate reports."
    )
    parser.add_argument("folder", help="Target folder path containing Python files")
    parser.add_argument(
        "-o", "--output", default="complexity_report.pdf", help="Output PDF filename"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument("-j", "--json", action="store_true", help="Export JSON results")
    parser.add_argument(
        "--max-func-len",
        type=int,
        default=50,
        help="Override max function length warning threshold",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Override loop nesting depth warning threshold",
    )
    parser.add_argument(
        "--no-recurse",
        action="store_true",
        help="Disable recursive directory scanning",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print("Error: folder not found")
        sys.exit(1)

    runtime_thresholds = DEFAULT_THRESHOLDS.copy()
    runtime_thresholds["max_func_len"] = args.max_func_len
    runtime_thresholds["max_depth"] = args.max_depth
    _ = runtime_thresholds

    try:
        python_files = get_python_files(args.folder, recursive=not args.no_recurse)
    except FileNotFoundError:
        print("Error: folder not found")
        sys.exit(1)

    if not python_files:
        print(f"Error: no Python files found in {args.folder}")
        sys.exit(1)


if __name__ == "__main__":
    main()
