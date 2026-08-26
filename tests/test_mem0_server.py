import json
import os
import sys
import unittest

# mem0_server 디렉터리를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mem0_server")))

import server


class TestMem0Server(unittest.TestCase):
    def test_mem0_crud_operations(self):
        # 1. 메모리 추가
        add_res = server.add_memory(
            "CI test memory content", category="ci-test", metadata={"env": "test"}
        )
        data = json.loads(add_res)
        self.assertEqual(data.get("status"), "success")
        mem_id = data["memory"]["id"]

        # 2. 메모리 검색
        search_res = server.search_memory("CI test")
        search_data = json.loads(search_res)
        self.assertGreaterEqual(search_data.get("count", 0), 1)

        # 3. 메모리 목록 조회
        list_res = server.get_all_memories(category="ci-test")
        list_data = json.loads(list_res)
        self.assertGreaterEqual(list_data.get("count", 0), 1)

        # 4. 메모리 삭제
        del_res = server.delete_memory(mem_id)
        del_data = json.loads(del_res)
        self.assertEqual(del_data.get("status"), "success")


if __name__ == "__main__":
    unittest.main()
