import json
import os
import re
import shlex
import subprocess
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

# 대량 파일 수정이 정당화되는 예외 커밋 스코프/타입
BULK_COMMIT_EXEMPTIONS = (
    "chore(init):",
    "chore(deps):",
    "style(format):",
    "refactor(arch):",
    "refactor(reorganize):",
)

WILDCARD_ADD_REGEX = re.compile(r"\bgit\s+add\b\s+(?:.*?\s+)?(\.|\-A|\-\-all|\*|\-u)(?:\s|$)")
AUTO_COMMIT_REGEX = re.compile(r"\bgit\s+commit\b\s+.*(-[a-zA-Z]*a[a-zA-Z]*|--all\b)")


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
    if re.search(
        r"rmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\?(windows|program files|users\\[^\\]+$)", cmd_lower
    ):
        return True, "시스템 주요 디렉터리 삭제 명령이 차단되었습니다."
    if "rm -rf /" in cmd_lower or "rm -rf /*" in cmd_lower:
        return True, "루트 디렉터리 전체 삭제 명령이 차단되었습니다."

    # 2. 강제 푸시 차단
    if re.search(r"git\s+push\s+.*(--force|-f\b)", cmd_lower):
        return True, "원격 저장소 강제 푸시(force push) 명령이 차단되었습니다."

    return False, ""


def check_wildcard_staging(command_line: str) -> tuple[bool, str]:
    """atomic-commits 원칙: 와일드카드 git add 및 git commit -a 차단"""
    if WILDCARD_ADD_REGEX.search(command_line):
        return (
            True,
            "와일드카드 스테이징(git add ., -A, --all, *)은 atomic-commits 원칙에 의해 차단되었습니다.\n"
            "변경 파일을 핀포인트로 개별 명시하세요 (예: git add <file1> <file2>).",
        )

    if AUTO_COMMIT_REGEX.search(command_line):
        return (
            True,
            "자동 스테이징 커밋(git commit -a, -am)은 atomic-commits 원칙에 의해 차단되었습니다.\n"
            "먼저 대상 파일을 개별 명시하여 git add한 후 커밋하세요.",
        )

    return False, ""


def check_backslash_git_paths(command_line: str) -> tuple[bool, str]:
    r"""Git add 명령어의 파일 경로 인자에서 백슬래시(\\) 사용 차단"""
    if not re.search(r"\bgit\s+add\b", command_line):
        return False, ""
    try:
        tokens = shlex.split(command_line, posix=False)
    except Exception:
        tokens = command_line.split()

    is_add = False
    for t in tokens:
        if t == "add":
            is_add = True
            continue
        if is_add:
            if t.startswith("-"):
                continue
            if "\\" in t:
                return (
                    True,
                    f"Git 경로 인자에 백슬래시(\\)가 포함되어 차단되었습니다: '{t}'\n"
                    "웹 표준 포워드 슬래시(/)를 사용하세요 (예: git add path/to/file).",
                )
    return False, ""


def check_dirty_push(command_line: str, cwd: str) -> tuple[bool, str]:
    """워킹 트리에 미커밋 변경사항이 남아있는 상태에서 git push 차단"""
    if not re.search(r"\bgit\s+push\b", command_line):
        return False, ""

    try:
        if cwd and not os.path.isdir(cwd):
            return False, ""
        run_cwd = cwd if cwd else None
        result = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            cwd=run_cwd,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
        )
        if result.returncode == 0:
            dirty_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if dirty_files:
                sample_files = ", ".join(dirty_files[:3])
                if len(dirty_files) > 3:
                    sample_files += f" 외 {len(dirty_files) - 3}개"
                return (
                    True,
                    f"커밋되지 않은 로컬 변경사항({len(dirty_files)}개: {sample_files})이 남아있어 푸시가 차단되었습니다.\n"
                    "모든 변경사항을 원자적으로 커밋한 후 푸시하세요.",
                )
    except Exception:
        # fail-open
        pass

    return False, ""


