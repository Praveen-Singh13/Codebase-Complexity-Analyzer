from __future__ import annotations

import argparse
import ast
from datetime import datetime
import getpass
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
    if not results:
        return {
            "total_files": 0,
            "parse_errors": 0,
            "total_functions": 0,
            "total_classes": 0,
            "avg_loc": 0.0,
            "avg_func_len": 0.0,
            "overall_score": 0.0,
            "warnings_by_severity": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
        }

    total_files = len(results)
    parse_errors = 0
    total_functions = 0
    total_classes = 0
    total_loc = 0
    score_values: list[float] = []
    all_function_lengths: list[int] = []
    warnings_by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}

    for result in results:
        parse_error = bool(result.get("parse_error", False))
        if parse_error:
            parse_errors += 1
            score_values.append(75.0)
        else:
            score_values.append(float(result.get("score", 0.0)))
            total_loc += int(result.get("loc", 0))
            total_functions += int(result.get("num_functions", 0))
            total_classes += int(result.get("num_classes", 0))
            function_lengths = result.get("func_lengths", [])
            if isinstance(function_lengths, list):
                all_function_lengths.extend(
                    length for length in function_lengths if isinstance(length, int)
                )

        warnings = result.get("warnings", [])
        if isinstance(warnings, list):
            for warning in warnings:
                severity = warning.get("severity")
                if severity in warnings_by_severity:
                    warnings_by_severity[severity] += 1

    avg_loc = round(total_loc / total_files, 2) if total_files else 0.0
    avg_func_len = (
        round(sum(all_function_lengths) / len(all_function_lengths), 2)
        if all_function_lengths
        else 0.0
    )
    overall_score = round(sum(score_values) / total_files, 2) if total_files else 0.0

    return {
        "total_files": total_files,
        "parse_errors": parse_errors,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "avg_loc": avg_loc,
        "avg_func_len": avg_func_len,
        "overall_score": overall_score,
        "warnings_by_severity": warnings_by_severity,
    }


