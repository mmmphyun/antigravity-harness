# Antigravity Harness (Agent Guardrails)

[![Antigravity Harness CI](https://github.com/mmmphyun/antigravity-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/mmmphyun/antigravity-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google Antigravity AI 코딩 에이전트를 위한 경량 프로덕션급 가드레일, 서킷 브레이커(Circuit Breaker), 라이프사이클 훅 하네스 시스템입니다.

---

## 주요 기능

1. **사전 도구 실행 차단 (PreToolUse Guard)**
   * **위험 명령어 차단**: `git push --force`, 시스템 루트/주요 디렉터리 삭제 명령 원천 차단 (`deny`).
   * **커밋 메시지 컨벤션 검증**: `<type>(<scope>): <한글 요약>` 정규식 기반 검증, 비규격 메시지 차단 (`deny`).
   * **인프라 변경 승인 통제**: Docker, GCP, AWS, Kubernetes 리소스 변경/삭제/배포 명령 시 사용자 승인 요구 (`ask`), 조회/빌드는 자동 허용 (`allow`).

2. **사후 검증 및 스마트 테스트 (Stop Validator)**
   * **스마트 테스트 감지**: Python(`uv`/`poetry`/`pytest`), Java(`gradlew test`) 빌드 설정을 자동 감지하여 조건부 테스트 실행.
   * **에러 로그 트렁케이션**: 테스트 실패 시 상위 15줄 핵심 에러만 에이전트에 전달하여 컨텍스트 윈도우 오염 방지.
   * **회로 차단기 (Circuit Breaker)**: 세션별 최대 3회 재시도 제한 후 무한 루프 방지 및 사용자 개입 요청.

3. **영구 로깅 및 세션 격리 (`state_manager.py`)**
   * 모든 차단 이벤트, 인프라 승인 요청, 테스트 실패, 회로 차단기 발동 이력을 타임스탬프 및 세션 ID와 함께 로깅.

4. **로컬 메모리 연동 (Cavemem Bridge)**
   * 도구 완료 및 세션 정지 시 백그라운드로 `cavemem hook run`을 호출하여 관측 데이터 자동 축적.

---

## 프로젝트 구조

```text
antigravity-harness/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions 멀티 OS 테스트 파이프라인
├── harness/
│   ├── pre_tool_use.py        # 사전 차단 및 커밋/인프라 가드레일
│   ├── stop_validator.py      # 스마트 테스트 및 서킷 브레이커
│   ├── post_tool_use.py       # 사후 메모리 동기화
│   └── state_manager.py       # 세션 격리 상태 및 영구 로깅
├── tests/
│   └── test_harness.py        # 가드레일 단위 테스트
├── GEMINI.md                  # 전역 커밋/주석 컨벤션 지침
├── hooks.json                 # Antigravity 라이프사이클 훅 매핑
├── .gitignore
└── README.md
```

---

## 설치 및 적용 방법

### 1. 레포지토리 클론
```bash
git clone https://github.com/mmmphyun/antigravity-harness.git
```

### 2. Antigravity 전역 설정 디렉터리에 적용
* **Windows**: `~/.gemini/config/`
* **Linux/macOS**: `~/.gemini/config/`

`harness/`, `hooks.json`, `GEMINI.md` 파일을 `~/.gemini/config/` 경로에 복사하거나 심볼릭 링크를 연결합니다.

---

## 라이선스
MIT License
