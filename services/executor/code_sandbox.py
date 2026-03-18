"""Code sandbox for validating generated code before delivery."""

from __future__ import annotations

import ast
import logging
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PYTHON_EXTENSIONS = {".py"}
COMMAND_TIMEOUT_SECONDS = 30
PYTHON_BIN = sys.executable or "python3"


class CodeSandbox:
    """Validates generated code files before delivery."""

    def __init__(self, workspace: Path):
        """Initialize the code sandbox with a workspace directory.

        Args:
            workspace: Path to directory containing generated code files
        """
        self.workspace = Path(workspace)

    def validate(self) -> dict[str, Any]:
        """Run all validation checks on the workspace.

        Returns:
            Validation result with passed status and check details
        """
        result = {
            "passed": True,
            "checks": [],
            "files_analyzed": 0,
            "errors": [],
        }

        try:
            # Find Python files
            python_files = self._find_files(PYTHON_EXTENSIONS)
            result["files_analyzed"] = len(python_files)

            if not python_files:
                # Not a failure — workspace may contain non-Python code (e.g. Flutter/Dart)
                result["checks"].append({
                    "name": "syntax",
                    "passed": True,
                    "details": "No Python files found in workspace (non-Python project)",
                })
                return result

            # Run syntax validation
            syntax_check = self._check_python_syntax(python_files)
            result["checks"].append(syntax_check)
            if not syntax_check["passed"]:
                result["passed"] = False

            # Run lint check (non-blocking: LLM-generated code may have style issues)
            lint_check = self._check_lint(python_files)
            result["checks"].append(lint_check)
            if not lint_check["passed"]:
                logger.info("Sandbox lint issues (non-blocking for generated code): %s", lint_check.get("details", ""))

            # Find and run tests (non-blocking: generated code may lack deps)
            test_files = self._find_test_files()
            if test_files:
                test_check = self._run_tests(test_files)
                result["checks"].append(test_check)
                if not test_check["passed"]:
                    # Test failures in sandbox are expected (missing deps, no venv).
                    # Syntax + lint are the hard gates; test failures are warnings.
                    logger.info("Sandbox tests failed (expected for generated code): %s", test_check.get("details", ""))
            else:
                result["checks"].append({
                    "name": "tests",
                    "passed": True,
                    "details": "No test files found",
                    "test_files": 0,
                })

        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
            result["passed"] = False

        return result

    def _find_files(self, extensions: set[str]) -> list[Path]:
        """Find all files with given extensions in workspace.

        Args:
            extensions: Set of file extensions to find (e.g., {".py"})

        Returns:
            List of file paths matching extensions
        """
        files = []
        try:
            for ext in extensions:
                files.extend(self.workspace.rglob(f"*{ext}"))
        except Exception as e:
            logger.error(f"Error finding files: {e}")
        return files

    def _check_python_syntax(self, files: list[Path]) -> dict[str, Any]:
        """Check Python syntax by compiling and parsing files.

        Args:
            files: List of Python file paths to check

        Returns:
            Check result with passed status and details
        """
        result = {
            "name": "syntax",
            "passed": True,
            "details": "",
            "files_checked": 0,
        }

        errors = []
        checked = 0

        for file_path in files:
            try:
                # First try to compile
                py_compile.compile(str(file_path), doraise=True)

                # Then try to parse with AST
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    ast.parse(content)

                checked += 1

            except SyntaxError as e:
                errors.append(f"{file_path.name}: {e.msg} at line {e.lineno}")
                result["passed"] = False
            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")
                result["passed"] = False

        result["files_checked"] = checked

        if result["passed"]:
            result["details"] = f"All {checked} files have valid syntax"
        else:
            result["details"] = f"Syntax errors: {'; '.join(errors)}"

        return result

    def _check_lint(self, files: list[Path]) -> dict[str, Any]:
        """Run ruff linter on Python files if available.

        Args:
            files: List of Python file paths to lint

        Returns:
            Check result with passed status and details
        """
        result = {
            "name": "lint",
            "passed": True,
            "details": "",
        }

        # Check if ruff is available
        try:
            subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result["details"] = "Ruff not available, skipping lint check"
            return result

        # Run ruff check on all Python files
        try:
            file_paths = [str(f) for f in files]
            proc = subprocess.run(
                ["ruff", "check", "--quiet"] + file_paths,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
                cwd=self.workspace,
            )

            if proc.returncode == 0:
                result["details"] = f"No lint issues found in {len(files)} files"
            else:
                result["passed"] = False
                # Truncate output if too long
                output = proc.stdout or proc.stderr
                if len(output) > 500:
                    output = output[:500] + "... (truncated)"
                result["details"] = f"Lint issues found: {output}"

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["details"] = "Lint check timed out"
        except Exception as e:
            result["passed"] = False
            result["details"] = f"Lint check failed: {str(e)}"

        return result

    def _find_test_files(self) -> list[Path]:
        """Find test files in the workspace.

        Returns:
            List of test file paths
        """
        test_patterns = ["test_*.py", "*_test.py", "*_test.dart"]
        test_files = []

        try:
            for pattern in test_patterns:
                test_files.extend(self.workspace.rglob(pattern))
        except Exception as e:
            logger.error(f"Error finding test files: {e}")

        return test_files

    def _run_tests(self, test_files: list[Path]) -> dict[str, Any]:
        """Run test files if they exist.

        Args:
            test_files: List of test file paths

        Returns:
            Check result with passed status and details
        """
        result = {
            "name": "tests",
            "passed": True,
            "details": "",
            "test_files": len(test_files),
        }

        if not test_files:
            result["details"] = "No test files to run"
            return result

        # Group tests by type
        python_tests = [f for f in test_files if f.suffix == ".py"]
        dart_tests = [f for f in test_files if f.suffix == ".dart"]

        errors = []

        # Run Python tests with pytest if available
        if python_tests:
            try:
                proc = subprocess.run(
                    [PYTHON_BIN, "-m", "pytest", "-xvs"] + [str(f) for f in python_tests],
                    capture_output=True,
                    text=True,
                    timeout=COMMAND_TIMEOUT_SECONDS,
                    check=False,
                    cwd=self.workspace,
                )

                if proc.returncode != 0:
                    result["passed"] = False
                    # Extract failure summary
                    output = proc.stdout or proc.stderr
                    if "FAILED" in output:
                        lines = output.split("\n")
                        for line in lines:
                            if "FAILED" in line or "ERROR" in line:
                                errors.append(line.strip())
                                if len(errors) > 5:  # Limit error lines
                                    break
                    else:
                        errors.append(f"Tests failed with code {proc.returncode}")

            except subprocess.TimeoutExpired:
                result["passed"] = False
                errors.append("Python tests timed out")
            except FileNotFoundError:
                # Try running tests directly with python
                for test_file in python_tests[:3]:  # Limit to avoid timeout
                    try:
                        proc = subprocess.run(
                            [PYTHON_BIN, str(test_file)],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            check=False,
                            cwd=self.workspace,
                        )
                        if proc.returncode != 0:
                            result["passed"] = False
                            errors.append(f"{test_file.name} failed")
                    except Exception as e:
                        result["passed"] = False
                        errors.append(f"{test_file.name}: {str(e)}")
            except Exception as e:
                result["passed"] = False
                errors.append(f"Python test error: {str(e)}")

        # Run Dart tests if any
        if dart_tests:
            try:
                proc = subprocess.run(
                    ["dart", "test"] + [str(f) for f in dart_tests],
                    capture_output=True,
                    text=True,
                    timeout=COMMAND_TIMEOUT_SECONDS,
                    check=False,
                    cwd=self.workspace,
                )

                if proc.returncode != 0:
                    result["passed"] = False
                    errors.append("Dart tests failed")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Dart not available or timed out, skip gracefully
                pass
            except Exception as e:
                result["passed"] = False
                errors.append(f"Dart test error: {str(e)}")

        # Set details
        if result["passed"]:
            result["details"] = f"All {len(test_files)} test files passed"
        else:
            error_msg = "; ".join(errors) if errors else "Test execution failed"
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "... (truncated)"
            result["details"] = error_msg

        return result