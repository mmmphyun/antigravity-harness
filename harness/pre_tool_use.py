import json
import re
import shlex
import sys

import state_manager

# Windows 콘솔/파이프 UTF-8 인코딩 보장
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

COMMIT_REGEX = re.compile(
    r"^(feat|fix|refactor|docs|chore|test|style|perf|build|ci)(\([a-zA-Z0-9_\-\./]+\))?:\s+(.+)$"
)
KOREAN_CHAR_REGEX = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")


def parse_commit_message(command_line: str) -> str:
    """CLI 인자에서 커밋 메시지 본문을 안전하게 추출"""
    try:
        tokens = shlex.split(command_line)
        messages = []
        for i, token in enumerate(tokens):
            if token in ("-m", "--message") and i + 1 < len(tokens):
                messages.append(tokens[i + 1])
        return "\n".join(messages) if messages else ""
    except Exception:
        match = re.search(r'(?:-m|--message)\s+["\']([^"\']+)["\']', command_line)
        return match.group(1) if match else ""


def check_dangerous_command(command_line: str) -> tuple[bool, str]:
    cmd_lower = command_line.lower()

    # 1. 시스템 폴더 파괴 및 루트 삭제 차단
    if re.search(r"rmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\?(windows|program files|users\\[^\\]+$)", cmd_lower):
        return True, "시스템 주요 디렉터리 삭제 명령이 차단되었습니다."
    if "rm -rf /" in cmd_lower or "rm -rf /*" in cmd_lower:
        return True, "루트 디렉터리 전체 삭제 명령이 차단되었습니다."

    # 2. 강제 푸시 차단
    if re.search(r"git\s+push\s+.*(--force|-f\b)", cmd_lower):
        return True, "원격 저장소 강제 푸시(force push) 명령이 차단되었습니다."

    return False, ""


def check_infra_mutation(command_line: str) -> tuple[bool, str]:
    cmd_lower = command_line.lower().strip()

    # Docker 인프라 변경
    if cmd_lower.startswith("docker ") or cmd_lower.startswith("docker.exe "):
        if any(
            action in cmd_lower
            for action in [" rm ", " rmi ", " stop ", " kill ", " system prune", " volume rm"]
        ):
            return True, f"Docker 리소스 변경/삭제 작업 승인 요청: {command_line}"

    # GCP gcloud 인프라 변경/삭제/배포
    if cmd_lower.startswith("gcloud ") or cmd_lower.startswith("gcloud.cmd "):
        if any(action in cmd_lower for action in [" delete", " deploy", " create", " update", " apply"]):
            return True, f"GCP 클라우드 리소스 변경/배포 작업 승인 요청: {command_line}"

    # K8s kubectl 인프라 변경
    if cmd_lower.startswith("kubectl ") or cmd_lower.startswith("kubectl.exe "):
        if any(action in cmd_lower for action in [" delete", " apply", " patch", " edit", " scale"]):
            return True, f"Kubernetes 클러스터 리소스 변경 작업 승인 요청: {command_line}"

    # AWS CLI 변경
    if cmd_lower.startswith("aws ") or cmd_lower.startswith("aws.cmd "):
        if any(action in cmd_lower for action in [" delete-", " terminate-", " create-", " put-", " apply"]):
            return True, f"AWS 리소스 변경 작업 승인 요청: {command_line}"

    return False, ""


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({}, ensure_ascii=False))
            return

        payload = json.loads(raw_input)
        conv_id = payload.get("conversationId", "unknown")
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        if tool_name == "run_command":
            cmd_line = args.get("CommandLine", "")

            # 1. 치명적 위험 명령어 검사 (하드 차단)
            is_dangerous, reason = check_dangerous_command(cmd_line)
            if is_dangerous:
                state_manager.log_event("DANGEROUS_CMD_BLOCKED", conv_id, reason, cmd_line)
                print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
                return

            # 2. 커밋 메시지 컨벤션 검사 (하드 차단)
            if re.search(r"\bgit\s+commit\b", cmd_line):
                commit_msg = parse_commit_message(cmd_line)
                if commit_msg:
                    first_line = commit_msg.strip().split("\n")[0]
                    match = COMMIT_REGEX.match(first_line)
                    has_korean = bool(KOREAN_CHAR_REGEX.search(first_line))

                    if not match or not has_korean:
                        reason = (
                            "커밋 메시지 컨벤션 위반:\n"
                            "- 형식: <type>(<scope>): <한글 요약> (예: feat(auth): 카카오 소셜 로그인 연동)\n"
                            "- 타입: feat, fix, refactor, docs, chore, test, style, perf 등 영문 소문자\n"
                            "- 제목: 한글로 명확하게 작성 (마침표 제외)"
                        )
                        state_manager.log_event(
                            "COMMIT_CONVENTION_BLOCKED", conv_id, "비규격 커밋 메시지 차단", first_line
                        )
                        print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
                        return

            # 3. 인프라 변경 작업 검사 (사용자 승인 요청)
            needs_approval, approve_reason = check_infra_mutation(cmd_line)
            if needs_approval:
                state_manager.log_event("INFRA_APPROVAL_REQUESTED", conv_id, approve_reason)
                print(json.dumps({"decision": "ask", "reason": approve_reason}, ensure_ascii=False))
                return

        print(json.dumps({}, ensure_ascii=False))

    except Exception as e:
        try:
            state_manager.log_event("PRE_TOOL_USE_ERROR", "system", f"Fail-open triggered: {e!s}")
        except Exception:
            pass
        print(json.dumps({}, ensure_ascii=False))


if __name__ == "__main__":
    main()
