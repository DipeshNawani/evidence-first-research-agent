"""One-command local demo: reuse the right server or own and clean up a new one."""

import errno
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import httpx
from pydantic import ValidationError

from research_agent.config import Settings
from research_agent.schemas import HealthResponse


def probe_server(port: int) -> HealthResponse | None:
    # Windows can report a connect timeout for a closed loopback port. Probe
    # ownership with bind first so that a free port is not mistaken for a hung app.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        try:
            candidate.bind(("127.0.0.1", port))
        except OSError as exc:
            if exc.errno not in {errno.EADDRINUSE, 10048}:
                raise RuntimeError(
                    f"Cannot use local port {port}. Choose a different --port."
                ) from None
        else:
            return None
    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=3, trust_env=False)
    except httpx.ConnectError:
        return None
    except httpx.HTTPError:
        raise RuntimeError(
            f"Port {port} is not responding. Stop the existing process or choose --port 8001."
        ) from None
    try:
        response.raise_for_status()
        health = HealthResponse.model_validate(response.json())
        if health.ui_version != "1":
            raise ValueError("Unsupported local UI")
        return health
    except (httpx.HTTPError, ValueError, ValidationError):
        raise RuntimeError(
            f"Port {port} is occupied by an incompatible server. Restart it or choose --port 8001."
        ) from None


def launch_demo(
    settings: Settings, *, port: int = 8000, mock: bool = False, open_browser: bool = True
) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    url = f"http://127.0.0.1:{port}/"
    provider = "mock" if mock else settings.llm_provider
    existing = probe_server(port)
    if existing:
        if existing.provider != provider:
            raise RuntimeError(
                f"Port {port} is serving {existing.provider}. Choose --port 8001 for {provider}."
            )
        print(f"Using your running {provider} server: {url}", flush=True)
        if open_browser:
            webbrowser.open(url)
        return
    environment = os.environ.copy()
    environment["RA_LLM_PROVIDER"] = provider
    environment["PYTHONUTF8"] = "1"
    settings.trace_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.trace_dir / f"demo-server-{port}.log"
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "research_agent.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=Path.cwd(),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform == "win32"
            else 0,
        )
        try:
            started = time.monotonic()
            while time.monotonic() - started < 20:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"The demo server could not start. Check {log_path.resolve()} (missing keys or an occupied port are common causes)."
                    )
                if probe_server(port):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f"Demo startup timed out. Check {log_path.resolve()}.")
            print(
                f"Research Agent is ready: {url}\nProvider: {provider}\nPress Ctrl+C here to stop this demo server. Logs: {log_path.resolve()}",
                flush=True,
            )
            if open_browser:
                webbrowser.open(url)
            process.wait()
        except KeyboardInterrupt:
            print("\nStopping the demo server…", flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
