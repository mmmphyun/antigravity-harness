# Antigravity Harness

[![Antigravity Harness CI](https://github.com/mmmphyun/antigravity-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/mmmphyun/antigravity-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google Antigravity AI 코딩 에이전트의 토큰 낭비, 반복 루프, 위험 명령어 실행을 통제하기 위한 실전 라이프사이클 훅 및 가드레일 시스템입니다.

외부 패키지 의존성 없이 파이썬 표준 라이브러리만으로 동작합니다.

---

## 1. 개발 배경 (Problem & Motivation)

AI 에이전트를 실무 개발에 자율 주행 모드로 투입하면서 실제로 마주친 병목과 비효율을 직접 통제하기 위해 만들었습니다.

- **비동기 작업 완료 대기 중 폴링 폭주**: 백그라운드 태스크 완료를 확인하려고 2-3초 간격으로 상태 조회를 연속 20회 이상 호출하여, 수백만 입력 토큰과 분당 요청 한도(RPM/TPM)를 낭비하는 문제.
- **`sleep` 명령을 통한 턴 점유**: 완료 대기를 위해 터미널에서 슬립 명령을 실행하여, 불필요하게 세션 턴을 붙잡고 대기하는 문제.
- **빅뱅 커밋 및 와일드카드 스테이징**: `git add .`나 `git commit -am`으로 검증되지 않은 파일까지 한꺼번에 올려 Git 히스토리 원자성과 `git bisect` 추적성을 깨뜨리는 문제.
- **위험 명령 실행 및 환경 파괴**: `git push --force`나 루트 경로 삭제처럼 비가역적인 파괴 명령을 사전 확인 없이 실행하는 문제.

---

## 2. 주요 기능 (Features)

### 사전 도구 실행 제어 (`PreToolUse` Guard)

도구가 실제 실행되기 전 입력 인자를 가로채 정책 위반 시 물리적으로 차단(`decision: deny`)합니다.

1. **상태 확인 폴링 방지 (Anti-Polling Guard)**
   - `manage_task(Action='status')` 호출 간격을 추적합니다.
   - 직전 호출 후 30초 이내에 다시 부르면 즉시 거부합니다.
   - 3분 동안 3회를 넘겨 조회하면 호출을 즉시 차단하고, 시스템 완료 알림(Reactive Wakeup)이 도착할 때까지 대기하게 만듭니다.

2. **슬립 대기 명령 차단 (Anti-Sleep Guard)**
   - `run_command`에서 `sleep` 또는 `Start-Sleep` 단독 실행을 탐지하여 즉시 막습니다.
   - 프로세스 종료 시그널에 반응하는 비동기 대기 방식을 강제합니다.

3. **원자적 커밋 유도 (`atomic-commits` 연동)**
   - 와일드카드 스테이징(`git add .`, `-A`, `--all`, `*`) 및 자동 커밋(`git commit -a`)을 전면 차단합니다.
   - 수정한 파일 경로를 개별적으로 지정해 스테이징하도록 요구합니다.

4. **커밋 메시지 컨벤션 검증**
   - `<type>(<scope>): <한글 요약>` 정규식 형식을 강제합니다.
   - 규격에 맞지 않는 메시지는 커밋 실행 단계에서 거절합니다.

5. **치명적 명령어 및 백슬래시 경로 차단**
   - `git push --force`, 루트/시스템 디렉터리 삭제 명령을 원천 차단합니다.
   - Git 및 GitHub CLI 명령어 내 백슬래시(`\`) 경로 입력을 막고 웹 표준 포워드 슬래시(`/`)를 강제합니다.

### 사후 검증 및 서킷 브레이커 (`Stop Validator`)

에이전트가 작업을 마치고 종료(`Stop`)를 선언할 때 작업 결과물을 자동 검증합니다.

1. **빌드 및 테스트 자동 감지**
   - 프로젝트 루트 설정을 읽어 Python(`pytest`, `uv`, `poetry`) 및 Java(`gradlew`) 테스트를 자동 실행합니다.
2. **에러 로그 압축 (Log Truncation)**
   - 테스트 실패 시 하위 15줄의 핵심 에러 로그만 에이전트에 전달하여 다음 턴의 컨텍스트 윈도우 오염을 방지합니다.
3. **서킷 브레이커 (Circuit Breaker)**
   - 동일 세션에서 테스트 수정 시도가 3회 연속 실패하면 무한 루프를 끊고 정상 종료한 뒤 사용자 개입을 요청합니다.

---

## 3. 프로젝트 구조

```text
antigravity-harness/
├── .github/
│   └── workflows/
│       └── ci.yml             # 멀티 OS(Ubuntu, Windows, macOS) 및 Python 버전 테스트
├── harness/
│   ├── pre_tool_use.py        # 사전 차단 및 실행 가드레일
│   ├── stop_validator.py      # 빌드/테스트 자동 실행 및 서킷 브레이커
│   ├── post_tool_use.py       # 사후 도구 실행 훅
│   └── state_manager.py       # 세션 격리 상태 및 호출 빈도 추적
├── skills/
│   └── atomic-commits/        # 1-Task 1-Commit 원자적 분할 프로토콜
├── tests/
│   └── test_harness.py        # 가드레일 단위 테스트 (9개 케이스)
├── hooks.json                 # Antigravity 라이프사이클 훅 설정 (상대 경로)
├── LICENSE                    # MIT License
├── requirements.txt           # 외부 의존성 없음 (표준 라이브러리)
└── README.md
```

---

## 4. 설치 및 적용 방법

### 1. 저장소 클론
```bash
git clone https://github.com/mmmphyun/antigravity-harness.git
```

### 2. Antigravity 설정 디렉터리에 연결
Antigravity 전역 설정 디렉터리(`~/.gemini/config/`)에 `harness/`, `hooks.json`을 복사하거나 디렉터리 정션(Junction)으로 연결합니다.

- **Windows PowerShell**:
```powershell
$TargetDir = "$env:USERPROFILE\.gemini\config"
if (!(Test-Path $TargetDir)) { New-Item -ItemType Directory -Path $TargetDir -Force }

New-Item -ItemType Junction -Path "$TargetDir\harness" -Target ".\harness"
Copy-Item ".\hooks.json" -Destination "$TargetDir\hooks.json" -Force
```

---

## 5. 라이선스

MIT License
