#!/usr/bin/env python3
"""Live status page for simplify_rebar work folders.

Read-only: it scans the per-layer work folders under --root (base.cpt,
plan-N.json, round-N.cpt, events.jsonl) and serves one page that polls
/status. It never talks to Concept.

  python dashboard.py --root <job>/ram-concept/rebar-simplify --port 8765
"""

from __future__ import annotations

import argparse
import ctypes
import json
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cpt_reader as cr
import rebar_groups as rg
import simplify_rebar as sr

LAYERS = ["bot-long", "bot-lat", "top-long", "top-lat"]
PAGE = Path(__file__).with_name("dashboard.html")
_cache: dict = {}


def cached(key, path: Path, build):
    stamp = (key, str(path), path.stat().st_mtime_ns)
    if stamp not in _cache:
        _cache[stamp] = build()
    return _cache[stamp]


def concept_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Concept.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "concept.exe" in out.lower()


def alive(pid: int) -> bool:
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # query limited information
    if not handle:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(handle)
    return code.value == 259                                          # STILL_ACTIVE


def working(root: Path) -> dict | None:
    """The newest work-folder marker whose process is still running."""
    live = []
    for marker in root.glob("*/.working"):
        try:
            info = json.loads(marker.read_text())
        except (ValueError, OSError):
            continue
        if alive(info["pid"]):
            live.append(info)
    return max(live, key=lambda i: i["t"], default=None)


def numbered(folder: Path, prefix: str, ext: str) -> int:
    nums = [int(m.group(1)) for p in folder.glob(f"{prefix}-*.{ext}")
            if (m := re.fullmatch(rf"{prefix}-(\d+)\.{ext}", p.name))]
    return max(nums, default=0)


def program_summary(path: Path, layer: cr.Layer, s: rg.Settings) -> dict:
    bars = cr.bars(path, layer, cr.PROGRAM)
    peaks = [d for d in bars if rg.is_peak(d, s)]
    tons = lambda ds: round(sum(d.count * d.length * rg.BAR_WEIGHT[d.size] for d in ds) / 2000, 2)
    return dict(groups=len(bars), real=len(bars) - len(peaks), peaking=len(peaks),
                tons=tons(bars), peaking_tons=tons(peaks))


def options_table(base: Path, layer: cr.Layer) -> list[dict]:
    demands = cr.bars(base, layer, cr.PROGRAM)
    s = rg.Settings(size=cr.dominant_size(demands))
    real = [d for d in demands if not rg.is_peak(d, s)]
    return [dict(n=i, groups=p["groups"], tons=p["tons"], budget_lb=p["budget_lb"])
            for i, p in enumerate(rg.options(real, s), 1)]


def events(folder: Path, last: int = 8) -> list[dict]:
    path = folder / "events.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines()[-last:]:
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def layer_status(name: str, folder: Path | None, running: bool) -> dict:
    out = dict(layer=name, folder=folder.name if folder else None, state="not started", events=[])
    if folder is None:
        return out
    layer = cr.Layer.parse(name)
    base = folder / "base.cpt"
    plan_n, round_n = numbered(folder, "plan", "json"), numbered(folder, "round", "cpt")
    out["events"] = events(folder)
    if base.exists():
        out["state"] = "baseline done"
        out["program"] = cached("program", base, lambda: program_summary(base, layer, rg.Settings()))
        out["options"] = cached("options", base, lambda: options_table(base, layer))
    if plan_n:
        state = json.loads((folder / f"plan-{plan_n}.json").read_text())
        s = sr.settings_of(state)
        groups = [rg.from_dict(g) for g in state["groups"]]
        out["plan"] = dict(n=plan_n, groups=len(groups), tons=round(sr.tons_of(groups, s), 1),
                           size=s.size, budget_lb=state["budget_lb"])
        out["state"] = "option chosen"
        if round_n:
            path = folder / f"round-{round_n}.cpt"
            out["round"] = dict(n=round_n, saved=path.stat().st_mtime,
                                **cached("round", path, lambda: program_summary(path, layer, s)))
        if round_n < plan_n:
            started = (folder / f"plan-{plan_n}.json").stat().st_mtime
            out["state"] = "calculating" if running else "plan written, not calculated"
            out["since"] = started
        elif out["round"]["real"]:
            out["state"] = "real leftovers"
        else:
            out["state"] = "done"
    return out


def status(root: Path) -> dict:
    running = concept_running()
    newest: dict[str, Path] = {}
    for plan in root.glob("*/plan-1.json"):
        try:
            name = json.loads(plan.read_text())["layer"]
        except (ValueError, KeyError):
            continue
        folder = plan.parent
        latest = max(p.stat().st_mtime for p in folder.iterdir())
        if name not in newest or latest > max(p.stat().st_mtime for p in newest[name].iterdir()):
            newest[name] = folder
    for name in LAYERS:                      # a folder with only base.cpt, named after its layer
        if name not in newest and (root / name / "base.cpt").exists():
            newest[name] = root / name
    layers = []
    for name in LAYERS:
        try:
            layers.append(layer_status(name, newest.get(name), running))
        except Exception as error:           # a file mid-save; show it and retry on the next poll
            layers.append(dict(layer=name, folder=newest[name].name, state="reading", error=str(error)[:200], events=[]))
    busy = working(root)
    recent = max((e for l in layers for e in l["events"]), key=lambda e: e["t"], default=None)
    return dict(now=time.time(), root=str(root), concept_running=running, layers=layers,
                state="working" if busy else "ready", busy=busy, last=recent)


class Handler(BaseHTTPRequestHandler):
    root: Path

    def do_GET(self):
        if self.path.startswith("/status"):
            body, kind = json.dumps(status(self.root)).encode(), "application/json"
        else:
            body, kind = PAGE.read_bytes(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", required=True, type=Path, help="folder holding the per-layer work folders")
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    Handler.root = a.root.resolve()
    print(f"rebar dashboard on http://localhost:{a.port}  root={Handler.root}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
