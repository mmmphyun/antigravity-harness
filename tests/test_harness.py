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
        for cmd in ["git add .", "git add -A", "git add --all", "git add *", "git add -u"]:
            is_blocked, _ = pre_tool_use.check_wildcard_staging(cmd)
            self.assertTrue(is_blocked, f"Failed to block: {cmd}")

        for cmd in [
            'git commit -a -m "feat: test"',
            'git commit -am "fix: test"',
            'git commit --all -m "feat: test"',
        ]:
            is_blocked, _ = pre_tool_use.check_wildcard_staging(cmd)
            self.assertTrue(is_blocked, f"Failed to block: {cmd}")

        is_blocked, _ = pre_tool_use.check_wildcard_staging("git add src/user.py tests/test_user.py")
        self.assertFalse(is_blocked)

    def test_backslash_git_paths_blocking(self):
        # 1. git add에 백슬래시 포함된 경로 차단
        is_blocked, _ = pre_tool_use.check_backslash_git_paths("git add src\\auth\\jwt.py")
        self.assertTrue(is_blocked)

        is_blocked, _ = pre_tool_use.check_backslash_git_paths("git add -v .\\tests\\test.py")
        self.assertTrue(is_blocked)

        # 2. 포워드 슬래시 경로는 정상 통과
        is_blocked, _ = pre_tool_use.check_backslash_git_paths("git add src/auth/jwt.py tests/test.py")
        self.assertFalse(is_blocked)

        # 3. git add가 아닌 명령어나 커밋 메시지 본문은 영향 없음
        is_blocked, _ = pre_tool_use.check_backslash_git_paths('git commit -m "fix: \\n bug"')
        self.assertFalse(is_blocked)

    def test_dirty_push_check(self):
        is_dirty, _ = pre_tool_use.check_dirty_push("git status", ".")
        self.assertFalse(is_dirty)

        is_dirty, _ = pre_tool_use.check_dirty_push("git push origin main", "C:\\non_existent_dir_12345")
        self.assertFalse(is_dirty)

    def test_commit_convention_parsing(self):
        msg = "feat(auth): 카카오 소셜 로그인 연동"
        match = pre_tool_use.COMMIT_REGEX.match(msg)
        has_korean = bool(pre_tool_use.KOREAN_CHAR_REGEX.search(msg))
        self.assertTrue(match)
        self.assertTrue(has_korean)

        msg_invalid = "fix(order): fix inventory concurrency issue"
        match = pre_tool_use.COMMIT_REGEX.match(msg_invalid)
        has_korean = bool(pre_tool_use.KOREAN_CHAR_REGEX.search(msg_invalid))
        self.assertTrue(match)
        self.assertFalse(has_korean)

        msg_bad = "just update code"
        match = pre_tool_use.COMMIT_REGEX.match(msg_bad)
        self.assertFalse(match)

    def test_infra_mutation_check(self):
        needs_ask, _ = pre_tool_use.check_infra_mutation("docker rm -f my-app")
        self.assertTrue(needs_ask)

        needs_ask, _ = pre_tool_use.check_infra_mutation("docker ps -a")
        self.assertFalse(needs_ask)

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
