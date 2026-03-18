"""Tests for LLM-powered pipeline stages."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from services.executor.llm_stages import (
    review_code,
    security_analysis,
    generate_documentation,
    accessibility_review,
    collect_generated_files,
    _extract_json_from_llm,
)


class TestExtractJson:
    """Test JSON extraction from LLM responses."""

    def test_direct_json(self):
        """Test extracting plain JSON."""
        content = '{"key": "value", "number": 42}'
        result = _extract_json_from_llm(content)
        assert result == {"key": "value", "number": 42}

    def test_json_in_markdown(self):
        """Test extracting JSON from markdown code block."""
        content = '''Some text
```json
{"approved": true, "issues": []}
```
More text'''
        result = _extract_json_from_llm(content)
        assert result == {"approved": True, "issues": []}

    def test_json_in_plain_code_block(self):
        """Test extracting JSON from plain code block."""
        content = '''
```
{"safe": false, "vulnerabilities": [{"type": "SQL Injection"}]}
```
'''
        result = _extract_json_from_llm(content)
        assert result == {"safe": False, "vulnerabilities": [{"type": "SQL Injection"}]}

    def test_invalid_json(self):
        """Test handling invalid JSON."""
        content = "This is not JSON at all"
        result = _extract_json_from_llm(content)
        assert result is None


class TestReviewCode:
    """Test code review function."""

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_successful_review(self, mock_chat):
        """Test successful code review."""
        mock_chat.return_value = json.dumps({
            "approved": False,
            "issues": [
                {"severity": "critical", "file": "main.py", "description": "SQL injection risk"}
            ],
            "summary": "Found critical security issue"
        })

        result = review_code("code content", "context summary")

        assert result["approved"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "critical"
        assert "SQL injection" in result["issues"][0]["description"]
        assert "critical security issue" in result["summary"]

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_unparseable_response(self, mock_chat):
        """Test handling unparseable LLM response."""
        mock_chat.return_value = "This is not JSON"

        result = review_code("code content", "context summary")

        assert result["approved"] is True
        assert result["issues"] == []
        assert "Could not parse" in result["summary"]

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_llm_failure(self, mock_chat):
        """Test handling LLM failure."""
        mock_chat.side_effect = Exception("LLM error")

        result = review_code("code content", "context summary")

        assert result["approved"] is True
        assert result["issues"] == []
        assert "LLM review unavailable" in result["summary"]
        assert result["error"] == "LLM error"


class TestSecurityAnalysis:
    """Test security analysis function."""

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_vulnerabilities_found(self, mock_chat):
        """Test finding security vulnerabilities."""
        mock_chat.return_value = json.dumps({
            "safe": False,
            "vulnerabilities": [
                {
                    "severity": "high",
                    "type": "Hardcoded Secret",
                    "file": "config.py",
                    "description": "API key in source code",
                    "remediation": "Use environment variables"
                }
            ],
            "summary": "Found hardcoded credentials"
        })

        result = security_analysis("code content", "context summary")

        assert result["safe"] is False
        assert len(result["vulnerabilities"]) == 1
        vuln = result["vulnerabilities"][0]
        assert vuln["severity"] == "high"
        assert vuln["type"] == "Hardcoded Secret"
        assert "environment variables" in vuln["remediation"]

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_no_vulnerabilities(self, mock_chat):
        """Test when no vulnerabilities found."""
        mock_chat.return_value = json.dumps({
            "safe": True,
            "vulnerabilities": [],
            "summary": "No security issues found"
        })

        result = security_analysis("code content", "context summary")

        assert result["safe"] is True
        assert result["vulnerabilities"] == []

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_security_analysis_error(self, mock_chat):
        """Test security analysis error handling."""
        mock_chat.side_effect = Exception("Analysis failed")

        result = security_analysis("code content", "context summary")

        assert result["safe"] is True
        assert "error" in result
        assert "unavailable" in result["summary"]


class TestGenerateDocumentation:
    """Test documentation generation."""

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_successful_generation(self, mock_chat):
        """Test successful documentation generation."""
        mock_chat.return_value = "# API Documentation\n\n## Overview\nThis is the docs."

        context = {
            "task_id": "TASK-123",
            "summary": "Create user API"
        }

        result = generate_documentation("code content", context)

        assert "# API Documentation" in result
        assert "Overview" in result

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_generation_failure(self, mock_chat):
        """Test documentation generation failure."""
        mock_chat.side_effect = Exception("Generation failed")

        context = {"task_id": "TASK-456", "summary": "Create API"}

        result = generate_documentation("code content", context)

        assert "# Documentation" in result
        assert "Create API" in result
        assert "documentation generation failed" in result.lower()


class TestAccessibilityReview:
    """Test accessibility review function."""

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_accessibility_issues(self, mock_chat):
        """Test finding accessibility issues."""
        mock_chat.return_value = json.dumps({
            "compliant": False,
            "issues": [
                {
                    "severity": "critical",
                    "guideline": "WCAG 2.1 - 1.4.3",
                    "file": "form.html",
                    "description": "Insufficient color contrast",
                    "remediation": "Increase contrast ratio to 4.5:1"
                }
            ],
            "summary": "Found accessibility violations"
        })

        result = accessibility_review("html content", "context")

        assert result["compliant"] is False
        assert len(result["issues"]) == 1
        issue = result["issues"][0]
        assert "WCAG" in issue["guideline"]
        assert "contrast" in issue["description"]

    @patch('services.executor.llm_stages._llm_chat_sync')
    def test_accessibility_compliant(self, mock_chat):
        """Test when code is accessibility compliant."""
        mock_chat.return_value = json.dumps({
            "compliant": True,
            "issues": [],
            "summary": "Code meets WCAG 2.1 AA standards"
        })

        result = accessibility_review("html content", "context")

        assert result["compliant"] is True
        assert result["issues"] == []


class TestCollectGeneratedFiles:
    """Test file collection function."""

    def test_collect_code_files(self, tmp_path):
        """Test collecting code files from workspace."""
        # Create test files
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.js").write_text("function test() {}")
        (tmp_path / "config.json").write_text('{"key": "value"}')
        (tmp_path / "image.png").write_bytes(b"binary data")

        # Create subdirectory
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "module.py").write_text("class MyClass: pass")

        # Create skip directory
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("should be skipped")

        result = collect_generated_files(tmp_path)

        # Check included files
        assert "=== main.py ===" in result
        assert "print('hello')" in result
        assert "=== utils.js ===" in result
        assert "function test()" in result
        assert "=== config.json ===" in result
        assert "=== src/module.py ===" in result or "=== src\\module.py ===" in result

        # Check excluded files
        assert "image.png" not in result
        assert "node_modules" not in result
        assert "should be skipped" not in result

    def test_max_chars_limit(self, tmp_path):
        """Test respecting max_chars limit."""
        # Create large file
        large_content = "x" * 1000
        (tmp_path / "file1.py").write_text(large_content)
        (tmp_path / "file2.py").write_text(large_content)

        result = collect_generated_files(tmp_path, max_chars=500)

        assert "truncated" in result
        assert len(result) < 600  # Should be close to limit

    def test_empty_workspace(self, tmp_path):
        """Test empty workspace."""
        result = collect_generated_files(tmp_path)
        assert "No code files found" in result

    def test_unicode_handling(self, tmp_path):
        """Test handling unicode in files."""
        (tmp_path / "unicode.py").write_text("# 你好世界\nprint('hello')", encoding='utf-8')

        result = collect_generated_files(tmp_path)

        assert "=== unicode.py ===" in result
        assert "hello" in result

    def test_permission_error(self, tmp_path):
        """Test handling permission errors."""
        restricted_file = tmp_path / "restricted.py"
        restricted_file.write_text("content")

        with patch('pathlib.Path.read_text', side_effect=PermissionError("No access")):
            result = collect_generated_files(tmp_path)
            # Should handle error gracefully
            assert isinstance(result, str)