def generate_terminal_report(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Print a terminal-formatted analysis report."""
    if not results:
        print("No files analysed.")
        return

    use_ansi = sys.stdout.isatty()
    colors = {
        "RESET": "\033[0m" if use_ansi else "",
        "GREEN": "\033[32m" if use_ansi else "",
        "YELLOW": "\033[33m" if use_ansi else "",
        "RED": "\033[31m" if use_ansi else "",
        "GRAY": "\033[90m" if use_ansi else "",
    }

    def _fmt_warning_severity(severity: str) -> str:
        if severity == "HIGH":
            return f"{colors['RED']}{severity}{colors['RESET']}"
        if severity == "MEDIUM":
            return f"{colors['YELLOW']}{severity}{colors['RESET']}"
        return f"{colors['GRAY']}{severity}{colors['RESET']}"

    def _score_bar(score: float, width: int = 20) -> str:
        clamped = max(0.0, min(100.0, score))
        filled = int(round((clamped / 100.0) * width))
        bar = f"[{'#' * filled}{'-' * (width - filled)}]"
        if score <= 30:
            color = colors["GREEN"]
        elif score <= 60:
            color = colors["YELLOW"]
        else:
            color = colors["RED"]
        return f"{color}{bar}{colors['RESET']}"

    target_folder = summary.get("target_folder", "[N/A]")
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 72)
    print("Codebase Complexity Analyzer")
    print(f"Target Folder: {target_folder}")
    print(f"Generated At : {now_text}")
    print(f"Total Files  : {len(results)}")
    print("=" * 72)

    for result in results:
        filepath = result.get("filepath", "[N/A]")
        print(f"\nFile: {filepath}")
        print("-" * 72)
        print(f"M-01 LOC                 : {result.get('loc', '[N/A]')}")
        print(f"M-02 Number of Functions : {result.get('num_functions', '[N/A]')}")
        print(f"M-03 Number of Classes   : {result.get('num_classes', '[N/A]')}")
        print(f"M-04 Function Lengths    : {result.get('func_lengths', '[N/A]')}")
        print(f"M-05 Avg Function Length : {result.get('avg_func_len', '[N/A]')}")
        print(f"M-06 Max Function Length : {result.get('max_func_len', '[N/A]')}")
        print(f"M-07 Loop Nesting Depth  : {result.get('nesting_depth', '[N/A]')}")
        print(f"M-08 Number of Loops     : {result.get('num_loops', '[N/A]')}")
        print(f"M-09 File Size (bytes)   : {result.get('file_size', '[N/A]')}")

        warnings = result.get("warnings", [])
        print("Warnings:")
        if isinstance(warnings, list) and warnings:
            for warning in warnings:
                warning_id = warning.get("id", "[N/A]")
                severity = warning.get("severity", "LOW")
                message = warning.get("message", "[N/A]")
                print(f"  - [{warning_id}] {_fmt_warning_severity(severity)}: {message}")
        else:
            print("  - None")

        score_value = float(result.get("score", 0.0))
        print(f"Complexity Score: {score_value}/100 {_score_bar(score_value)}")

    warn_summary = summary.get("warnings_by_severity", {})
    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"Total Files Analysed     : {summary.get('total_files', '[N/A]')}")
    print(f"Total Parse Errors       : {summary.get('parse_errors', '[N/A]')}")
    print(f"Warnings LOW             : {warn_summary.get('LOW', '[N/A]')}")
    print(f"Warnings MEDIUM          : {warn_summary.get('MEDIUM', '[N/A]')}")
    print(f"Warnings HIGH            : {warn_summary.get('HIGH', '[N/A]')}")
    print(f"Average LOC              : {summary.get('avg_loc', '[N/A]')}")
    print(f"Average Function Length  : {summary.get('avg_func_len', '[N/A]')}")
    print(f"Overall Complexity Score : {summary.get('overall_score', '[N/A]')}/100")


def generate_pdf_report(
    results: list[dict[str, Any]], summary: dict[str, Any], output_path: str
) -> None:
    """Generate a PDF report using fpdf2."""
    if not output_path.lower().endswith(".pdf"):
        raise ValueError("Output path must end in .pdf")

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.isdir(output_dir):
        raise FileNotFoundError(f"Output directory not found: {output_dir}")

    try:
        from fpdf import FPDF
    except ImportError as error:
        raise ImportError("Install fpdf2: pip install fpdf2") from error

    class ReportPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-10)
            self.set_font("Helvetica", size=8)
            self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")

    try:
        pdf = ReportPDF(orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(15, 15, 15)
        pdf.set_title("Codebase Complexity Analyzer Report")
        pdf.set_author(getpass.getuser())
        pdf.set_creator("Codebase Complexity Analyzer")

        # Title page
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=24)
        pdf.set_y(60)
        pdf.cell(0, 12, "Codebase Complexity Analyzer", align="C", ln=True)
        pdf.set_font("Helvetica", size=14)
        pdf.cell(0, 8, "Python Codebase Analysis Report", align="C", ln=True)
        pdf.line(15, 100, 195, 100)

        pdf.set_y(110)
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 7, f"Analysed by: {getpass.getuser()}", ln=True)
        pdf.cell(0, 7, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.cell(0, 7, f"Target: {summary.get('target_folder', '[N/A]')}", ln=True)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 7, f"Files Found: {summary.get('total_files', 0)}", ln=True)

        overall_score = float(summary.get("overall_score", 0.0))
        if overall_score <= 30:
            pdf.set_text_color(0, 128, 0)
        elif overall_score <= 60:
            pdf.set_text_color(204, 136, 0)
        else:
            pdf.set_text_color(204, 0, 0)
        pdf.ln(6)
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(0, 10, f"Overall Complexity Score: {overall_score}/100", align="C", ln=True)
        pdf.set_text_color(0, 0, 0)

        # Analysis section
        pdf.add_page()
        for result in results:
            if pdf.get_y() > 245:
                pdf.add_page()

            filename = os.path.basename(str(result.get("filepath", "[N/A]")))
            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, filename, ln=True, fill=True)

            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            table_rows = [
                ("M-01 LOC", result.get("loc", "[N/A]")),
                ("M-02 Num Functions", result.get("num_functions", "[N/A]")),
                ("M-03 Num Classes", result.get("num_classes", "[N/A]")),
                ("M-04 Function Lengths", str(result.get("func_lengths", "[N/A]"))),
                ("M-05 Avg Function Length", result.get("avg_func_len", "[N/A]")),
                ("M-06 Max Function Length", result.get("max_func_len", "[N/A]")),
                ("M-07 Loop Nesting Depth", result.get("nesting_depth", "[N/A]")),
                ("M-08 Number of Loops", result.get("num_loops", "[N/A]")),
                ("M-09 File Size (bytes)", result.get("file_size", "[N/A]")),
            ]
            for key, value in table_rows:
                pdf.set_font("Helvetica", size=10)
                pdf.cell(65, 6, str(key), border=1)
                pdf.set_font("Helvetica", style="B", size=10)
                pdf.cell(0, 6, str(value), border=1, ln=True)

            pdf.ln(1)
            warnings = result.get("warnings", [])
            if isinstance(warnings, list) and warnings:
                for warning in warnings:
                    severity = str(warning.get("severity", "LOW"))
                    if severity == "HIGH":
                        pdf.set_text_color(220, 20, 60)
                    elif severity == "MEDIUM":
                        pdf.set_text_color(255, 140, 0)
                    else:
                        pdf.set_text_color(128, 128, 128)
                    pdf.set_font("Helvetica", size=9)
                    prefix = f"[{severity}] "
                    message = str(warning.get("message", "Warning"))
                    pdf.multi_cell(0, 5, prefix + message)
                    pdf.set_text_color(0, 0, 0)
            else:
                pdf.set_font("Helvetica", size=9)
                pdf.cell(0, 5, "No warnings", ln=True)
            pdf.ln(4)

        # Warnings summary section
        if pdf.get_y() > 148:
            pdf.add_page()
        else:
            pdf.ln(4)
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.cell(0, 8, "Warning Summary", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)

        for result in results:
            warnings = result.get("warnings", [])
            if not isinstance(warnings, list) or not warnings:
                continue
            if pdf.get_y() > 250:
                pdf.add_page()
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(0, 6, os.path.basename(str(result.get("filepath", "[N/A]"))), ln=True)
            for warning in warnings:
                if pdf.get_y() > 250:
                    pdf.add_page()
                severity = str(warning.get("severity", "LOW"))
                if severity == "HIGH":
                    pdf.set_fill_color(220, 20, 60)
                elif severity == "MEDIUM":
                    pdf.set_fill_color(255, 140, 0)
                else:
                    pdf.set_fill_color(150, 150, 150)
                y = pdf.get_y()
                pdf.rect(15, y + 1.5, 4, 4, style="F")
                pdf.set_x(21)
                warning_id = str(warning.get("id", "W-XX"))
                message = str(warning.get("message", "Warning"))
                pdf.set_font("Helvetica", size=9)
                pdf.multi_cell(0, 5, f"{warning_id} [{severity}] {message}")

        # Final summary section
        pdf.add_page()
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.cell(0, 8, "Summary", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)

        summary_rows = [
            ("Total Files", summary.get("total_files", 0)),
            ("Parse Errors", summary.get("parse_errors", 0)),
            ("Total Functions", summary.get("total_functions", 0)),
            ("Total Classes", summary.get("total_classes", 0)),
            ("Average LOC", summary.get("avg_loc", 0.0)),
            ("Average Function Length", summary.get("avg_func_len", 0.0)),
            ("Overall Complexity Score", f"{summary.get('overall_score', 0.0)}/100"),
        ]
        for label, value in summary_rows:
            pdf.set_font("Helvetica", size=10)
            pdf.cell(75, 7, str(label), border=1)
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.cell(0, 7, str(value), border=1, ln=True)

        pdf.ln(6)
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 7, "Per-file Score Distribution", ln=True)
        chart_x = 15
        chart_y = pdf.get_y() + 4
        chart_width = 180
        chart_height = 50
        pdf.rect(chart_x, chart_y, chart_width, chart_height)
        bar_count = max(1, len(results))
        bar_spacing = chart_width / bar_count

        for idx, result in enumerate(results):
            score = float(result.get("score", 0.0))
            bar_height = (score / 100.0) * (chart_height - 4)
            bar_x = chart_x + (idx * bar_spacing) + 1
            bar_y = chart_y + chart_height - bar_height - 1
            bar_w = max(1.5, bar_spacing - 2)
            if score <= 30:
                pdf.set_fill_color(0, 128, 0)
            elif score <= 60:
                pdf.set_fill_color(204, 136, 0)
            else:
                pdf.set_fill_color(204, 0, 0)
            pdf.rect(bar_x, bar_y, bar_w, bar_height, style="F")

        pdf.output(output_path)
    except Exception as error:
        raise RuntimeError(f"PDF generation failed: {error}") from error

    print(f"PDF saved to {output_path}")


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

    results: list[dict[str, Any]] = []
    for filepath in python_files:
        try:
            try:
                loc = count_lines_of_code(filepath)
            except PermissionError:
                print(f"Warning: permission denied while reading {filepath}")
                continue
            except FileNotFoundError:
                print(f"Warning: file not found during analysis: {filepath}")
                continue

            file_size = os.path.getsize(filepath)

            source_code: str
            try:
                with open(filepath, "r", encoding="utf-8") as source_file:
                    source_code = source_file.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="latin-1") as source_file:
                    source_code = source_file.read()

            parse_error = False
            parse_error_message = ""
            try:
                tree = ast.parse(source_code)
            except (SyntaxError, UnicodeDecodeError) as error:
                tree = None
                parse_error = True
                parse_error_message = str(error)

            if parse_error:
                ast_metrics = analyze_ast(tree)
                warnings = [
                    {
                        "id": "W-00",
                        "message": f"Parse error: {parse_error_message}",
                        "severity": "HIGH",
                        "metric": "parse_error",
                    }
                ]
                results.append(
                    {
                        "filepath": filepath,
                        "loc": 0,
                        "num_functions": ast_metrics["num_functions"],
                        "num_classes": ast_metrics["num_classes"],
                        "func_lengths": ast_metrics["func_lengths"],
                        "avg_func_len": ast_metrics["avg_func_len"],
                        "max_func_len": ast_metrics["max_func_len"],
                        "nesting_depth": ast_metrics["nesting_depth"],
                        "num_loops": ast_metrics["num_loops"],
                        "file_size": file_size,
                        "warnings": warnings,
                        "score": 75.0,
                        "parse_error": True,
                    }
                )
                continue

            ast_metrics = analyze_ast(tree)
            metrics = {
                "loc": loc,
                "num_functions": ast_metrics["num_functions"],
                "num_classes": ast_metrics["num_classes"],
                "func_lengths": ast_metrics["func_lengths"],
                "avg_func_len": ast_metrics["avg_func_len"],
                "max_func_len": ast_metrics["max_func_len"],
                "nesting_depth": ast_metrics["nesting_depth"],
                "num_loops": ast_metrics["num_loops"],
                "file_size": file_size,
            }
            warnings = detect_warnings(metrics, thresholds=runtime_thresholds)
            score = calculate_complexity_score(metrics)
            results.append(
                {
                    "filepath": filepath,
                    **metrics,
                    "warnings": warnings,
                    "score": score,
                    "parse_error": False,
                }
            )
        except Exception as error:
            print(f"Warning: analysis failed for {filepath}: {error}")
            results.append(
                {
                    "filepath": filepath,
                    "loc": 0,
                    "num_functions": 0,
                    "num_classes": 0,
                    "func_lengths": [],
                    "avg_func_len": 0.0,
                    "max_func_len": 0,
                    "nesting_depth": 0,
                    "num_loops": 0,
                    "file_size": 0,
                    "warnings": [
                        {
                            "id": "W-00",
                            "message": f"Unhandled analysis error: {error}",
                            "severity": "HIGH",
                            "metric": "parse_error",
                        }
                    ],
                    "score": 75.0,
                    "parse_error": True,
                }
            )

    summary = summarize_results(results)
    summary["target_folder"] = os.path.abspath(args.folder)
    generate_terminal_report(results, summary)
    generate_pdf_report(results, summary, args.output)


if __name__ == "__main__":
    main()
