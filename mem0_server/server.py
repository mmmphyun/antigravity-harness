import os
import sys
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from mcp.server.mcpserver import MCPServer

# 메모리 데이터베이스 저장 경로
DB_DIR = os.path.expanduser("~/.mem0")
DB_PATH = os.path.join(DB_DIR, "memories.db")

os.makedirs(DB_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 메인 메모리 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        metadata TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # 2. FTS5 전문 검색 가상 테이블 생성
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        id UNINDEXED,
        content,
        category,
        metadata
    )
    """)
    
    # 3. FTS 동기화 트리거 설정
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
        INSERT INTO memories_fts(id, content, category, metadata)
        VALUES (new.id, new.content, new.category, new.metadata);
    END;
    """)
    
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
        DELETE FROM memories_fts WHERE id = old.id;
    END;
    """)
    
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
        DELETE FROM memories_fts WHERE id = old.id;
        INSERT INTO memories_fts(id, content, category, metadata)
        VALUES (new.id, new.content, new.category, new.metadata);
    END;
    """)
    
    conn.commit()
    conn.close()

init_db()

server = MCPServer("mem0-local")

@server.tool()
def add_memory(content: str, category: str = "general", metadata: Optional[Dict[str, Any]] = None) -> str:
    """새로운 장기 기억(선호도, 프로젝트 컨텍스트, 결정사항 등)을 저장합니다."""
    if not content or not content.strip():
        return json.dumps({"error": "Content cannot be empty"}, ensure_ascii=False)
    
    clean_content = content.strip()
    clean_category = (category or "general").strip().lower()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    now_iso = datetime.now(timezone.utc).isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 동일 내용 존재 여부 확인
    cursor.execute("SELECT id FROM memories WHERE content = ? AND category = ?", (clean_content, clean_category))
    row = cursor.fetchone()
    
    if row:
        mem_id = row[0]
        cursor.execute(
            "UPDATE memories SET metadata = ?, updated_at = ? WHERE id = ?",
            (meta_json, now_iso, mem_id)
        )
        msg = f"Memory updated (id: {mem_id})"
    else:
        mem_id = str(uuid.uuid4())[:8]
        cursor.execute(
            "INSERT INTO memories (id, content, category, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (mem_id, clean_content, clean_category, meta_json, now_iso, now_iso)
        )
        msg = f"Memory added (id: {mem_id})"
    
    conn.commit()
    conn.close()
    
    return json.dumps({
        "status": "success",
        "message": msg,
        "memory": {
            "id": mem_id,
            "content": clean_content,
            "category": clean_category,
            "metadata": metadata or {},
            "updated_at": now_iso
        }
    }, ensure_ascii=False, indent=2)

@server.tool()
def search_memory(query: str, category: Optional[str] = None, limit: int = 5) -> str:
    """저장된 기억을 키워드 및 전문 검색(FTS5)으로 조회합니다."""
    if not query or not query.strip():
        return json.dumps({"results": []})
    
    clean_query = query.strip()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    results = []
    # 1. FTS5 검색 시도
    try:
        # 특수문자 제거 후 AND 조건 연결
        safe_words = [w for w in clean_query.split() if w.isalnum() or len(w) > 1]
        fts_query = " ".join(safe_words)
        
        if fts_query:
            if category:
                cursor.execute("""
                SELECT m.id, m.content, m.category, m.metadata, m.updated_at
                FROM memories_fts f
                JOIN memories m ON f.id = m.id
                WHERE memories_fts MATCH ? AND m.category = ?
                ORDER BY rank
                LIMIT ?
                """, (fts_query, category.strip().lower(), limit))
            else:
                cursor.execute("""
                SELECT m.id, m.content, m.category, m.metadata, m.updated_at
                FROM memories_fts f
                JOIN memories m ON f.id = m.id
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """, (fts_query, limit))
            
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "id": r[0],
                    "content": r[1],
                    "category": r[2],
                    "metadata": json.loads(r[3]),
                    "updated_at": r[4]
                })
    except Exception:
        results = []
    
    # 2. FTS 결과가 없을 경우 LIKE 폴백 검색
    if not results:
        like_pattern = f"%{clean_query}%"
        if category:
            cursor.execute("""
            SELECT id, content, category, metadata, updated_at
            FROM memories
            WHERE (content LIKE ? OR metadata LIKE ?) AND category = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """, (like_pattern, like_pattern, category.strip().lower(), limit))
        else:
            cursor.execute("""
            SELECT id, content, category, metadata, updated_at
            FROM memories
            WHERE content LIKE ? OR metadata LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """, (like_pattern, like_pattern, limit))
            
        for r in cursor.fetchall():
            results.append({
                "id": r[0],
                "content": r[1],
                "category": r[2],
                "metadata": json.loads(r[3]),
                "updated_at": r[4]
            })
    
    conn.close()
    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)

@server.tool()
def get_all_memories(category: Optional[str] = None, limit: int = 50) -> str:
    """저장된 전체 기억 목록을 최신순으로 가져옵니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
        SELECT id, content, category, metadata, updated_at
        FROM memories
        WHERE category = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """, (category.strip().lower(), limit))
    else:
        cursor.execute("""
        SELECT id, content, category, metadata, updated_at
        FROM memories
        ORDER BY updated_at DESC
        LIMIT ?
        """, (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    
    results = [
        {
            "id": r[0],
            "content": r[1],
            "category": r[2],
            "metadata": json.loads(r[3]),
            "updated_at": r[4]
        }
        for r in rows
    ]
    
    return json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2)

@server.tool()
def delete_memory(memory_id: str) -> str:
    """지정된 ID의 기억을 삭제합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id.strip(),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        return json.dumps({"status": "success", "message": f"Memory {memory_id} deleted."})
    return json.dumps({"status": "not_found", "message": f"Memory {memory_id} not found."})

@server.tool()
def clear_memories(category: Optional[str] = None) -> str:
    """저장된 기억을 초기화합니다. category 지정 시 해당 카테고리만 삭제합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if category:
        cursor.execute("DELETE FROM memories WHERE category = ?", (category.strip().lower(),))
    else:
        cursor.execute("DELETE FROM memories")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return json.dumps({"status": "success", "message": f"Cleared {count} memories."})

if __name__ == "__main__":
    server.run(transport="stdio")
