# Agent Workflow & Execution Guidelines

## 1. Git Workflow & Branch Strategy
- Branching Model: GitHub Flow
  - Base branch: `main` (always deployable state).
  - Feature branch naming: `feat/<feature-name>`, `fix/<bug-name>`, `docs/<topic-name>`.
- Rules:
  - Do NOT commit directly to `main` for non-trivial changes; open a Pull Request (PR).
  - Keep commits atomic and self-contained.
  - Follow Commit Convention: `<type>(<scope>): <한글 요약>`.

## 2. Mandatory Pre-commit / Pre-PR Verification
Before committing or creating a PR, the agent MUST run and pass all local checks:
- **Lint Check**: Run `ruff check harness/ tests/` (0 errors required).
- **Unit Tests**: Run `python -m unittest discover -s tests` (100% pass required).
- **Fail-Open Check**: Ensure all hook scripts maintain fail-open behavior (must never block turn on internal hook errors).

## 3. Issue & PR Management
- **Issue Association**: Every PR must reference its corresponding Issue using keywords (e.g., `Closes #<issue_number>`).
- **Label Mapping**: Apply appropriate labels when creating or managing issues/PRs:
  - `guardrail:rule`: Changes related to PreToolUse/commit/infra filtering rules.
  - `guardrail:core`: Changes related to hook lifecycle, state management, or circuit breakers.
  - `ci/cd`: GitHub Actions workflows or automated tooling updates.
  - `bug`: Error fixes or false-positive block resolutions.
  - `enhancement`: Feature improvements and general optimizations.
  - `documentation`: README, AGENTS.md, or convention guide updates.
- **PR Template Checklist**: Ensure all items in `.github/pull_request_template.md` are verified before submission.
