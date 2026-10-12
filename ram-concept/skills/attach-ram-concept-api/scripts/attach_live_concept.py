#!/usr/bin/env python3
"""Attach to a running RAM Concept session through the official localhost API.

The live GUI only answers if it was started with -apiServer or
-apiServerWithGui. This script discovers that listener, wraps the already-open
model, and reports a read-only snapshot. It does not close, save, mesh, calc,
change units, or call open_file on an attached session.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
CONCEPT_INSTALL_ROOT = Path(r"C:\Program Files\Bentley\Engineering\RAM Concept")
DEFAULT_API_PORT_HINTS = (1999, 8080, 8888, 9000)
PING_TIMEOUT_SECONDS = 2.0

PORT_FLAG_RE = re.compile(r"(?:^|\s)-port(?:\s+|=)(\d+)\b", re.IGNORECASE)
WORKDIR_FLAG_RE = re.compile(r'-workdir\s+"([^"]+)"', re.IGNORECASE)
CPT_ARG_RE = re.compile(r'"([^"]+\.cpt\d*)"', re.IGNORECASE)
CPT_IN_TITLE_RE = re.compile(
    r"([A-Za-z]:[^\n\r\"<>|]+\.cpt\d*)",
    re.IGNORECASE,
)
CPT_BASENAME_RE = re.compile(r"([^\\/]+\.cpt\d*)", re.IGNORECASE)


class AttachError(RuntimeError):
    """Raised when a live Concept API session cannot be used."""


def parse_port_from_command_line(command_line: str | None) -> int | None:
    if not command_line:
        return None
    match = PORT_FLAG_RE.search(command_line)
    if not match:
        return None
    return int(match.group(1))


def python_api_dir_for_exe(exe_path: str | None) -> Path | None:
    if exe_path:
        candidate = Path(exe_path).resolve().parent / "python"
        if (candidate / "ram_concept" / "concept.py").is_file():
            return candidate
    for version_dir in sorted(CONCEPT_INSTALL_ROOT.glob("RAM Concept *"), reverse=True):
        candidate = version_dir / "python"
        if (candidate / "ram_concept" / "concept.py").is_file():
            return candidate
    return None


def parse_netstat_listeners(netstat_text: str) -> dict[int, list[int]]:
    listeners: dict[int, list[int]] = {}
    for line in netstat_text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        state = parts[3].upper()
        if state != "LISTENING":
            continue
        address = parts[1]
        port_text = address.rsplit(":", 1)[-1]
        if not port_text.isdigit():
            continue
        pid_text = parts[4]
        if not pid_text.isdigit():
            continue
        listeners.setdefault(int(pid_text), []).append(int(port_text))
    return listeners


def parse_open_cpt_from_command_line(command_line: str | None) -> str | None:
    if not command_line:
        return None
    match = CPT_ARG_RE.search(command_line)
    if not match:
        return None
    cpt = match.group(1)
    if Path(cpt).is_absolute():
        return cpt
    workdir_match = WORKDIR_FLAG_RE.search(command_line)
    if workdir_match:
        return str(Path(workdir_match.group(1)) / cpt)
    return cpt


def extract_cpt_from_title(title: str | None) -> str | None:
    if not title:
        return None
    path_match = CPT_IN_TITLE_RE.search(title)
    if path_match:
        return path_match.group(1)
    basename_match = CPT_BASENAME_RE.search(title)
    if basename_match:
        return basename_match.group(1)
    return None


def command_has_api_server(command_line: str | None) -> bool:
    if not command_line:
        return False
    lowered = command_line.lower()
    return "-apiserver" in lowered or "-apiserverwithgui" in lowered


def ping_concept_port(port: int, timeout_seconds: float = PING_TIMEOUT_SECONDS) -> str | None:
    url = f"http://localhost:{port}/"
    request = Request(
        url,
        data=b"[PING]",
        headers={
            "Content-Type": "text/plain;charset=UTF-8",
            "RequestId": "1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (OSError, URLError, TimeoutError, ValueError):
        return None
    if body.startswith("[SUCCESS][") and body.endswith("]"):
        return body[10:-1]
    return None


def _run_powershell(command: str) -> str:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AttachError(
            "PowerShell process query failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or str(completed.returncode))
        )
    return completed.stdout


def list_concept_processes() -> list[dict[str, Any]]:
    raw = _run_powershell(
        "Get-CimInstance Win32_Process -Filter \"Name = 'Concept.exe'\" | "
        "Select-Object ProcessId, ExecutablePath, CommandLine | ConvertTo-Json -Compress"
    ).strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    records = parsed if isinstance(parsed, list) else [parsed]
    processes = []
    for record in records:
        pid = int(record["ProcessId"])
        processes.append(
            {
                "pid": pid,
                "exe": record.get("ExecutablePath") or "",
                "command_line": record.get("CommandLine") or "",
                "window_titles": [],
                "listen_ports": [],
                "command_port": parse_port_from_command_line(record.get("CommandLine")),
                "started_with_api": command_has_api_server(record.get("CommandLine")),
            }
        )
    return processes


def list_window_titles_by_pid() -> dict[int, list[str]]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    IsWindowVisible = user32.IsWindowVisible

    titles: dict[int, list[str]] = {}

    def callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        length = GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        titles.setdefault(int(pid.value), []).append(title)
        return True

    EnumWindows(EnumWindowsProc(callback), 0)
    return titles


def list_listen_ports_by_pid() -> dict[int, list[int]]:
    completed = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {}
    return parse_netstat_listeners(completed.stdout)


def probe_concept_sessions() -> list[dict[str, Any]]:
    processes = list_concept_processes()
    titles = list_window_titles_by_pid()
    listeners = list_listen_ports_by_pid()
    sessions = []
    for process in processes:
        pid = process["pid"]
        window_titles = titles.get(pid, [])
        listen_ports = sorted(set(listeners.get(pid, [])))
        candidate_ports: list[int] = []
        if process["command_port"]:
            candidate_ports.append(process["command_port"])
        candidate_ports.extend(port for port in listen_ports if port not in candidate_ports)
        candidate_ports.extend(
            port for port in DEFAULT_API_PORT_HINTS if port not in candidate_ports
        )
        api_port = None
        ping = None
        for port in candidate_ports:
            ping = ping_concept_port(port)
            if ping == "PONG":
                api_port = port
                break
        sessions.append(
            {
                **process,
                "window_titles": window_titles,
                "listen_ports": listen_ports,
                "open_cpt": next(
                    (
                        extract_cpt_from_title(title)
                        for title in window_titles
                        if extract_cpt_from_title(title)
                    ),
                    None,
                )
                or parse_open_cpt_from_command_line(process.get("command_line")),
                "api_port": api_port,
                "api_ping": ping if api_port else None,
                "api_ready": api_port is not None,
                # Started with the API and showing its Scripting Server window, but not answering: the
                # server is paused (its Resume button is up) or busy with a long call. The port is the
                # command line's; the listener belongs to http.sys (pid 4), so listen_ports never has it.
                "api_paused": (
                    api_port is None
                    and process["started_with_api"]
                    and any(title == "Scripting Server" for title in window_titles)
                ),
            }
        )
    return sessions


def load_concept_api(exe_path: str | None):
    api_dir = python_api_dir_for_exe(exe_path)
    if api_dir is None:
        raise AttachError("Installed RAM Concept Python API was not found.")
    vendor = str(SCRIPT_DIRECTORY / "api_vendor")
    api = str(api_dir)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    if api not in sys.path:
        sys.path.insert(1, api)
    from ram_concept.concept import Concept
    from ram_concept.model import Model

    return Concept, Model, api_dir


def wrap_live_model(concept, Model):
    model = Model(concept)
    concept._model = model
    return model


def read_only_snapshot(model) -> dict[str, Any]:
    cad = model.cad_manager
    structure = cad.structure_layer
    calc = model.calc_options
    snapshot: dict[str, Any] = {
        "units_token": model.units.get_units(),
        "structure": {
            "slab_areas": len(structure.slab_areas),
            "slab_openings": len(structure.slab_openings),
            "beams": len(structure.beams),
            "walls_below": len(structure.walls_below),
            "walls_above": len(structure.walls_above),
            "columns_below": len(structure.columns_below),
            "columns_above": len(structure.columns_above),
        },
        "calc_options": {
            "auto_xy_stabilize": calc.auto_xy_stabilize,
            "create_viewable_self_dead_loading": calc.create_viewable_self_dead_loading,
            "supports_above_in_self_dead": calc.supports_above_in_self_dead,
            "consider_tendon_component_in_punch_check_reaction": (
                calc.consider_tendon_component_in_punch_check_reaction
            ),
            "check_capacity_only": calc.check_capacity_only,
            "desired_element_size": calc.desired_element_size,
        },
        "tendon_layers": len(cad.tendon_layers),
        "pt_systems": [system.name for system in model.pt_systems.pt_systems],
        "api_gaps": [
            "design_strips",
            "span_segments",
            "consider_as_post_tensioned",
        ],
    }
    return snapshot


def attach_to_session(session: dict[str, Any]) -> dict[str, Any]:
    if not session.get("api_ready"):
        raise AttachError(relaunch_hint(session))
    Concept, Model, api_dir = load_concept_api(session.get("exe"))
    concept = Concept.attach_to_concept(int(session["api_port"]))
    process_id = concept._get_process_id()
    model = wrap_live_model(concept, Model)
    snapshot = read_only_snapshot(model)
    return {
        "attached": True,
        "pid": session["pid"],
        "api_pid": process_id,
        "port": session["api_port"],
        "exe": session.get("exe"),
        "python_api": str(api_dir),
        "window_titles": session.get("window_titles") or [],
        "open_cpt": session.get("open_cpt"),
        "snapshot": snapshot,
    }


def relaunch_hint(session: dict[str, Any] | None = None) -> str:
    file_arg = ""
    if session and session.get("open_cpt") and "\\" in str(session["open_cpt"]):
        file_arg = f' --file "{session["open_cpt"]}"'
    return (
        ("This RAM Concept window was started with the API but its Scripting Server is paused or busy: "
         "resume it (scripting-server.ps1 -Resume) and try again.\n"
         if session and session.get("api_paused") else "")
        + "This RAM Concept window is not serving the API. "
        "Close it, then start an API-enabled GUI:\n"
        "  python ram-concept\\scripts\\attach-live-concept.py --start-gui"
        f"{file_arg}"
    )


def choose_session(sessions: list[dict[str, Any]], port: int | None) -> dict[str, Any]:
    if port is not None:
        for session in sessions:
            if session.get("api_port") == port or port in (session.get("listen_ports") or []):
                if ping_concept_port(port) == "PONG":
                    session = dict(session)
                    session["api_port"] = port
                    session["api_ready"] = True
                    session["api_ping"] = "PONG"
                    return session
        raise AttachError(f"No RAM Concept API responded on port {port}.")
    ready = [session for session in sessions if session.get("api_ready")]
    if len(ready) == 1:
        return ready[0]
    if len(ready) > 1:
        ports = ", ".join(str(session["api_port"]) for session in ready)
        raise AttachError(f"Multiple API-enabled Concept sessions found. Pass --port ({ports}).")
    if len(sessions) == 1:
        return sessions[0]
    if not sessions:
        raise AttachError("No Concept.exe process is running.")
    raise AttachError(
        "Multiple Concept.exe processes are running and none have a live API. "
        "Pass --port if one was started with -apiServerWithGui."
    )


def start_api_gui(file_path: str | None, port: int | None, exe_path: str | None) -> dict[str, Any]:
    Concept, Model, api_dir = load_concept_api(exe_path)
    concept = Concept.start_concept(
        headless=False,
        path=exe_path or None,
        port=port,
        start_timeout_seconds=90,
        inactivity_timeout_seconds=3600,
    )
    result: dict[str, Any] = {
        "started": True,
        "headless": False,
        "python_api": str(api_dir),
        "api_pid": concept._get_process_id(),
        "url": concept._url,
    }
    if file_path:
        model = concept.open_file(str(Path(file_path).resolve()))
        result["opened"] = str(Path(file_path).resolve())
        result["snapshot"] = read_only_snapshot(model)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Attach to a live RAM Concept GUI through the official API."
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="List running Concept.exe sessions and whether their API is reachable.",
    )
    parser.add_argument(
        "--attach",
        action="store_true",
        help="Attach to the live session and print a read-only model snapshot.",
    )
    parser.add_argument(
        "--start-gui",
        action="store_true",
        help="Start a new Concept GUI that listens for the official API.",
    )
    parser.add_argument("--port", type=int, help="API port to use or attach to.")
    parser.add_argument("--file", help="Open this .cpt in a newly started API GUI.")
    parser.add_argument("--exe", help="Concept.exe path when starting a new API GUI.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format. Default: json.",
    )
    return parser


def render_markdown(payload: dict[str, Any]) -> str:
    if payload.get("sessions") is not None:
        lines = ["# RAM Concept API probe", ""]
        if not payload["sessions"]:
            lines.append("No Concept.exe process is running.")
            return "\n".join(lines)
        for session in payload["sessions"]:
            titles = [t for t in (session.get("window_titles") or []) if t != "Scripting Server"]
            title = session.get("open_cpt") or (titles or ["untitled"])[0]
            if session.get("api_ready"):
                status, port = "API ready", session.get("api_port")
            elif session.get("api_paused"):
                status, port = "API paused or busy: resume the Scripting Server (scripting-server.ps1 -Resume)", session.get("command_port")
            else:
                status, port = "no API", None
            lines.append(
                f"- pid `{session['pid']}` / {status}"
                + (f" / port `{port}`" if port else "")
                + f" / {title}"
            )
        return "\n".join(lines)
    return "```json\n" + json.dumps(payload, indent=2) + "\n```"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.probe or args.attach or args.start_gui):
        args.probe = True
        args.attach = True

    try:
        if args.start_gui:
            payload = start_api_gui(args.file, args.port, args.exe)
        else:
            sessions = probe_concept_sessions()
            payload = {"sessions": sessions}
            if args.attach:
                session = choose_session(sessions, args.port)
                payload = attach_to_session(session)
    except AttachError as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.format == "markdown":
        print(render_markdown(payload))
    else:
        json.dump(payload, sys.stdout, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
