"""Pytest suite for Codebase Complexity Analyzer (Phase 10)."""

import os
import tempfile

import pytest

from project import calculate_complexity_score, count_lines_of_code, get_python_files


def test_get_python_files_basic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for name in ["a.py", "b.py", "c.py"]:
            open(os.path.join(tmp, name), "w", encoding="utf-8").close()
        result = get_python_files(tmp)
        assert len(result) == 3
        assert all(path.endswith(".py") for path in result)


def test_get_python_files_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert get_python_files(tmp) == []


def test_get_python_files_recursive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        nested = os.path.join(tmp, "nested")
        os.makedirs(nested)
        open(os.path.join(tmp, "root.py"), "w", encoding="utf-8").close()
        open(os.path.join(nested, "deep.py"), "w", encoding="utf-8").close()
        result = get_python_files(tmp)
        assert len(result) == 2
        basenames = sorted(os.path.basename(p) for p in result)
        assert basenames == ["deep.py", "root.py"]


def test_get_python_files_nonexistent() -> None:
    with pytest.raises(FileNotFoundError):
        get_python_files("/this/path/does/not/exist")


def test_get_python_files_no_recurse() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        nested = os.path.join(tmp, "nested")
        os.makedirs(nested)
        open(os.path.join(tmp, "top.py"), "w", encoding="utf-8").close()
        open(os.path.join(nested, "inner.py"), "w", encoding="utf-8").close()
        result = get_python_files(tmp, recursive=False)
        assert len(result) == 1
        assert os.path.basename(result[0]) == "top.py"


def test_count_lines_of_code_basic() -> None:
    src = "x = 1\ny = 2\n\nz = 3\na = 4\nb = 5\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(src)
        path = handle.name
    try:
        assert count_lines_of_code(path) == 5
    finally:
        os.unlink(path)


def test_count_lines_of_code_empty() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        path = handle.name
    try:
        assert count_lines_of_code(path) == 0
    finally:
        os.unlink(path)


def test_count_lines_of_code_comments_only() -> None:
    src = "# comment 1\n# comment 2\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(src)
        path = handle.name
    try:
        assert count_lines_of_code(path) == 0
    finally:
        os.unlink(path)


def test_count_lines_of_code_inline_comment() -> None:
    src = "x = 1  # comment\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(src)
        path = handle.name
    try:
        assert count_lines_of_code(path) == 1
    finally:
        os.unlink(path)


def test_count_lines_of_code_mixed() -> None:
    src = (
        "a = 1\n"
        "\n"
        "b = 2\n"
        "# comment\n"
        "\n"
        "c = 3\n"
        "d = 4\n"
        "e = 5\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(src)
        path = handle.name
    try:
        assert count_lines_of_code(path) == 5
    finally:
        os.unlink(path)


def test_calculate_complexity_score_zero() -> None:
    metrics = {
        "max_func_len": 0,
        "nesting_depth": 0,
        "loc": 0,
        "num_functions": 0,
        "avg_func_len": 0.0,
    }
    assert calculate_complexity_score(metrics) == 0.0


def test_calculate_complexity_score_long_func() -> None:
    metrics = {
        "max_func_len": 100,
        "nesting_depth": 0,
        "loc": 0,
        "num_functions": 0,
        "avg_func_len": 0.0,
    }
    score = calculate_complexity_score(metrics)
    assert score > 0
    assert score == 25.0


def test_calculate_complexity_score_deep_nesting() -> None:
    metrics = {
        "max_func_len": 0,
        "nesting_depth": 6,
        "loc": 0,
        "num_functions": 0,
        "avg_func_len": 0.0,
    }
    score = calculate_complexity_score(metrics)
    assert score == 24.0


def test_calculate_complexity_score_clamp() -> None:
    metrics = {
        "max_func_len": 9999,
        "nesting_depth": 999,
        "loc": 9999,
        "num_functions": 999,
        "avg_func_len": 999.0,
    }
    assert calculate_complexity_score(metrics) == 100.0


def test_calculate_complexity_score_partial() -> None:
    metrics = {
        "max_func_len": 0,
        "nesting_depth": 0,
        "loc": 600,
        "num_functions": 0,
        "avg_func_len": 0.0,
    }
    score = calculate_complexity_score(metrics)
    assert score > 0
    assert score == 15.0
