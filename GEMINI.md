# Global Development Conventions & Environment Guidelines

## 1. Response Language
- Always respond to the user in concise, professional Korean (한국어).
- Do NOT use emojis.

## 2. Environment & Shell Guidelines
- Host OS: Windows
- Default Shell: PowerShell (Do NOT use Linux/Bash syntax like `export`, `source`, `grep`, `rm -rf`, `cat`)
- Command Mappings:
  - Environment Variables: `$env:VAR = "value"` (NEVER `export VAR=value`)
  - Virtualenv Activation: `.\.venv\Scripts\Activate.ps1` (NEVER `source .venv/bin/activate`)
  - Java / Gradle: `.\gradlew.bat test` (NEVER `./gradlew test`)
  - Python Tooling: Use `uv run <cmd>` or `poetry run <cmd>` when available.
  - File Reading: `Get-Content <file>`
  - Pattern Search: `Select-String -Pattern "..."` (NEVER `grep`)
  - Path Handling: Use Windows path conventions with proper quotes.
  - CLI Tools: `gh` (GitHub CLI), `git`, `uv`, `docker`, `gcloud`

## 3. Commit Message Convention
- Format: `<type>(<scope>): <한글 요약>` (scope is optional but recommended)
  - Type & Scope: Lowercase English (`feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf`, `ci`)
  - Subject: Clear Korean summary without period (e.g. `feat(auth): 카카오 소셜 로그인 연동`)
  - Body: Atomic commits preferred. Add Korean body only if necessary for context.

## 4. Code Comments Convention
- Language: Korean (한국어)
- Style: Production-grade professional comments.
- Prohibited:
  - NO tutorial-style comments (e.g., "checks if condition", "declares variable").
  - NO obvious redundant code explanation.
  - NO caller listing (IDE references handle this).
- Required Targets:
  - **Why**: Business or architectural reasons behind algorithms, workarounds, or libraries.
  - **Constraints**: Parameter constraints, units, nullability policies, validation rules.
  - **Side-effects / Edge-cases**: External dependencies, exception conditions, concurrency caveats.
