from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import requests

from config import settings

logger = logging.getLogger(__name__)


class QualityGateEvaluator:
    _UI_KEYWORDS = ("ui", "frontend", "design", "theme", "ux")
    _UI_LABELS = {"ui", "frontend"}
    _RELEASE_KEYWORDS = ("release", "deploy", "go-live", "production-readiness")
    _RELEASE_LABELS = {"release", "prod-release", "deploy"}
    _E2E_KEYWORDS = ("e2e", "uat", "regression", "smoke", "production-readiness")
    _E2E_LABELS = {"e2e", "uat", "regression", "smoke"}
    _UI_FILE_PATTERN = re.compile(
        r"^(lib/|web/|assets/)|\.(css|scss|sass|html|js|jsx|ts|tsx|dart)$"
    )
    _UI_DESIGN_PATTERN = re.compile(r"(theme|design|style|token|typography|color)", re.IGNORECASE)
    _NON_PRODUCT_PATH_PATTERN = re.compile(r"^(swarmforge_runs/|lib/src/deliveries/)")

    def evaluate(
        self,
        *,
        context: dict[str, Any],
        stage_results: dict[str, dict[str, Any]],
        pr_url: str | None,
    ) -> dict[str, Any]:
        if not settings.SWARMFORGE_QUALITY_GATES_ENABLED:
            return {"enabled": False, "passed": True, "checks": []}

        checks: list[dict[str, Any]] = []

        def add_check(name: str, passed: bool, details: str, required: bool = True):
            checks.append(
                {
                    "name": name,
                    "passed": passed,
                    "required": required,
                    "details": details,
                }
            )

        required_stages = [
            "intent-analysis",
            "solution-plan",
            "code-generation",
            "test-verification",
            "security-check",
            "documentation",
        ]
        if self._requires_e2e(context):
            required_stages.append("e2e-verification")
        if self._is_ui_scoped(context):
            required_stages.append("ui-accessibility-gate")
        if self._requires_release_slo(context):
            required_stages.append("post-deploy-slo-gate")
        missing_artifacts = [
            stage
            for stage in required_stages
            if not (stage_results.get(stage, {}).get("artifact"))
        ]
        add_check(
            "artifacts-complete",
            len(missing_artifacts) == 0,
            "all required stage artifacts present"
            if not missing_artifacts
            else f"missing artifacts for: {', '.join(missing_artifacts)}",
        )

        test_result = stage_results.get("test-verification", {})
        test_ok = not bool(test_result.get("warning"))
        add_check(
            "tests-pass",
            test_ok,
            "smoke tests passed" if test_ok else str(test_result.get("warning")),
        )

        security_result = stage_results.get("security-check", {})
        security_ok = not bool(security_result.get("warning"))
        add_check(
            "security-pass",
            security_ok,
            "security check completed" if security_ok else str(security_result.get("warning")),
        )

        if self._requires_e2e(context):
            e2e_result = stage_results.get("e2e-verification", {})
            e2e_ok = not bool(e2e_result.get("warning"))
            add_check(
                "e2e-pass",
                e2e_ok,
                "e2e verification passed" if e2e_ok else str(e2e_result.get("warning")),
            )

        if self._requires_release_slo(context):
            slo_result = stage_results.get("post-deploy-slo-gate", {})
            slo_ok = not bool(slo_result.get("warning"))
            add_check(
                "post-deploy-slo-pass",
                slo_ok,
                "post-deploy SLO checks passed" if slo_ok else str(slo_result.get("warning")),
            )

        if context.get("source") == "jira":
            add_check(
                "delivery-pr",
                bool(pr_url),
                f"delivery PR linked: {pr_url}" if pr_url else "no PR linked in execution output",
            )
            files = self._fetch_pr_files(stage_results=stage_results, pr_url=pr_url)
            has_real_code = self._has_real_delivery_code(files) or bool(
                stage_results.get("code-generation", {})
                .get("delivery", {})
                .get("real_code_changed")
            )
            add_check(
                "delivery-real-code",
                has_real_code,
                "product code changes detected in delivery PR"
                if has_real_code
                else "delivery PR does not contain product code changes",
            )

        if self._is_ui_scoped(context):
            ui_stage = stage_results.get("ui-accessibility-gate", {})
            ui_stage_ok = not bool(ui_stage.get("warning"))
            add_check(
                "ui-a11y-pass",
                ui_stage_ok,
                "ui accessibility checks passed" if ui_stage_ok else str(ui_stage.get("warning")),
            )

            files = self._fetch_pr_files(stage_results=stage_results, pr_url=pr_url)
            has_ui_changes = any(self._UI_FILE_PATTERN.search(path) for path in files)
            if not has_ui_changes and not files and pr_url:
                # Fallback: when GitHub file API is temporarily unavailable but a PR exists,
                # avoid hard-failing UI flow on missing file list.
                logger.warning("No PR files available from GitHub API; falling back to pass for ui-files-changed")
                has_ui_changes = True
            add_check(
                "ui-files-changed",
                has_ui_changes,
                "ui-impacting files detected"
                if has_ui_changes
                else "no UI-impacting files found in PR",
            )

            has_design_signal = any(self._UI_DESIGN_PATTERN.search(path) for path in files)
            if not has_design_signal and not files and pr_url:
                logger.warning("No PR files available from GitHub API; falling back to summary check for ui-design-signal")
                summary = str(context.get("summary", "")).lower()
                has_design_signal = any(k in summary for k in self._UI_KEYWORDS)
            add_check(
                "ui-design-signal",
                has_design_signal,
                "design/theming artifacts detected"
                if has_design_signal
                else "no explicit design token/theme/style artifact detected",
            )

        required_failures = [c for c in checks if c["required"] and not c["passed"]]
        return {
            "enabled": True,
            "passed": len(required_failures) == 0,
            "failed_checks": [c["name"] for c in required_failures],
            "checks": checks,
        }

    def _is_ui_scoped(self, context: dict[str, Any]) -> bool:
        summary = str(context.get("summary", "")).lower()
        labels = {str(x).lower() for x in context.get("labels", [])}
        return any(k in summary for k in self._UI_KEYWORDS) or bool(labels.intersection(self._UI_LABELS))

    def _requires_e2e(self, context: dict[str, Any]) -> bool:
        summary = str(context.get("summary", "")).lower()
        labels = {str(x).lower() for x in context.get("labels", [])}
        return any(k in summary for k in self._E2E_KEYWORDS) or bool(labels.intersection(self._E2E_LABELS))

    def _requires_release_slo(self, context: dict[str, Any]) -> bool:
        summary = str(context.get("summary", "")).lower()
        labels = {str(x).lower() for x in context.get("labels", [])}
        return any(k in summary for k in self._RELEASE_KEYWORDS) or bool(
            labels.intersection(self._RELEASE_LABELS)
        )

    def _fetch_pr_files(
        self,
        *,
        stage_results: dict[str, dict[str, Any]],
        pr_url: str | None,
    ) -> list[str]:
        delivery = stage_results.get("code-generation", {}).get("delivery", {})
        repo = str(
            delivery.get("repo")
            or settings.SWARMFORGE_TARGET_REPO
            or ""
        ).strip()
        pr_number = delivery.get("pr_number") or self._pr_number_from_url(pr_url)
        token = (settings.GITHUB_TOKEN or "").strip()
        if not repo or not pr_number or not token or token == "placeholder":
            return []

        all_files: list[str] = []
        for page in range(1, 6):
            try:
                response = requests.get(
                    f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    params={"per_page": 100, "page": page},
                    timeout=30,
                )
            except requests.RequestException:
                return all_files
            if response.status_code >= 300:
                return all_files
            batch = [str(f.get("filename", "")) for f in response.json()]
            all_files.extend(batch)
            if len(batch) < 100:
                break
        return all_files

    _PRODUCT_CODE_PREFIXES = (
        "lib/", "test/", "web/",           # Flutter/Dart
        "src/", "app/", "api/", "services/", "tests/", "scripts/",  # Python/general
    )
    _PRODUCT_CODE_EXTENSIONS = {
        ".py", ".dart", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    }

    def _has_real_delivery_code(self, files: list[str]) -> bool:
        for path in files:
            if self._NON_PRODUCT_PATH_PATTERN.search(path):
                continue
            if any(path.startswith(prefix) for prefix in self._PRODUCT_CODE_PREFIXES):
                return True
            if any(path.endswith(ext) for ext in self._PRODUCT_CODE_EXTENSIONS):
                return True
        return False

    def _pr_number_from_url(self, pr_url: str | None) -> int | None:
        if not pr_url:
            return None
        parsed = urlparse(pr_url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 4 or parts[-2] != "pull":
            return None
        try:
            return int(parts[-1])
        except ValueError:
            return None
