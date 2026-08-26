import sys
import json
import subprocess

def main():
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            # cavemem post-tool-use 비동기/동기 연동
            try:
                proc = subprocess.Popen(
                    ["cmd.exe", "/c", "cavemem hook run post-tool-use"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                proc.communicate(input=raw_input, timeout=5)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        # PostToolUse는 항상 빈 JSON 객체 반환 규격
        print(json.dumps({}))

if __name__ == "__main__":
    main()
