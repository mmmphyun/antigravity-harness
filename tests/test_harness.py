import os
import sys
import unittest

# harness 디렉터리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "harness")))

import pre_tool_use
import state_manager


class TestHarness(unittest.TestCase):
    def test_dangerous_commands_blocking(self):
        is_dang, _ = pre_tool_use.check_dangerous_command("git push origin main --force")
        self.assertTrue(is_dang)

        is_dang, _ = pre_tool_use.check_dangerous_command("rm -rf /")
        self.assertTrue(is_dang)

        is_dang, _ = pre_tool_use.check_dangerous_command("git status")
        self.assertFalse(is_dang)

    def test_wildcard_staging_blocking(self):
        # 1. 와일드카드 git add 차단
        for cmd in ["git add .", "git add -A", "git add --all", "git add *", "git add -u"]:
            is_blocked, _ = pre_tool_use.check_wildcard_staging(cmd)
            self.assertTrue(is_blocked, f"Failed to block: {cmd}")

        # 2. 자동 스테이징 커밋(git commit -a) 차단
        for cmd in ["git commit -a -m \"feat: test\"", "git commit -am \"fix: test\"", "git commit --all -m \"feat: test\""]:
            is_blocked, _ = pre_tool_use.check_wildcard_staging(cmd)
            self.assertTrue(is_blocked, f"Failed to block: {cmd}")

        # 3. 정상적인 개별 파일 스테이징 통과
        is_blocked, _ = pre_tool_use.check_wildcard_staging("git add src/user.py tests/test_user.py")
        self.assertFalse(is_blocked)

    def test_commit_convention_parsing(self):
        # 1. 유효한 커밋 (한글 포함)
        msg = "feat(auth): 카카오 소셜 로그인 연동"
        match = pre_tool_use.COMMIT_REGEX.match(msg)
        has_korean = bool(pre_tool_use.KOREAN_CHAR_REGEX.search(msg))
        self.assertTrue(match)
        self.assertTrue(has_korean)

        # 2. 비규격 커밋 (영문만 작성됨)
        msg_invalid = "fix(order): fix inventory concurrency issue"
        match = pre_tool_use.COMMIT_REGEX.match(msg_invalid)
        has_korean = bool(pre_tool_use.KOREAN_CHAR_REGEX.search(msg_invalid))
        self.assertTrue(match)
        self.assertFalse(has_korean)

        # 3. 비규격 커밋 (형식 위반)
        msg_bad = "just update code"
        match = pre_tool_use.COMMIT_REGEX.match(msg_bad)
        self.assertFalse(match)

    def test_infra_mutation_check(self):
        # 1. Docker
        needs_ask, _ = pre_tool_use.check_infra_mutation("docker rm -f my-app")
        self.assertTrue(needs_ask)

        needs_ask, _ = pre_tool_use.check_infra_mutation("docker ps -a")
        self.assertFalse(needs_ask)

        # 2. GCP
        needs_ask, _ = pre_tool_use.check_infra_mutation(
            "gcloud run deploy my-api --image gcr.io/test"
        )
        self.assertTrue(needs_ask)

        needs_ask, _ = pre_tool_use.check_infra_mutation("gcloud run services list")
        self.assertFalse(needs_ask)

    def test_state_manager_retry_and_logging(self):
        session_id = "unit-test-session"
        state_manager.reset_retry_count(session_id)
        self.assertEqual(state_manager.get_retry_count(session_id), 0)

        count = state_manager.increment_retry_count(
            session_id, "Test Failure Reason", "Sample details"
        )
        self.assertEqual(count, 1)
        self.assertEqual(state_manager.get_retry_count(session_id), 1)

        state_manager.reset_retry_count(session_id)
        self.assertEqual(state_manager.get_retry_count(session_id), 0)


if __name__ == "__main__":
    unittest.main()
