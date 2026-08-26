# Global Development Conventions

## 1. Commit Message Convention
- Format: `<type>(<scope>): <한글 요약>` (scope는 선택 사항이나 가급적 명시)
  - Type & Scope: 영문 소문자 (`feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf` 등)
  - Subject: 한글로 명확하게 작성 (마침표 제외, 개조식 서술)
  - Body: 최소 작업 단위(Atomic Commit) 커밋을 기본으로 하되, 부득이한 배경 설명이 필요한 경우 한글로 본문 추가.
- Examples:
  - `feat(auth): 카카오 소셜 로그인 연동`
  - `fix(order): 재고 차감 시 동시성 이슈로 인한 음수 재고 버그 수정`
  - `refactor(user): 레거시 회원 조회 쿼리 QueryDSL로 전환`

## 2. Code Comments Convention
- 언어: 한글로 작성.
- 스타일: 실무형 주석 (Professional Production-grade Comments).
- 금지 사항:
  - 코드를 가르치기 위한 튜토리얼형 주석 금지 (예: "if문으로 검사합니다", "변수를 선언합니다").
  - 단순 코드 반복 주석 금지.
  - 함수/클래스의 호출처 목록 기재 금지 (IDE 참조 기능으로 대체).
  - 이미 코드 시그니처/타입 힌트에 명시된 단순 타입명 나열 지양.
- 필수 작성 대상:
  - **Why**: 특정 알고리즘, 라이브러리, 회피책을 선택한 비즈니스/기술적 이유.
  - **Constraints**: 파라미터의 도메인 제약조건 (허용 범위, 단위, null 처리 정책 등).
  - **Side-effects / Edge-cases**: 부작용, 외부 의존성 주의사항, 예외 발생 조건.

## 3. General Principles
- 불필요한 이모지 사용 금지.
- 가독성과 코드 자체의 자기 서술성(Self-describing code)을 최우선으로 유지.