def check_staged_file_count(cwd: str, commit_msg: str, threshold: int = 4) -> tuple[bool, str]:
    """스테이징된 파일 수가 임계치를 초과할 경우 승인(ask) 요구"""
    first_line = commit_msg.strip().split("\n")[0] if commit_msg else ""
    if any(first_line.startswith(prefix) for prefix in BULK_COMMIT_EXEMPTIONS):
        return False, ""

    try:
        run_cwd = cwd if cwd and os.path.isdir(cwd) else None
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=run_cwd,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
        )
        if result.returncode == 0:
            staged_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            count = len(staged_files)
            if count > threshold:
                sample_files = ", ".join(staged_files[:3])
                if count > 3:
                    sample_files += f" 외 {count - 3}개"
                return (
                    True,
                    f"스테이징된 파일 수({count}개: {sample_files})가 atomic-commits 권장 상한선({threshold}개)을 초과했습니다.\n"
                    "빅뱅 커밋을 계속 진행하시겠습니까?",
                )
    except Exception:
        # fail-open
        pass

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
        if any(
            action in cmd_lower for action in [" delete", " deploy", " create", " update", " apply"]
        ):
            return True, f"GCP 클라우드 리소스 변경/배포 작업 승인 요청: {command_line}"

    # K8s kubectl 인프라 변경
    if cmd_lower.startswith("kubectl ") or cmd_lower.startswith("kubectl.exe "):
        if any(
            action in cmd_lower for action in [" delete", " apply", " patch", " edit", " scale"]
        ):
            return True, f"Kubernetes 클러스터 리소스 변경 작업 승인 요청: {command_line}"

    # AWS CLI 변경
    if cmd_lower.startswith("aws ") or cmd_lower.startswith("aws.cmd "):
        if any(
            action in cmd_lower
            for action in [" delete-", " terminate-", " create-", " put-", " apply"]
        ):
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
            cwd = args.get("Cwd", "")

            # 1. 치명적 위험 명령어 검사 (하드 차단)
            is_dangerous, reason = check_dangerous_command(cmd_line)
            if is_dangerous:
                state_manager.log_event("DANGEROUS_CMD_BLOCKED", conv_id, reason, cmd_line)
                print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
                return

            # 2. 와일드카드 스테이징 및 git commit -a 차단 (atomic-commits)
            is_wildcard, wildcard_reason = check_wildcard_staging(cmd_line)
            if is_wildcard:
                state_manager.log_event("WILDCARD_STAGING_BLOCKED", conv_id, wildcard_reason, cmd_line)
                print(json.dumps({"decision": "deny", "reason": wildcard_reason}, ensure_ascii=False))
                return

            # 3. Git add 경로 인자 백슬래시 사용 차단 (포워드 슬래시 강제)
            is_backslash, backslash_reason = check_backslash_git_paths(cmd_line)
            if is_backslash:
                state_manager.log_event("BACKSLASH_GIT_PATH_BLOCKED", conv_id, backslash_reason, cmd_line)
                print(json.dumps({"decision": "deny", "reason": backslash_reason}, ensure_ascii=False))
                return

            # 4. 워킹 트리 오염(Dirty Tree) 상태에서 git push 차단
            is_dirty_push, dirty_reason = check_dirty_push(cmd_line, cwd)
            if is_dirty_push:
                state_manager.log_event("DIRTY_PUSH_BLOCKED", conv_id, dirty_reason, cmd_line)
                print(json.dumps({"decision": "deny", "reason": dirty_reason}, ensure_ascii=False))
                return

            # 5. 커밋 메시지 컨벤션 검사 (하드 차단) 및 대량 커밋 검사
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
                            "COMMIT_CONVENTION_BLOCKED",
                            conv_id,
                            "비규격 커밋 메시지 차단",
                            first_line,
                        )
                        print(
                            json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False)
                        )
                        return

                # 6. 스테이징 파일 수 초과 검사 (ask)
                is_bulk, bulk_reason = check_staged_file_count(cwd, commit_msg)
                if is_bulk:
                    state_manager.log_event("BULK_COMMIT_APPROVAL_REQUESTED", conv_id, bulk_reason, cmd_line)
                    print(json.dumps({"decision": "ask", "reason": bulk_reason}, ensure_ascii=False))
                    return

            # 7. 인프라 변경 작업 검사 (사용자 승인 요청)
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

