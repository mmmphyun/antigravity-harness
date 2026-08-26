import json
import os
import subprocess
import sys

import state_manager

MAX_RETRIES = 3


def find_test_command(workspace_dir: str) -> list[str] | None:
    """프로젝트 루트에 존재하는 빌드/테스트 설정에 맞추어 실행 명령 감지"""
    if not workspace_dir or not os.path.exists(workspace_dir):
        return None

    # 1. Java / Gradle 프로젝트
    gradlew_bat = os.path.join(workspace_dir, "gradlew.bat")
    gradlew_sh = os.path.join(workspace_dir, "gradlew")
    if os.path.exists(gradlew_bat):
        return [gradlew_bat, "test", "--no-daemon"]
    if os.path.exists(gradlew_sh):
        return [gradlew_sh, "test", "--no-daemon"]
    if os.path.exists(os.path.join(workspace_dir, "build.gradle")) or os.path.exists(
        os.path.join(workspace_dir, "build.gradle.kts")
    ):
        return ["gradle", "test", "--no-daemon"]

    # 2. Python 프로젝트 (uv -> poetry -> pytest 순 감지)
    has_pyproject = os.path.exists(os.path.join(workspace_dir, "pyproject.toml"))
    has_tests_dir = os.path.exists(os.path.join(workspace_dir, "tests"))
    has_pytest_ini = os.path.exists(os.path.join(workspace_dir, "pytest.ini"))

    if has_pyproject or has_tests_dir or has_pytest_ini:
        if os.path.exists(os.path.join(workspace_dir, "uv.lock")):
            return ["uv", "run", "pytest", "-q"]
        if os.path.exists(os.path.join(workspace_dir, "poetry.lock")):
            return ["poetry", "run", "pytest", "-q"]
        return ["pytest", "-q"]

    return None


def truncate_error_log(output: str, max_lines: int = 15) -> str:
    """에러 로그에서 상위 핵심 라인만 추출하여 컨텍스트 오염 방지"""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def trigger_cavemem_stop(raw_payload: str):
    """cavemem 세션 종료 훅 동기화"""
    try:
        proc = subprocess.Popen(
            ["cmd.exe", "/c", "cavemem hook run stop"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        proc.communicate(input=raw_payload, timeout=5)
    except Exception:
        pass


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({}))
            return

        payload = json.loads(raw_input)
        conv_id = payload.get("conversationId", "unknown")
        workspace_paths = payload.get("workspacePaths", [])
        workspace_dir = workspace_paths[0] if workspace_paths else os.getcwd()

        # cavemem 기록 백그라운드 연동
        trigger_cavemem_stop(raw_input)

        # 1. 회로 차단기 (Circuit Breaker) 검사
        current_retries = state_manager.get_retry_count(conv_id)
        if current_retries >= MAX_RETRIES:
            state_manager.log_event(
                "CIRCUIT_BREAKER_TRIPPED",
                conv_id,
                f"최대 재시도({MAX_RETRIES}회) 초과로 회로 차단기 발동. 에이전트 종료 허용 및 사용자 인계.",
            )
            state_manager.reset_retry_count(conv_id)
            print(json.dumps({}))
            return

        # 2. 스마트 테스트 도구 탐색 및 실행
        test_cmd = find_test_command(workspace_dir)
        if not test_cmd:
            state_manager.reset_retry_count(conv_id)
            print(json.dumps({}))
            return

        # 3. 테스트 실행 (타임아웃 45초)
        try:
            res = subprocess.run(
                test_cmd,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=45,
                shell=True,
            )

            if res.returncode != 0:
                combined_output = f"{res.stdout}\n{res.stderr}".strip()
                truncated_error = truncate_error_log(combined_output, max_lines=15)

                new_retry_count = state_manager.increment_retry_count(
                    conv_id, f"테스트 실패 ({test_cmd[0]})", truncated_error
                )

                reason = (
                    f"테스트 검증 실패 (시도 {new_retry_count}/{MAX_RETRIES}회).\n"
                    f"다음 에러를 수정하세요:\n{truncated_error}"
                )
                print(json.dumps({"decision": "continue", "reason": reason}))
                return

            state_manager.reset_retry_count(conv_id)
            state_manager.log_event("TEST_PASSED", conv_id, f"테스트 성공: {' '.join(test_cmd)}")
            print(json.dumps({}))
            return

        except subprocess.TimeoutExpired:
            state_manager.log_event("TEST_TIMEOUT", conv_id, f"테스트 실행 시간 초과(45초): {' '.join(test_cmd)}")
            print(json.dumps({}))
            return
        except Exception as e:
            state_manager.log_event("TEST_EXEC_ERROR", conv_id, str(e))
            print(json.dumps({}))
            return

    except Exception as e:
        try:
            state_manager.log_event("STOP_HOOK_ERROR", "system", f"Fail-open: {e!s}")
        except Exception:
            pass
        print(json.dumps({}))


if __name__ == "__main__":
    main()
