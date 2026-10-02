"""Record whose turn it is for the rebar status page.

  turn_state.py working   UserPromptSubmit hook: the user just handed over
  turn_state.py ready     Stop hook: Claude finished and is waiting

Writes .claude/turn.json next to this folder. dashboard.py reads it and only
shows the green "Ready for human review" screen when the state is ready.
"""
import json
import sys
import time
from pathlib import Path

state = sys.argv[1] if len(sys.argv) > 1 else "ready"
target = Path(__file__).resolve().parents[1] / "turn.json"
target.write_text(json.dumps({"state": state, "t": time.time()}))
