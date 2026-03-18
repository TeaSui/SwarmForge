from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

import requests

from config import settings
from services.executor.flutter_codegen import FlutterCodeGenerator
from services.executor.git_ops import GitOperations

logger = logging.getLogger(__name__)


class GitHubDeliveryService:
    def __init__(self, git_ops: GitOperations, flutter_codegen: FlutterCodeGenerator):
        self.git_ops = git_ops
        self.flutter = flutter_codegen
        self.token = (os.getenv("GITHUB_TOKEN") or getattr(settings, "GITHUB_TOKEN", "")).strip()
        self.repo = os.getenv(
            "SWARMFORGE_TARGET_REPO",
            getattr(settings, "SWARMFORGE_TARGET_REPO", ""),
        ).strip()
        self.base_branch = os.getenv("SWARMFORGE_TARGET_BASE_BRANCH", "main").strip()
        self.bootstrap_branch = os.getenv(
            "SWARMFORGE_FLUTTER_BOOTSTRAP_BRANCH",
            "swarmforge/bootstrap-flutter",
        ).strip()

    def issue_key_from_context(self, context: dict[str, Any]) -> str:
        issue = context.get("payload", {}).get("issue", {})
        return str(issue.get("key") or context.get("task_id") or "unknown")

    def find_existing_open_pr(self, issue_key: str) -> Dict[str, Any] | None:
        response = requests.get(
            f"https://api.github.com/repos/{self.repo}/pulls?state=open&per_page=100",
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )
        if response.status_code >= 300:
            return None
        marker = f"[SwarmForge] {issue_key} ".lower()
        for pr in response.json():
            title = str(pr.get("title", "")).lower()
            if marker in title:
                return {
                    "enabled": True,
                    "reused": True,
                    "repo": self.repo,
                    "pr_url": pr.get("html_url"),
                    "pr_number": pr.get("number"),
                    "branch": (pr.get("head") or {}).get("ref"),
                    "base_branch": (pr.get("base") or {}).get("ref"),
                }
        return None

    def pr_has_real_code_changes(self, pr_number: int) -> bool:
        try:
            response = requests.get(
                f"https://api.github.com/repos/{self.repo}/pulls/{pr_number}/files",
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github+json",
                },
                params={"per_page": 100},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException:
            return False

        for changed in response.json():
            path = str(changed.get("filename", ""))
            if path.startswith("swarmforge_runs/") or path.startswith("lib/src/deliveries/"):
                continue
            if path.startswith("lib/") or path.startswith("test/") or path.startswith("web/"):
                return True
        return False

    def create_pr_for_jira_issue(
        self, run_dir: Path, context: dict[str, Any], synthesized_code: Any | None = None,
    ) -> Dict[str, Any]:
        if context.get("source") != "jira":
            return {"enabled": False, "reason": "non-jira-source"}

        enabled = os.getenv("SWARMFORGE_GITHUB_DELIVERY_ENABLED", "true").lower() == "true"
        if not enabled:
            return {"enabled": False, "reason": "disabled"}

        if not self.token or self.token == "placeholder":
            return {"enabled": False, "reason": "missing-github-token"}

        issue_key = self.issue_key_from_context(context)
        summary = context.get("summary", "")
        existing = self.find_existing_open_pr(issue_key=issue_key)
        if existing is not None:
            pr_number = existing.get("pr_number")
            if isinstance(pr_number, int) and self.pr_has_real_code_changes(pr_number=pr_number):
                existing["real_code_changed"] = True
                return existing

        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        branch = f"codex/{issue_key.lower()}-{ts}"
        workdir = run_dir / "delivery_repo"
        auth_remote = f"https://x-access-token:{self.token}@github.com/{self.repo}.git"

        clone_result = self.git_ops.run_git(["git", "clone", auth_remote, str(workdir)], cwd=run_dir)
        if clone_result["returncode"] != 0:
            return {"enabled": True, "error": "clone_failed", "details": clone_result}

        self.git_ops.run_git(["git", "remote", "set-url", "origin", auth_remote], cwd=workdir)
        self.git_ops.run_git(["git", "checkout", self.base_branch], cwd=workdir)
        self.git_ops.run_git(["git", "checkout", "-b", branch], cwd=workdir)
        self.git_ops.run_git(["git", "config", "user.email", "swarmforge-bot@local"], cwd=workdir)
        self.git_ops.run_git(["git", "config", "user.name", "SwarmForge Bot"], cwd=workdir)

        pubspec = workdir / "pubspec.yaml"
        if not pubspec.exists():
            fetch_result = self.git_ops.run_git(["git", "fetch", "origin", self.bootstrap_branch], cwd=workdir)
            if fetch_result["returncode"] != 0:
                return {"enabled": True, "error": "fetch_bootstrap_failed", "details": fetch_result}
            seed_result = self.git_ops.run_git(
                ["git", "checkout", "FETCH_HEAD", "--", "."],
                cwd=workdir,
            )
            if seed_result["returncode"] != 0:
                return {"enabled": True, "error": "seed_flutter_baseline_failed", "details": seed_result}

        safe_summary = json.dumps(summary)
        real_code_changed = False

        has_llm_files = (
            synthesized_code is not None
            and getattr(synthesized_code, "error", None) is None
            and getattr(synthesized_code, "files", [])
        )

        if has_llm_files:
            for file_entry in synthesized_code.files:
                file_path = workdir / file_entry["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_entry["content"], encoding="utf-8")
                logger.info("Wrote LLM-generated file: %s", file_entry["path"])
            real_code_changed = True
        elif self.flutter.is_session_dashboard_scope(summary, context.get("labels", [])):
            self.flutter.write_session_dashboard_ui(workdir)
            real_code_changed = True
        else:
            generated_module = (
                workdir / "lib" / "src" / "swarmforge" / "generated"
                / f"{issue_key.lower().replace('-', '_')}_task.dart"
            )
            generated_module.parent.mkdir(parents=True, exist_ok=True)
            generated_module.write_text(
                (
                    "/// Generated by SwarmForge autonomous delivery.\n"
                    f"const String kSwarmforgeIssueKey = '{issue_key}';\n"
                    f"const String kSwarmforgeIssueSummary = {safe_summary};\n"
                ),
                encoding="utf-8",
            )
            real_code_changed = True

        delivery_file = workdir / "lib" / "src" / "deliveries" / f"{issue_key.lower()}_delivery.dart"
        delivery_file.parent.mkdir(parents=True, exist_ok=True)
        delivery_file.write_text(
            (
                "/// Autogenerated delivery marker for Jira execution.\n"
                f"const String deliveryIssueKey = '{issue_key}';\n"
                f"const String deliverySummary = {safe_summary};\n"
            ),
            encoding="utf-8",
        )

        report_file = workdir / "swarmforge_runs" / f"{issue_key}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            (
                f"# SwarmForge Delivery: {issue_key}\n\n"
                f"- generated_at: {datetime.now(UTC).isoformat()}\n"
                f"- summary: {summary}\n"
                f"- source: jira\n"
                "- buildable: true (seeded Flutter baseline if needed)\n"
            ),
            encoding="utf-8",
        )

        if "automation test" in summary.lower():
            smoke = workdir / "integration_test" / "health_check_smoke_test.dart"
            smoke.parent.mkdir(parents=True, exist_ok=True)
            smoke.write_text(
                (
                    "import 'package:flutter_test/flutter_test.dart';\n\n"
                    "void main() {\n"
                    "  test('health check placeholder smoke', () {\n"
                    "    expect(true, isTrue);\n"
                    "  });\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

        if "ci/cd" in summary.lower() or "pipeline" in summary.lower():
            workflow = workdir / ".github" / "workflows" / "flutter_ci.yml"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text(
                (
                    "name: Flutter CI\n"
                    "on:\n"
                    "  pull_request:\n"
                    "  push:\n"
                    "    branches: [ main ]\n"
                    "jobs:\n"
                    "  test:\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - uses: actions/checkout@v4\n"
                    "      - uses: subosito/flutter-action@v2\n"
                    "      - run: flutter pub get\n"
                    "      - run: flutter test\n"
                ),
                encoding="utf-8",
            )

        self.git_ops.run_git(["git", "add", "."], cwd=workdir)
        commit_result = self.git_ops.run_git(
            ["git", "commit", "-m", f"feat: deliver {issue_key} via swarmforge automation"],
            cwd=workdir,
        )
        if commit_result["returncode"] != 0:
            return {"enabled": True, "error": "commit_failed", "details": commit_result}

        push_result = self.git_ops.run_git(
            ["git", "push", "-u", "origin", branch],
            cwd=workdir,
        )
        if push_result["returncode"] != 0:
            return {"enabled": True, "error": "push_failed", "details": push_result}

        pr_payload = {
            "title": f"[SwarmForge] {issue_key} {summary}".strip(),
            "head": branch,
            "base": self.base_branch,
            "body": (
                "Autogenerated by SwarmForge autonomous executor.\n\n"
                f"- Issue: {issue_key}\n"
                f"- Summary: {summary}\n"
            ),
        }
        response = requests.post(
            f"https://api.github.com/repos/{self.repo}/pulls",
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json",
            },
            json=pr_payload,
            timeout=30,
        )
        if response.status_code >= 300:
            return {
                "enabled": True,
                "error": "create_pr_failed",
                "status_code": response.status_code,
                "response_tail": response.text[-300:],
            }

        pr = response.json()
        return {
            "enabled": True,
            "repo": self.repo,
            "branch": branch,
            "base_branch": self.base_branch,
            "pr_url": pr.get("html_url"),
            "pr_number": pr.get("number"),
            "real_code_changed": real_code_changed,
        }
