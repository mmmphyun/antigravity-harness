import json
import os
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
    session_data["history"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "retry_count": session_data["retry_count"],
        }
    )
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
