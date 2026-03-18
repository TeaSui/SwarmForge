import pytest
from unittest.mock import patch

from services.quality_gate import QualityGateEvaluator


def test_quality_gate_passes_when_required_evidence_present():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Backend API", "labels": ["api"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md", "delivery": {"repo": "TeaSui/repo", "pr_number": 1}},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "documentation": {"artifact": "REPORT.md"},
    }

    with patch.object(evaluator, "_fetch_pr_files", return_value=["lib/main.dart"]):
        report = evaluator.evaluate(
            context=context,
            stage_results=stage_results,
            pr_url="https://github.com/a/b/pull/1",
        )
    assert report["passed"] is True


def test_quality_gate_fails_without_delivery_pr_for_jira():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Backend API", "labels": ["api"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md"},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "documentation": {"artifact": "REPORT.md"},
    }

    report = evaluator.evaluate(context=context, stage_results=stage_results, pr_url=None)
    assert report["passed"] is False
    assert "delivery-pr" in report["failed_checks"]


def test_quality_gate_fails_when_delivery_has_no_real_code_changes():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Backend API", "labels": ["api"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md"},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "documentation": {"artifact": "REPORT.md"},
    }

    with patch.object(
        evaluator,
        "_fetch_pr_files",
        return_value=["swarmforge_runs/SCRUM-99.md", "lib/src/deliveries/scrum-99_delivery.dart"],
    ):
        report = evaluator.evaluate(
            context=context,
            stage_results=stage_results,
            pr_url="https://github.com/a/b/pull/99",
        )

    assert report["passed"] is False
    assert "delivery-real-code" in report["failed_checks"]


def test_quality_gate_ui_requires_design_signal():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Dashboard UI refresh", "labels": ["ui"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md", "delivery": {"repo": "TeaSui/repo", "pr_number": 9}},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "ui-accessibility-gate": {"artifact": "UI_A11Y.json"},
        "documentation": {"artifact": "REPORT.md"},
    }

    with patch("services.quality_gate.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"filename": "lib/main.dart"},
            {"filename": "lib/screens/dashboard_screen.dart"},
            {"filename": "README.md"},
        ]
        report = evaluator.evaluate(
            context=context,
            stage_results=stage_results,
            pr_url="https://github.com/TeaSui/repo/pull/9",
        )

    assert report["passed"] is False
    assert "ui-design-signal" in report["failed_checks"]


def test_quality_gate_dashboard_word_alone_is_not_ui_scope():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Observability Dashboard Slice", "labels": ["gsd-integration"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md", "delivery": {"repo": "TeaSui/repo", "pr_number": 10}},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "documentation": {"artifact": "REPORT.md"},
    }

    with patch.object(evaluator, "_fetch_pr_files", return_value=["lib/main.dart"]):
        report = evaluator.evaluate(
            context=context,
            stage_results=stage_results,
            pr_url="https://github.com/TeaSui/repo/pull/10",
        )
    assert report["passed"] is True


def test_quality_gate_requires_e2e_and_slo_on_release_scope():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Production-readiness release", "labels": ["release"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md", "delivery": {"repo": "TeaSui/repo", "pr_number": 12}},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "documentation": {"artifact": "REPORT.md"},
    }
    report = evaluator.evaluate(
        context=context,
        stage_results=stage_results,
        pr_url="https://github.com/TeaSui/repo/pull/12",
    )
    assert report["passed"] is False
    assert "artifacts-complete" in report["failed_checks"]


def test_quality_gate_release_scope_passes_with_e2e_and_slo_artifacts():
    evaluator = QualityGateEvaluator()
    context = {"source": "jira", "summary": "Production-readiness release", "labels": ["release"]}
    stage_results = {
        "intent-analysis": {"artifact": "intent.json"},
        "solution-plan": {"artifact": "PLAN.md"},
        "code-generation": {"artifact": "CODEGEN.md", "delivery": {"repo": "TeaSui/repo", "pr_number": 13}},
        "test-verification": {"artifact": "TEST.json"},
        "security-check": {"artifact": "SECURITY.json"},
        "e2e-verification": {"artifact": "E2E.json"},
        "post-deploy-slo-gate": {"artifact": "SLO_GATE.json"},
        "documentation": {"artifact": "REPORT.md"},
    }
    with patch.object(evaluator, "_fetch_pr_files", return_value=["lib/main.dart"]):
        report = evaluator.evaluate(
            context=context,
            stage_results=stage_results,
            pr_url="https://github.com/TeaSui/repo/pull/13",
        )
    assert report["passed"] is True


# ---------------------------------------------------------------------------
# Parametrized scope detection tests
# ---------------------------------------------------------------------------

class TestScopeDetection:
    @pytest.mark.parametrize("summary,labels,expected", [
        ("Dashboard UI refresh", ["ui"], True),
        ("Improve frontend accessibility", [], True),
        ("Theme customization", ["api"], True),
        ("Backend ingestion reliability", ["session-dashboard"], False),
        ("Observability Dashboard Slice", ["gsd-integration"], False),
        ("API endpoint update", ["api"], False),
    ])
    def test_is_ui_scoped(self, summary: str, labels: list[str], expected: bool):
        evaluator = QualityGateEvaluator()
        context = {"summary": summary, "labels": labels}
        assert evaluator._is_ui_scoped(context) is expected

    @pytest.mark.parametrize("summary,labels,expected", [
        ("E2E regression suite", [], True),
        ("Production-readiness check", ["e2e"], True),
        ("UAT verification", [], True),
        ("Fix login bug", ["api"], False),
        ("Backend API", ["ai-task"], False),
    ])
    def test_requires_e2e(self, summary: str, labels: list[str], expected: bool):
        evaluator = QualityGateEvaluator()
        context = {"summary": summary, "labels": labels}
        assert evaluator._requires_e2e(context) is expected

    @pytest.mark.parametrize("summary,labels,expected", [
        ("Prepare prod release", ["release"], True),
        ("Deploy to production", [], True),
        ("Go-live checklist", ["api"], True),
        ("Fix login bug", ["api"], False),
        ("Backend API", ["ai-task"], False),
    ])
    def test_requires_release_slo(self, summary: str, labels: list[str], expected: bool):
        evaluator = QualityGateEvaluator()
        context = {"summary": summary, "labels": labels}
        assert evaluator._requires_release_slo(context) is expected
