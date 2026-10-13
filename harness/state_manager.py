import os
import json
import time
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "harness.log")

def _load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_retry_count(conv_id: str) -> int:
    state = _load_state()
    return state.get(conv_id, {}).get("retry_count", 0)

def increment_retry_count(conv_id: str, reason: str, details: str = "") -> int:
    state = _load_state()
    session_data = state.get(conv_id, {"retry_count": 0, "history": []})
    session_data["retry_count"] += 1
    session_data["last_updated"] = datetime.now().isoformat()
    session_data["history"].append({
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "retry_count": session_data["retry_count"]
    })
    state[conv_id] = session_data
    _save_state(state)
    
    log_event("RETRY_INCREMENT", conv_id, reason, details)
    return session_data["retry_count"]

def reset_retry_count(conv_id: str):
    state = _load_state()
    if conv_id in state:
        state[conv_id]["retry_count"] = 0
        state[conv_id]["last_updated"] = datetime.now().isoformat()
        _save_state(state)

def log_event(event_type: str, conv_id: str, message: str, details: str = ""):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] [Session: {conv_id}] {message}\n"
        if details:
            log_entry += f"  Details: {details}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass


def check_task_status_rate_limit(conv_id: str, task_id: str = "") -> tuple[bool, str]:
    state = _load_state()
    session_data = state.get(conv_id, {})
    polling_info = session_data.get("task_polling", {"last_status_time": 0.0, "status_count": 0})

    current_time = time.time()
    last_status_time = polling_info.get("last_status_time", 0.0)
    status_count = polling_info.get("status_count", 0)

    time_diff = current_time - last_status_time
    min_interval_seconds = 30
    max_status_count_per_burst = 3
    burst_window_seconds = 180

    # 1. 최소 호출 간격 검사 (30초 미만 재호출 차단)
    if time_diff < min_interval_seconds:
        remaining = int(min_interval_seconds - time_diff)
        reason = (
            f"하네스 가드레일: 백그라운드 태스크 완료 대기를 위한 반복 폴링(manage_task Action='status')이 차단되었습니다.\n"
            f"- 직전 상태 확인 후 경과 시간: {int(time_diff)}초 (최소 간격: {min_interval_seconds}초, 남은 대기: {remaining}초)\n"
            f"- 태스크가 종료되면 시스템이 Reactive Wakeup(SYSTEM_MESSAGE)으로 자동 통지합니다.\n"
            f"- 추가 도구 호출을 중단하고 턴을 종료하여 유휴(Idle) 상태로 대기하십시오."
        )
        log_event(
            "TASK_POLLING_BLOCKED",
            conv_id,
            "반복 status 폴링 차단",
            f"TaskId: {task_id}, TimeDiff: {time_diff:.1f}s",
        )
        return False, reason

    # 2. 단기 누적 횟수 검사 (3분 윈도우 내 3회 초과 차단)
    if time_diff < burst_window_seconds:
        if status_count >= max_status_count_per_burst:
            reason = (
                f"하네스 가드레일: 단기 태스크 상태 확인 허용 횟수({max_status_count_per_burst}회)를 초과했습니다.\n"
                f"- 태스크 종료 시 시스템이 자동으로 결과를 통지하므로 추가 도구 호출을 중단하고 대기하십시오."
            )
            log_event(
                "TASK_BURST_POLLING_BLOCKED",
                conv_id,
                "버스트 status 폴링 한도 초과",
                f"TaskId: {task_id}, Count: {status_count}",
            )
            return False, reason
        new_count = status_count + 1
    else:
        new_count = 1

    polling_info["last_status_time"] = current_time
    polling_info["status_count"] = new_count
    session_data["task_polling"] = polling_info
    state[conv_id] = session_data
    _save_state(state)
    return True, ""

