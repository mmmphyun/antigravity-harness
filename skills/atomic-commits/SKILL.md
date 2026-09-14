---
name: atomic-commits
description: >
  빅뱅 커밋을 원천 차단하고 1-Task 1-Commit 원칙을 기계적으로 준수하도록 작업을 최소 단위로 분해하고 즉시 커밋하는 하네스 연동 스킬.
  "atomic-commits", "커밋 쪼개서 해", "빅뱅 커밋 금지", "원자적 커밋", "작업 단위 분할" 요청 시 또는 다중 결함/기능 구현 자율 주행 시 필수 발동.
---

# atomic-commits: 전역 범용 마이크로 커밋 분할 프로토콜

이 스킬은 LLM 에이전트의 고질적인 '일괄 완성 후 단일 거대 커밋(Big-Bang Commit)' 실행 관성을 차단하고, **1개 논리적 작업(Task) = 1개 커밋(Commit)**의 원자성을 엄격히 보장하기 위한 안티그래비티 전역 범용 프로토콜입니다.

---

## 1. 4단계 마이크로 실행 루프 (The Micro-Loop)

복수 기능이나 다중 결함 수정 요구가 인입되면 모든 코드를 한 번에 작성하는 행위를 엄격히 금지하고, 반드시 아래 4단계를 순환 실행합니다.

```
[1. Task 계획 분해] ──> [2. 단일 태스크 TDD 구현] ──> [3. 핀포인트 파일 스테이징] ──> [4. Green 즉시 커밋]
         ▲                                                                                   │
         └─────────────────────────── 다음 태스크로 이동 ────────────────────────────────────┘
```

### 1단계: 커밋 계획 수립 (Commit Plan Decomposition)
- 작업을 시작하기 전, 프롬프트의 요구사항을 **독립적으로 빌드/테스트 가능한 최소 커밋 단위**로 분해하여 사용자에게 먼저 선언합니다.
- 예시:
  - `[Commit 1/3] feat(auth): JWT 토큰 검증 로직 및 만료 예외 처리`
  - `[Commit 2/3] feat(user): 사용자 프로필 조회 엔드포인트 및 DTO 매핑`
  - `[Commit 3/3] feat(cache): Redis 사용자 세션 캐싱 및 무효화 연동`

### 2단계: 단일 태스크 집중 구현 (Strict Scope Isolation)
- 현재 진행 중인 1개 태스크에 속하지 않는 파일은 **단 한 글자도 미리 수정하지 않습니다**.
- 반드시 검증 테스트(`tests/` 또는 `src/test/`)와 실제 소스(`src/`)의 1개 쌍만 집중 구현합니다.

### 3단계: 핀포인트 명시 스테이징 (No Wildcard Staging)
- `git add .` 또는 `git add -A`와 같은 와일드카드 명령 사용을 **전면 금지**합니다.
- 반드시 현재 태스크에 직접 관련된 소스 및 테스트 파일 경로만 명시적으로 스테이징합니다:
  ```powershell
  # Python 예시
  git add src/auth/jwt.py tests/test_jwt.py

  # TypeScript / React 예시
  git add src/components/UserProfile.tsx src/components/UserProfile.test.tsx

  # Kotlin / Java 예시
  git add src/main/kotlin/com/example/UserService.kt src/test/kotlin/com/example/UserServiceTest.kt

  # Go 예시
  git add pkg/auth/token.go pkg/auth/token_test.go
  ```

### 4단계: Green-State 즉시 커밋 (Immediate Commit)
- 단위/통합 테스트가 통과하면 다음 태스크 코드를 작성하기 전에 **즉시 터미널에서 커밋을 실행**합니다.
  ```powershell
  git commit -m "<type>(<scope>): <한글 요약>"
  ```
- 커밋 성공을 확인한 후에만 다음 태스크로 넘어갑니다.

---

## 2. 원자적 커밋 크기 상한선 (Threshold Bounds)

Git 훅(pre-commit)이 설치된 레포지토리에서는 물리적 차단선으로 동작하며, 훅이 없는 일반 레포지토리에서도 에이전트가 **스스로 준수해야 하는 절대적 상한선(Self-Imposed Bound)**으로 동작합니다:

1. **최대 스테이징 파일 수**: 단일 `feat`/`refactor` 커밋당 **최대 4개 파일** (핵심 소스 1~2개 + 검증 테스트 1~2개). 초과 시 커밋을 즉시 중단하고 분할.
2. **최대 라인 변경량**: 단일 커밋당 **최대 250줄**(diffstat insertions + deletions 기준, 문서/자동생성 파일 제외).
3. **단일 모듈/도메인 제한**: 멀티모듈/모노레포 환경에서 2개 이상의 독립 모듈을 단일 커밋에 결합하는 행위 금지.

---

## 3. 위반 시 비상 분할 수칙 (Emergency Re-splitting)

만약 실행 관성으로 인해 여러 태스크의 파일을 이미 동시에 수정해버렸다면, 전체를 일괄 커밋하지 말고 즉시 변경사항을 쪼개어 단계별로 커밋합니다:

```powershell
# 1. 모든 스테이징 해제
git restore --staged .

# 2. 첫 번째 태스크 관련 소스/테스트 파일만 개별 추가
git add src/task1/File.py tests/task1/test_file.py

# 3. 1차 원자적 커밋
git commit -m "feat(task1): 1차 작업 요약"

# 4. 두 번째 태스크 파일 추가 및 2차 원자적 커밋
git add src/task2/File.py tests/task2/test_file.py
git commit -m "feat(task2): 2차 작업 요약"
```
