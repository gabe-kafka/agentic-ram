"""PreToolUse hook: auto-approve the RAM Concept mesh/calc helper.

Approves only a single, unchained shell command that runs
ram-concept/skills/run-ram-concept-mesh-calc/scripts/run-mesh-calc.(ps1|cmd).
Everything else falls through to the normal permission flow.
"""
import json
import re
import sys

SCRIPT = re.compile(
    r"ram-concept/skills/run-ram-concept-mesh-calc/scripts/run-mesh-calc\.(ps1|cmd)\b",
    re.IGNORECASE,
)
CHAINING = re.compile(r"[;&|`\n\r<>]|\$\(")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return
    command = str(payload.get("tool_input", {}).get("command", ""))
    normalized = command.replace("\\", "/")
    if not SCRIPT.search(normalized) or CHAINING.search(command):
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "RAM Concept mesh/calc helper (user-approved)",
        }
    }))


if __name__ == "__main__":
    main()
