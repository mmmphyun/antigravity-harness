import sys
import json

def main():
    try:
        raw_input = sys.stdin.read()
    except Exception:
        pass
    finally:
        # PostToolUse는 항상 빈 JSON 객체 반환 규격
        print(json.dumps({}))

if __name__ == "__main__":
    main()
