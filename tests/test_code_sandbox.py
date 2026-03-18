"""Tests for the CodeSandbox class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.executor.code_sandbox import CodeSandbox


class TestCodeSandbox:
    """Test suite for CodeSandbox validation."""

    def test_validate_empty_workspace(self):
        """Test validation with empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = CodeSandbox(Path(tmpdir))
            result = sandbox.validate()

            assert not result["passed"]
            assert result["files_analyzed"] == 0
            assert "No Python files found" in result["errors"][0]

    def test_validate_valid_python_file(self):
        """Test validation with valid Python code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create valid Python file
            valid_file = workspace / "valid.py"
            valid_file.write_text("""
def hello_world():
    '''Simple function.'''
    return "Hello, World!"

if __name__ == "__main__":
    print(hello_world())
""")

            sandbox = CodeSandbox(workspace)
            result = sandbox.validate()

            assert result["passed"]
            assert result["files_analyzed"] == 1

            # Check syntax check passed
            syntax_check = next(c for c in result["checks"] if c["name"] == "syntax")
            assert syntax_check["passed"]
            assert syntax_check["files_checked"] == 1

    def test_validate_syntax_error(self):
        """Test validation with Python syntax error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create file with syntax error
            bad_file = workspace / "bad.py"
            bad_file.write_text("""
def broken_function(
    # Missing closing parenthesis
    return "This won't compile"
""")

            sandbox = CodeSandbox(workspace)
            result = sandbox.validate()

            assert not result["passed"]
            assert result["files_analyzed"] == 1

            # Check syntax check failed
            syntax_check = next(c for c in result["checks"] if c["name"] == "syntax")
            assert not syntax_check["passed"]
            assert "Syntax errors" in syntax_check["details"]

    def test_validate_with_test_files(self):
        """Test validation with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create main file
            main_file = workspace / "calculator.py"
            main_file.write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")

            # Create test file
            test_file = workspace / "test_calculator.py"
            test_file.write_text("""
from calculator import add, subtract

def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 3) == 2

if __name__ == "__main__":
    test_add()
    test_subtract()
    print("All tests passed!")
""")

            sandbox = CodeSandbox(workspace)
            result = sandbox.validate()

            # Should pass syntax check
            syntax_check = next(c for c in result["checks"] if c["name"] == "syntax")
            assert syntax_check["passed"]
            assert syntax_check["files_checked"] == 2

            # Test check should be included
            test_check = next(c for c in result["checks"] if c["name"] == "tests")
            assert test_check["test_files"] == 1

    def test_find_files(self):
        """Test finding files by extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create various files
            (workspace / "file1.py").write_text("# Python file 1")
            (workspace / "file2.py").write_text("# Python file 2")
            (workspace / "subdir").mkdir()
            (workspace / "subdir" / "file3.py").write_text("# Python file 3")
            (workspace / "not_python.txt").write_text("Not Python")

            sandbox = CodeSandbox(workspace)
            python_files = sandbox._find_files({".py"})

            assert len(python_files) == 3
            assert all(f.suffix == ".py" for f in python_files)

    def test_find_test_files(self):
        """Test finding test files with various patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create test files with different patterns
            (workspace / "test_module.py").write_text("# Test file")
            (workspace / "module_test.py").write_text("# Test file")
            (workspace / "widget_test.dart").write_text("// Dart test")
            (workspace / "regular_module.py").write_text("# Not a test")

            sandbox = CodeSandbox(workspace)
            test_files = sandbox._find_test_files()

            assert len(test_files) == 3
            test_names = {f.name for f in test_files}
            assert "test_module.py" in test_names
            assert "module_test.py" in test_names
            assert "widget_test.dart" in test_names
            assert "regular_module.py" not in test_names

    @patch("subprocess.run")
    def test_check_lint_ruff_available(self, mock_run):
        """Test lint check when ruff is available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            file1 = workspace / "file.py"
            file1.write_text("x = 1")

            # Mock ruff version check succeeds
            version_result = MagicMock()
            version_result.returncode = 0

            # Mock ruff check succeeds
            check_result = MagicMock()
            check_result.returncode = 0

            mock_run.side_effect = [version_result, check_result]

            sandbox = CodeSandbox(workspace)
            result = sandbox._check_lint([file1])

            assert result["passed"]
            assert "No lint issues" in result["details"]

    @patch("subprocess.run")
    def test_check_lint_ruff_not_available(self, mock_run):
        """Test lint check when ruff is not available."""
        mock_run.side_effect = FileNotFoundError("ruff not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            file1 = workspace / "file.py"
            file1.write_text("x = 1")

            sandbox = CodeSandbox(workspace)
            result = sandbox._check_lint([file1])

            assert result["passed"]
            assert "Ruff not available" in result["details"]

    @patch("subprocess.run")
    def test_run_tests_timeout(self, mock_run):
        """Test handling of test timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 30)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test_module.py"
            test_file.write_text("def test_something(): pass")

            sandbox = CodeSandbox(workspace)
            result = sandbox._run_tests([test_file])

            assert not result["passed"]
            assert "timed out" in result["details"]

    def test_validate_handles_exception(self):
        """Test that validate handles exceptions gracefully."""
        sandbox = CodeSandbox(Path("/nonexistent/path"))
        result = sandbox.validate()

        assert not result["passed"]
        assert len(result["errors"]) > 0